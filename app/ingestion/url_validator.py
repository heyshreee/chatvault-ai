from urllib.parse import urlsplit
import re


ALLOWED_HOST = "chatgpt.com"

SHARE_PATH_PATTERN = re.compile(
    r"^/share/([A-Za-z0-9_-]+)/?$"
)


class InvalidChatGPTURL(ValueError):
    """Raised when a ChatGPT shared URL is invalid."""


def validate_chatgpt_url(url: str) -> str:
    """
    Validate a publicly shared ChatGPT conversation URL.

    Returns:
        Normalized URL.

    Raises:
        InvalidChatGPTURL: If URL is invalid.
    """

    if not isinstance(url, str) or not url.strip():
        raise InvalidChatGPTURL("URL cannot be empty.")

    try:
        parsed = urlsplit(url.strip())
    except ValueError as exc:
        raise InvalidChatGPTURL("Malformed URL.") from exc

    if parsed.scheme != "https":
        raise InvalidChatGPTURL("Only HTTPS URLs are allowed.")

    if parsed.hostname != ALLOWED_HOST:
        raise InvalidChatGPTURL("Only chatgpt.com URLs are allowed.")

    if parsed.username or parsed.password:
        raise InvalidChatGPTURL("URL credentials are not allowed.")

    if parsed.port not in (None, 443):
        raise InvalidChatGPTURL("Custom ports are not allowed.")

    match = SHARE_PATH_PATTERN.fullmatch(parsed.path)

    if not match:
        raise InvalidChatGPTURL(
            "Invalid ChatGPT shared conversation URL."
        )

    share_id = match.group(1)

    return f"https://{ALLOWED_HOST}/share/{share_id}"