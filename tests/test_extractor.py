from pathlib import Path

import pytest

from app.ingestion.extractor import (
    extract_conversation,
    extract_conversation_id,
    extract_messages,
    ExtractionError,
    ConversationNotFoundError
)

FIXTURE = Path(
    "tests/fixtures/sample_conversation.html"
)


TEST_URL = "https://chatgpt.com/share/abc123"


def test_extract_conversation():

    html = FIXTURE.read_text(encoding="utf-8")

    conversation = extract_conversation(html, TEST_URL)

    assert conversation.conversation_id == "abc123"

    assert conversation.title == "Learning Nmap - ChatGPT"

    assert len(conversation.messages) == 4


def test_extract_message_roles():

    html = FIXTURE.read_text(encoding="utf-8")

    conversation = extract_conversation(html, TEST_URL)

    roles = [message.role for message in conversation.messages]

    assert roles == [
        "user",
        "assistant",
        "user",
        "assistant"
    ]


def test_extract_message_order():

    html = FIXTURE.read_text(encoding="utf-8")

    conversation = extract_conversation(html, TEST_URL)

    positions = [
        message.position
        for message in conversation.messages
    ]

    assert positions == [0, 1, 2, 3]


def test_extract_code_content():

    html = FIXTURE.read_text(encoding="utf-8")

    conversation = extract_conversation(html, TEST_URL)

    last_message = conversation.messages[-1]

    assert "nmap -sV 192.168.1.1" in last_message.content


def test_extract_conversation_id():

    result = extract_conversation_id(TEST_URL)

    assert result == "abc123"


def test_invalid_conversation_url():

    with pytest.raises(ExtractionError):

        extract_conversation_id(
            "https://google.com"
        )


def test_empty_html():

    with pytest.raises(ConversationNotFoundError):

        extract_conversation("", TEST_URL)


def test_missing_messages():

    html = "<html><head><title>Empty</title></head><body></body></html>"

    with pytest.raises(ConversationNotFoundError):

        extract_conversation(html, TEST_URL)