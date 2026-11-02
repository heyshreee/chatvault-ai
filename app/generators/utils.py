
import re
from pathlib import Path

GENERATED_DIR = Path("storage/generated")


def get_output_path(conversation_id: str, extension: str) -> Path:
    """Build a safe output path using the conversation ID."""

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", conversation_id):
        raise ValueError("Invalid conversation ID.")

    if extension not in {"pdf", "docx"}:
        raise ValueError("Unsupported document extension.")

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    return GENERATED_DIR / f"{conversation_id}.{extension}"


def split_message_blocks(content: str):
    """
    Split message text into normal paragraphs and fenced code blocks.

    Returns tuples: ("text", content) or ("code", content).
    """

    blocks = []
    current_lines = []
    in_code = False

    for line in content.splitlines():
        if line.strip().startswith("```"):
            if current_lines:
                blocks.append((
                    "code" if in_code else "text",
                    "\n".join(current_lines).strip("\n"),
                ))
                current_lines = []

            in_code = not in_code
            continue

        current_lines.append(line)

    if current_lines:
        blocks.append((
            "code" if in_code else "text",
            "\n".join(current_lines).strip("\n"),
        ))

    return [
        (kind, text)
        for kind, text in blocks
        if text.strip()
    ]
