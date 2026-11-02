import asyncio

import httpx
import pytest

from app.ingestion.fetcher import (
    fetch_shared_page,
    FetchHTTPError,
    FetchContentError,
    FetchRedirectError
)


TEST_URL = "https://chatgpt.com/share/abc123"


def run(coro):
    return asyncio.run(coro)


def make_client(handler):

    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(
        transport=transport,
        follow_redirects=False
    )


def test_successful_fetch():

    async def handler(request):
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html; charset=utf-8"
            },
            text="<html><body>Hello ChatVault</body></html>",
            request=request
        )

    async def execute():
        async with make_client(handler) as client:

            result = await fetch_shared_page(
                TEST_URL,
                client
            )

            assert result.status_code == 200
            assert "Hello ChatVault" in result.html
            assert result.content_type.startswith("text/html")

    run(execute())


def test_http_error():

    async def handler(request):
        return httpx.Response(
            404,
            request=request
        )

    async def execute():
        async with make_client(handler) as client:

            with pytest.raises(FetchHTTPError):
                await fetch_shared_page(TEST_URL, client)

    run(execute())


def test_non_html_response():

    async def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            text='{"message": "not html"}',
            request=request
        )

    async def execute():
        async with make_client(handler) as client:

            with pytest.raises(FetchContentError):
                await fetch_shared_page(TEST_URL, client)

    run(execute())


def test_external_redirect_blocked():

    async def handler(request):
        return httpx.Response(
            302,
            headers={
                "location": "https://google.com/"
            },
            request=request
        )

    async def execute():
        async with make_client(handler) as client:

            with pytest.raises(FetchRedirectError):
                await fetch_shared_page(TEST_URL, client)

    run(execute())


def test_oversized_response():

    async def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"A" * (5 * 1024 * 1024 + 1),
            request=request
        )

    async def execute():
        async with make_client(handler) as client:

            with pytest.raises(FetchContentError):
                await fetch_shared_page(TEST_URL, client)

    run(execute())