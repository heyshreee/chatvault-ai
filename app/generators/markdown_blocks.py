"""Shared Markdown block parsing for document exports.

The exporters intentionally support a practical subset of Markdown:
headings, paragraphs, bullet and numbered lists, task lists, block quotes,
fenced code blocks, pipe tables, and horizontal rules. This keeps PDF and DOCX
output consistent without pulling in a full Markdown renderer.
"""

import re

from app.processing.text_cleaner import clean_chatgpt_text


HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
LINK_TAG_RE = re.compile(
    r'<Link\b[^>]*\btitle="([^"]*)"[^>]*/>',
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"^\s*```")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$")
TASK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")
NUMBERED_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$")
RULE_RE = re.compile(r"^\s*([-*_])\1{2,}\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^:?-{2,}:?$")


def _strip_tags(text: str) -> str:
    text = LINK_TAG_RE.sub(r"\1", text)

    return HTML_TAG_RE.sub("", text)


def strip_inline_html(text: str) -> str:
    """Remove inline HTML tags while preserving backticked code spans."""

    parts = re.split(r"(`[^`]*`)", text)

    return "".join(
        part
        if part.startswith("`") and part.endswith("`")
        else _strip_tags(part)
        for part in parts
    )


def split_table_row(line: str) -> list[str]:
    """Split a pipe-table row without breaking escaped pipes."""

    text = line.strip()

    if text.startswith("|"):
        text = text[1:]

    if text.endswith("|"):
        text = text[:-1]

    return [
        cell.strip().replace("\\|", "|")
        for cell in re.split(r"(?<!\\)\|", text)
    ]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)

    return bool(cells) and all(
        TABLE_SEPARATOR_RE.match(cell.replace(" ", ""))
        for cell in cells
    )


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False

    line = lines[index].strip()
    next_line = lines[index + 1].strip()

    return (
        line.startswith("|")
        and line.endswith("|")
        and "|" in line[1:-1]
        and next_line.startswith("|")
        and next_line.endswith("|")
        and is_table_separator(next_line)
    )


def parse_blocks(content: str) -> list[tuple]:
    """Parse message text into structured export blocks."""

    lines = clean_chatgpt_text(content).splitlines()
    blocks: list[tuple] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(("paragraph", "\n".join(paragraph)))
            paragraph.clear()

    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if FENCE_RE.match(line):
            flush_paragraph()

            code: list[str] = []
            index += 1

            while index < len(lines) and not FENCE_RE.match(lines[index]):
                code.append(lines[index])
                index += 1

            if index < len(lines):
                index += 1

            blocks.append(("code", "\n".join(code)))
            continue

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if is_table_start(lines, index):
            flush_paragraph()

            rows = [split_table_row(line)]
            index += 2

            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_table_row(lines[index]))
                index += 1

            width = max(len(row) for row in rows)
            rows = [row + [""] * (width - len(row)) for row in rows]

            blocks.append(("table", rows))
            continue

        heading = HEADING_RE.match(stripped)

        if heading:
            flush_paragraph()
            blocks.append((
                "heading",
                len(heading.group(1)),
                heading.group(2),
            ))
            index += 1
            continue

        if RULE_RE.match(stripped):
            flush_paragraph()
            blocks.append(("rule", ""))
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()

            quote_lines: list[str] = []

            while index < len(lines):
                quote_line = lines[index].strip()

                if not quote_line.startswith(">"):
                    break

                quote_line = quote_line[1:]

                if quote_line.startswith(" "):
                    quote_line = quote_line[1:]

                quote_lines.append(quote_line)
                index += 1

            blocks.append(("quote", "\n".join(quote_lines)))
            continue

        task = TASK_RE.match(line)

        if task:
            flush_paragraph()
            blocks.append((
                "task",
                task.group(1).lower() == "x",
                task.group(2),
            ))
            index += 1
            continue

        bullet = BULLET_RE.match(line)

        if bullet:
            flush_paragraph()
            blocks.append(("bullet", bullet.group(1)))
            index += 1
            continue

        numbered = NUMBERED_RE.match(line)

        if numbered:
            flush_paragraph()
            blocks.append(("numbered", stripped))
            index += 1
            continue

        paragraph.append(stripped)
        index += 1

    flush_paragraph()

    return blocks
