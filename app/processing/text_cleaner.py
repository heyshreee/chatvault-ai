"""Normalize ChatGPT-specific annotations in stored message text.

Shared conversations contain private-use markers such as:

    \\ue200url\\ue202Title\\ue202https://example.com\\ue201

These annotations power ChatGPT's UI but are not meaningful prose. They must
not leak into exports, retrieval context, or the conversation viewer.
"""

import json
import re


ANNOTATION_RE = re.compile(r"\ue200([^\ue200\ue201]*)\ue201")
RESIDUAL_RE = re.compile(r"[\ue200-\ue2ff]")
FIELD_SEPARATOR = "\ue202"


def _clean_annotation(body: str) -> str:
    parts = body.split(FIELD_SEPARATOR)
    kind = parts[0].strip()

    if kind == "url":
        values = [part.strip() for part in parts[1:] if part.strip()]

        # The title is more readable than a bare URL. Fall back to the URL
        # when an annotation has no title.
        return values[0] if values else ""

    if kind == "entity":
        if len(parts) < 2:
            return ""

        try:
            data = json.loads(parts[1])
        except (TypeError, ValueError):
            return ""

        if isinstance(data, list):
            for value in data[1:]:
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

    # genui, image_group, and unknown UI-only annotations carry no prose.
    return ""


def clean_chatgpt_text(text: str) -> str:
    """Remove ChatGPT UI annotations while preserving normal Markdown."""

    if not text:
        return text

    cleaned = ANNOTATION_RE.sub(
        lambda match: _clean_annotation(match.group(1)),
        text,
    )

    return RESIDUAL_RE.sub("", cleaned)
