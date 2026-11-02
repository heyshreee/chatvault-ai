from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import import_chat
from app.ingestion.fetcher import FetchedPage, FetchError


client = TestClient(app)

FIXTURE = Path(
    "tests/fixtures/sample_conversation.html"
)

TEST_URL = "https://chatgpt.com/share/abc123"


def test_import_conversation_success(monkeypatch):

    html = FIXTURE.read_text(encoding="utf-8")

    async def mock_fetcher(url):

        return FetchedPage(
            url=url,
            status_code=200,
            content_type="text/html",
            html=html
        )

    monkeypatch.setattr(
        import_chat,
        "fetch_shared_page",
        mock_fetcher
    )

    response = client.post(
        "/api/v1/import/url",
        json={"url": TEST_URL}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "success"
    assert data["conversation_id"] == "abc123"
    assert data["message_count"] == 4

    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


def test_invalid_url():

    response = client.post(
        "/api/v1/import/url",
        json={"url": "https://google.com"}
    )

    assert response.status_code == 400


def test_fetch_error(monkeypatch):

    async def mock_fetcher(url):
        raise FetchError("Connection failed")

    monkeypatch.setattr(
        import_chat,
        "fetch_shared_page",
        mock_fetcher
    )

    response = client.post(
        "/api/v1/import/url",
        json={"url": TEST_URL}
    )

    assert response.status_code == 502


def test_extraction_error(monkeypatch):

    async def mock_fetcher(url):

        return FetchedPage(
            url=url,
            status_code=200,
            content_type="text/html",
            html="<html><body>No messages</body></html>"
        )

    monkeypatch.setattr(
        import_chat,
        "fetch_shared_page",
        mock_fetcher
    )

    response = client.post(
        "/api/v1/import/url",
        json={"url": TEST_URL}
    )

    assert response.status_code == 502


def test_missing_url():

    response = client.post(
        "/api/v1/import/url",
        json={}
    )

    assert response.status_code == 422