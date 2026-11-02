from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.ingestion.url_validator import (
    validate_chatgpt_url,
    InvalidChatGPTURL
)


MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_REDIRECTS = 3
REQUEST_TIMEOUT = 20.0


class FetchError(Exception):
    """Base exception for webpage fetching errors."""


class FetchTimeoutError(FetchError):
    """Raised when the request times out."""


class FetchHTTPError(FetchError):
    """Raised when the server returns an HTTP error."""


class FetchRedirectError(FetchError):
    """Raised when a redirect is unsafe or excessive."""


class FetchContentError(FetchError):
    """Raised when the response is not valid HTML."""


@dataclass
class FetchedPage:
    url: str
    status_code: int
    content_type: str
    html: str


async def fetch_shared_page(
    url: str,
    client: httpx.AsyncClient | None = None
) -> FetchedPage:

    # Validate the original URL
    current_url = validate_chatgpt_url(url)

    owns_client = client is None

    if owns_client:
        client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            headers={
                "User-Agent": (
                    "ChatVaultAI/0.1 "
                    "(public conversation importer)"
                ),
                "Accept": "text/html,application/xhtml+xml"
            }
        )

    try:
        for redirect_count in range(MAX_REDIRECTS + 1):

            async with client.stream(
                "GET",
                current_url
            ) as response:

                # Handle redirects manually
                if response.status_code in (301, 302, 303, 307, 308):

                    location = response.headers.get("location")

                    if not location:
                        raise FetchRedirectError(
                            "Redirect location is missing."
                        )

                    if redirect_count >= MAX_REDIRECTS:
                        raise FetchRedirectError(
                            "Maximum redirects exceeded."
                        )

                    next_url = urljoin(current_url, location)

                    try:
                        current_url = validate_chatgpt_url(next_url)
                    except InvalidChatGPTURL as exc:
                        raise FetchRedirectError(
                            "Redirect to an unsupported URL was blocked."
                        ) from exc

                    continue

                # HTTP errors
                if response.status_code >= 400:
                    raise FetchHTTPError(
                        f"ChatGPT returned HTTP {response.status_code}."
                    )

                # Only accept HTML
                content_type = response.headers.get(
                    "content-type", ""
                ).lower()

                if not (
                    "text/html" in content_type
                    or "application/xhtml+xml" in content_type
                ):
                    raise FetchContentError(
                        f"Expected HTML, received: {content_type or 'unknown'}"
                    )

                # Read response with a size limit
                chunks = []
                total_size = 0

                async for chunk in response.aiter_bytes():

                    total_size += len(chunk)

                    if total_size > MAX_RESPONSE_SIZE:
                        raise FetchContentError(
                            "Response exceeds the 5 MB size limit."
                        )

                    chunks.append(chunk)

                raw_html = b"".join(chunks)

                html = raw_html.decode(
                    response.encoding or "utf-8",
                    errors="replace"
                )

                return FetchedPage(
                    url=str(response.url),
                    status_code=response.status_code,
                    content_type=content_type,
                    html=html
                )

        raise FetchRedirectError("Unable to resolve redirects.")

    except httpx.TimeoutException as exc:
        raise FetchTimeoutError(
            "ChatGPT request timed out."
        ) from exc

    except httpx.RequestError as exc:
        raise FetchError(
            f"Unable to fetch ChatGPT page: {exc}"
        ) from exc

    finally:
        if owns_client:
            await client.aclose()