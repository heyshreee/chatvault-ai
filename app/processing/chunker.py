import math
import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.core.config import settings
from app.processing.text_cleaner import clean_chatgpt_text


# The default token counter is a deterministic approximation. It is
# intentionally labelled as approximate in the API; nomic-embed-text uses
# a different tokenizer, and exact tokenization is not required for stable
# chunk boundaries.
CHARS_PER_TOKEN = 4
TOKEN_COUNTING_METHOD = "approximate_char4"


class MessageLike(Protocol):
    id: int
    position: int
    role: str
    content: str


class ConversationLike(Protocol):
    id: int
    conversation_id: str
    title: str
    messages: Sequence[MessageLike]


@dataclass(frozen=True)
class Chunk:
    conversation_id: str
    conversation_db_id: int
    conversation_title: str
    message_id: int
    message_position: int
    role: str
    chunk_index: int
    content: str
    estimated_tokens: int

    @property
    def chunk_id(self) -> str:
        return (
            f"{self.conversation_id}:"
            f"{self.message_position}:"
            f"{self.chunk_index}"
        )


def estimate_tokens(text: str) -> int:
    """Approximate token count using a deterministic character ratio."""

    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def chunk_conversation(
    conversation: ConversationLike,
    size_tokens: int | None = None,
    overlap_tokens: int | None = None,
    min_tokens: int | None = None,
    chunking_version: str | None = None,
) -> list[Chunk]:
    """Split a stored conversation into message-aware chunks."""

    size_tokens = (
        settings.CHUNK_SIZE_TOKENS
        if size_tokens is None
        else size_tokens
    )
    overlap_tokens = (
        settings.CHUNK_OVERLAP_TOKENS
        if overlap_tokens is None
        else overlap_tokens
    )
    min_tokens = settings.CHUNK_MIN_TOKENS if min_tokens is None else min_tokens
    chunking_version = (
        settings.CHUNKING_VERSION
        if chunking_version is None
        else chunking_version
    )

    if size_tokens <= 0:
        raise ValueError("Chunk size must be positive.")

    if overlap_tokens < 0 or overlap_tokens >= size_tokens:
        raise ValueError("Chunk overlap must be smaller than chunk size.")

    if min_tokens < 0 or min_tokens > size_tokens:
        raise ValueError("Minimum chunk size is invalid.")

    if not chunking_version.strip():
        raise ValueError("Chunking version cannot be empty.")

    size_chars = size_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN
    min_chars = min_tokens * CHARS_PER_TOKEN

    # Leave room for the overlap prefix and its separator in every chunk.
    body_budget_chars = max(1, size_chars - overlap_chars - 2)

    chunks: list[Chunk] = []

    ordered_messages = sorted(
        conversation.messages,
        key=lambda message: message.position,
    )

    for message in ordered_messages:
        content = clean_chatgpt_text(
            message.content or ""
        ).strip()

        if not content:
            continue

        units = _split_message_units(content)

        pieces: list[tuple[str, str]] = []

        for kind, unit_text in units:
            if not unit_text.strip():
                continue

            pieces.extend(
                _split_unit(
                    kind=kind,
                    text=unit_text,
                    max_chars=body_budget_chars,
                    min_chars=min_chars,
                )
            )

        message_chunks = _pack_units(
            pieces=pieces,
            size_chars=size_chars,
            overlap_chars=overlap_chars,
            min_chars=min_chars,
        )

        for index, text in enumerate(message_chunks):
            chunks.append(
                Chunk(
                    conversation_id=conversation.conversation_id,
                    conversation_db_id=conversation.id,
                    conversation_title=conversation.title,
                    message_id=message.id,
                    message_position=message.position,
                    role=message.role,
                    chunk_index=index,
                    content=text,
                    estimated_tokens=estimate_tokens(text),
                )
            )

    return chunks


# --------------------------------------------------
# Message block parsing
# --------------------------------------------------

_HEADING_PATTERN = re.compile(r"^#{1,6}\s+\S")
_BULLET_PATTERN = re.compile(r"^\s*[-*+]\s+\S")
_NUMBERED_PATTERN = re.compile(r"^\s*\d+[.)]\s+\S")


def _split_message_units(content: str) -> list[tuple[str, str]]:
    """Split Markdown-ish content into paragraphs and fenced code blocks."""

    units: list[tuple[str, str]] = []
    paragraph_lines: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph():
        if paragraph_lines:
            units.append(("text", "\n".join(paragraph_lines).strip()))
            paragraph_lines.clear()

    for line in content.splitlines():

        fence = line.strip().startswith("```")

        if in_code:
            code_lines.append(line)

            if fence:
                units.append(("code", "\n".join(code_lines).strip("\n")))
                code_lines = []
                in_code = False

            continue

        if fence:
            flush_paragraph()
            in_code = True
            code_lines = [line]
            continue

        if not line.strip():
            flush_paragraph()
            continue

        if (
            _HEADING_PATTERN.match(line)
            or _BULLET_PATTERN.match(line)
            or _NUMBERED_PATTERN.match(line)
        ):
            flush_paragraph()
            units.append(("text", line.strip()))
            continue

        paragraph_lines.append(line)

    flush_paragraph()

    if code_lines:
        units.append(("code", "\n".join(code_lines).strip("\n")))

    return [(kind, text) for kind, text in units if text.strip()]


# --------------------------------------------------
# Unit splitting
# --------------------------------------------------

