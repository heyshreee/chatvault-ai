
from dataclasses import dataclass
from urllib.parse import urlsplit
import json
import re

from bs4 import BeautifulSoup

from app.processing.text_cleaner import clean_chatgpt_text


class ExtractionError(Exception):
    """Base exception for conversation extraction errors."""


class ConversationNotFoundError(ExtractionError):
    """Raised when no supported conversation messages are found."""


@dataclass
class Message:
    role: str
    content: str
    position: int


@dataclass
class Conversation:
    conversation_id: str
    title: str
    source_url: str
    messages: list[Message]


# --------------------------------------------------
# Conversation metadata
# --------------------------------------------------

def extract_conversation_id(url: str) -> str:
    match = re.search(
        r"/share/([A-Za-z0-9_-]+)/?$",
        urlsplit(url).path
    )

    if not match:
        raise ExtractionError("Unable to extract conversation ID.")

    return match.group(1)


def extract_title(soup: BeautifulSoup) -> str:
    title = soup.find("title")

    if title and title.get_text(strip=True):
        return title.get_text(strip=True)

    return "Untitled Conversation"


# --------------------------------------------------
# Serialized ChatGPT payload decoder
# --------------------------------------------------

def get_field(payload: list, obj, name: str):
    """
    Resolve a serialized object property name.

    Properties are represented as references such as:
        {"_142": 1237}

    The actual property name is stored at payload[142].
    """

    if not isinstance(obj, dict):
        return None

    for key, value in obj.items():
        if not isinstance(key, str) or not key.startswith("_"):
            continue

        try:
            property_index = int(key[1:])
            if payload[property_index] == name:
                return value
        except (ValueError, IndexError, TypeError):
            continue

    return None


def resolve(payload: list, ref):
    """Resolve an indexed reference when it is valid."""

    if isinstance(ref, int) and 0 <= ref < len(payload):
        return payload[ref]

    return ref


def extract_js_string(source: str, start: int) -> str:
    """Extract a quoted JavaScript string, respecting escapes."""

    quote = source[start]
    escaped = False

    for index in range(start + 1, len(source)):
        char = source[index]

        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote:
            return source[start:index + 1]

    raise ExtractionError("Unterminated serialized payload string.")


def decode_script_payload(source: str):
    """
    Decode the serialized JSON payload inside a script's enqueue call.
    """

    marker = ".enqueue("
    search_from = 0

    while True:
        position = source.find(marker, search_from)

        if position == -1:
            return None

        position += len(marker)

        while position < len(source) and source[position].isspace():
            position += 1

        if position >= len(source) or source[position] not in {"'", '"'}:
            search_from = position
            continue

        try:
            js_string = extract_js_string(source, position)
            serialized = json.loads(js_string)
            payload = json.loads(serialized)

            if not isinstance(payload, list):
                raise ValueError("Expected a serialized list.")

            return payload

        except (ValueError, json.JSONDecodeError, TypeError):
            search_from = position + 1


def find_conversation_metadata(payload: list):
    """
    Find the object containing both mapping and linear_conversation.
    """

    for item in payload:
        if not isinstance(item, dict):
            continue

        mapping_ref = get_field(payload, item, "mapping")
        linear_ref = get_field(payload, item, "linear_conversation")

        mapping = resolve(payload, mapping_ref)
        linear = resolve(payload, linear_ref)

        if isinstance(mapping, dict) and isinstance(linear, list):
            return item, mapping, linear

    return None


