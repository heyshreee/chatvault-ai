import pytest

from app.ingestion.url_validator import (
    validate_chatgpt_url,
    InvalidChatGPTURL
)


def test_valid_chatgpt_url():

    url = "https://chatgpt.com/share/abc123"

    result = validate_chatgpt_url(url)

    assert result == url


def test_valid_url_with_trailing_slash():

    url = "https://chatgpt.com/share/abc123/"

    result = validate_chatgpt_url(url)

    assert result == "https://chatgpt.com/share/abc123"


@pytest.mark.parametrize(
    "url",
    [
        "https://google.com",
        "http://chatgpt.com/share/abc123",
        "https://fake-chatgpt.com/share/abc123",
        "https://chatgpt.com/",
        "https://chatgpt.com/share/",
        "https://chatgpt.com.evil.com/share/abc123",
        "https://user:pass@chatgpt.com/share/abc123",
        "https://chatgpt.com:8080/share/abc123",
        "",
    ]
)
def test_invalid_urls(url):

    with pytest.raises(InvalidChatGPTURL):
        validate_chatgpt_url(url)