def _split_unit(
    kind: str,
    text: str,
    max_chars: int,
    min_chars: int,
) -> list[tuple[str, str]]:
    if len(text) <= max_chars:
        return [(kind, text)]

    if kind == "code":
        return [
            ("code", piece)
            for piece in _split_code_block(text, max_chars)
        ]

    pieces = _split_text(text, max_chars)

    # Avoid leaving a tiny final text piece when it can be merged.
    if len(pieces) > 1 and len(pieces[-1]) < min_chars:
        combined = f"{pieces[-2]}\n\n{pieces[-1]}"

        if len(combined) <= max_chars:
            pieces[-2:] = [combined]

    return [("text", piece) for piece in pieces]


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text at natural boundaries without exceeding max_chars."""

    if max_chars <= 0:
        return [text]

    pieces: list[str] = []
    remaining = text

    while len(remaining) > max_chars:
        window = remaining[:max_chars + 1]

        cut = window.rfind("\n")

        if cut <= 0:
            sentence_cut = 0

            for match in re.finditer(r"[.!?](?:\s|$)", window):
                sentence_cut = match.end()

            cut = sentence_cut

        if cut <= 0:
            whitespace_cut = max(
                window.rfind(" "),
                window.rfind("\t"),
            )
            cut = whitespace_cut

        if cut <= 0:
            cut = max_chars

        # Sentence boundaries can land one character past the window.
        cut = min(cut, max_chars)

        piece = remaining[:cut].rstrip()

        if piece:
            pieces.append(piece)

        remaining = remaining[cut:].lstrip()

    if remaining.strip():
        pieces.append(remaining.rstrip())

    return pieces


def _split_code_block(text: str, max_chars: int) -> list[str]:
    """Split an oversized fenced code block and re-fence each piece."""

    lines = text.splitlines()

    opening_fence = "```"

    if lines and lines[0].strip().startswith("```"):
        opening_fence = lines[0].strip()
        lines = lines[1:]

    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]

    if not lines:
        lines = [""]

    overhead = len(opening_fence) + len("\n```") + 2
    line_budget = max(8, max_chars - overhead)

    if max_chars <= overhead + 8:
        # The chunk budget is too small to keep a fenced block intact.
        # Fall back to plain splitting so the hard size limit still holds.
        return _split_text(text, max_chars)

    groups: list[list[str]] = []
    current: list[str] = []
    current_length = 0

    def flush():
        if current:
            groups.append(current.copy())
            current.clear()

    for line in lines:

        line_pieces = (
            _split_text(line, line_budget)
            if len(line) > line_budget
            else [line]
        )

        for line_piece in line_pieces:
            extra = len(line_piece) + (1 if current else 0)

            if current and current_length + extra > line_budget:
                flush()
                current_length = 0

            current.append(line_piece)
            current_length += extra

    flush()

    result = []

    for group in groups:
        result.append(
            f"{opening_fence}\n{'\n'.join(group)}\n```"
        )

    return result


# --------------------------------------------------
# Packing
# --------------------------------------------------

def _pack_units(
    pieces: list[tuple[str, str]],
    size_chars: int,
    overlap_chars: int,
    min_chars: int,
) -> list[str]:
    """Pack units into chunks, adding overlap within one message."""

    if not pieces:
        return []

    drafts: list[dict] = []
    current_parts: list[str] = []
    current_overlap = ""
    current_length = 0

    def flush():
        nonlocal current_parts, current_overlap, current_length

        if not current_parts:
            return

        body = "\n\n".join(current_parts)

        drafts.append({
            "overlap": current_overlap,
            "body": body,
        })

        current_overlap = _tail(
            _join_overlap_body(current_overlap, body),
            overlap_chars,
        )
        current_parts = []
        current_length = 0

    for _, piece in pieces:
        separator = "\n\n" if current_parts else ""
        projected = (
            len(current_overlap)
            + (2 if current_overlap else 0)
            + current_length
            + len(separator)
            + len(piece)
        )

        if current_parts and projected > size_chars:
            flush()

        if not current_parts:
            current_overlap = (
                current_overlap
                if drafts
                else ""
            )
            current_parts = [piece]
            current_length = len(piece)
            continue

        current_parts.append(piece)
        current_length += len(piece) + len(separator)

    flush()

    # Merge a tiny final chunk into its predecessor where it fits.
    if len(drafts) > 1:
        last_estimated = estimate_tokens(
            _join_overlap_body(
                drafts[-1]["overlap"],
                drafts[-1]["body"],
            )
        )

        if last_estimated < max(1, math.ceil(min_chars / CHARS_PER_TOKEN)):
            merged_body = f"{drafts[-2]['body']}\n\n{drafts[-1]['body']}"
            merged_content = _join_overlap_body(
                drafts[-2]["overlap"],
                merged_body,
            )

            if len(merged_content) <= size_chars:
                drafts[-2]["body"] = merged_body
                drafts.pop()

    return [
        _join_overlap_body(draft["overlap"], draft["body"])
        for draft in drafts
    ]


def _join_overlap_body(overlap: str, body: str) -> str:
    if overlap and body:
        return f"{overlap}\n\n{body}"

    return overlap or body


def _tail(text: str, max_chars: int) -> str:
    """Return a word-aligned suffix no longer than max_chars."""

    if max_chars <= 0 or not text:
        return ""

    if len(text) <= max_chars:
        return text

    tail = text[-max_chars:]

    # Prefer a line boundary, then a word boundary.
    newline = tail.find("\n")

    if newline != -1 and newline + 1 < len(tail):
        return tail[newline + 1:].lstrip()

    space = tail.find(" ")

    if space != -1 and space + 1 < len(tail):
        return tail[space + 1:].lstrip()

    return tail