def extract_serialized_messages(payload: list) -> list[Message]:
    """
    Extract user and assistant text messages in linear conversation order.
    """

    metadata_result = find_conversation_metadata(payload)

    if metadata_result is None:
        raise ConversationNotFoundError(
            "Supported conversation metadata was not found."
        )

    _, mapping, linear = metadata_result

    # Build node lookup using actual node IDs.
    nodes_by_id = {}

    for node_ref in mapping.values():
        node = resolve(payload, node_ref)

        if not isinstance(node, dict):
            continue

        node_id_ref = get_field(payload, node, "id")
        node_id = resolve(payload, node_id_ref)

        if isinstance(node_id, str):
            nodes_by_id[node_id] = node

    messages = []

    for linear_ref in linear:
        linear_item = resolve(payload, linear_ref)

        if not isinstance(linear_item, dict):
            continue

        node_id_ref = get_field(payload, linear_item, "id")
        node_id = resolve(payload, node_id_ref)

        if not isinstance(node_id, str):
            continue

        node = nodes_by_id.get(node_id)

        if not node:
            continue

        message_ref = get_field(payload, node, "message")
        message = resolve(payload, message_ref)

        if not isinstance(message, dict):
            continue

        # Extract role.
        author_ref = get_field(payload, message, "author")
        author = resolve(payload, author_ref)

        role_ref = get_field(payload, author, "role")
        role = resolve(payload, role_ref)

        # Only import actual conversation participants.
        if role not in {"user", "assistant"}:
            continue

        # Extract content.
        content_ref = get_field(payload, message, "content")
        content = resolve(payload, content_ref)

        if not isinstance(content, dict):
            continue

        content_type_ref = get_field(
            payload, content, "content_type"
        )
        content_type = resolve(payload, content_type_ref)

        # Exclude thoughts, reasoning recaps, metadata, etc.
        if content_type != "text":
            continue

        parts_ref = get_field(payload, content, "parts")
        parts = resolve(payload, parts_ref)

        if not isinstance(parts, list):
            continue

        text_parts = []

        for part_ref in parts:
            part = resolve(payload, part_ref)

            # Only accept verified plain-text parts.
            if isinstance(part, str) and part.strip():
                text_parts.append(part)

        text_content = clean_chatgpt_text(
            "\n".join(text_parts)
        ).strip()

        if not text_content:
            continue

        messages.append(
            Message(
                role=role,
                content=text_content,
                position=len(messages)
            )
        )

    if not messages:
        raise ConversationNotFoundError(
            "No supported user or assistant text messages found."
        )

    return messages


# --------------------------------------------------
# Legacy HTML fallback for existing fixtures
# --------------------------------------------------

def extract_message_content(element) -> str:
    parts = []

    for node in element.descendants:
        if getattr(node, "name", None) == "code":
            text = node.get_text()

            if text:
                parts.append(text)

        elif isinstance(node, str):
            parent = node.parent

            if parent and parent.name in {"script", "style"}:
                continue

            parts.append(node)

    return "".join(parts).strip()


def extract_legacy_messages(soup: BeautifulSoup) -> list[Message]:
    elements = soup.select(
        '[data-message-author-role="user"], '
        '[data-message-author-role="assistant"]'
    )

    messages = []

    for element in elements:
        role = element.get("data-message-author-role")
        content = extract_message_content(element)

        if not content:
            continue

        messages.append(
            Message(
                role=role,
                content=content,
                position=len(messages)
            )
        )

    return messages



# --------------------------------------------------
# Main extractor
# --------------------------------------------------

def extract_conversation(html: str, source_url: str) -> Conversation:
    if not html or not html.strip():
        raise ConversationNotFoundError("HTML content is empty.")

    soup = BeautifulSoup(html, "html.parser")

    conversation_id = extract_conversation_id(source_url)

    messages = None

    # Try the real serialized ChatGPT payload first.
    for script in soup.find_all("script"):
        source = script.string or script.get_text()

        if not source or ".enqueue(" not in source:
            continue

        payload = decode_script_payload(source)

        if payload is None:
            continue

        metadata_result = find_conversation_metadata(payload)

        if metadata_result is None:
            continue

        metadata, _, _ = metadata_result

        title_ref = get_field(payload, metadata, "title")
        title = resolve(payload, title_ref)

        if not isinstance(title, str) or not title.strip():
            title = extract_title(soup)

        messages = extract_serialized_messages(payload)
        break

    # Retain compatibility with the original unit-test fixture.
    if messages is None:
        title = extract_title(soup)
        messages = extract_legacy_messages(soup)

    if not messages:
        raise ConversationNotFoundError(
            "No supported conversation messages found in HTML."
        )

    return Conversation(
        conversation_id=conversation_id,
        title=title,
        source_url=source_url,
        messages=messages
    )


def extract_messages(soup: BeautifulSoup) -> list[Message]:
    """Backward-compatible HTML extractor for existing tests."""

    messages = extract_legacy_messages(soup)

    if not messages:
        raise ConversationNotFoundError(
            "No supported conversation messages found in HTML."
        )

    return messages