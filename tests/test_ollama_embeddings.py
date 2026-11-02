import json

import httpx
import pytest

from app.embeddings.ollama_embeddings import (
    EmbeddingResponseError,
    OllamaEmbeddingClient,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)


def make_client(handler, **kwargs):
    options = {
        "base_url": "http://ollama.test",
        "model": "nomic-embed-text",
        "timeout": 5,
        "batch_size": 16,
        "max_retries": 0,
        "retry_delay": 0,
    }
    options.update(kwargs)

    return OllamaEmbeddingClient(
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
        ),
        **options,
    )


def test_embedding_success():
    def handler(request):
        assert request.url.path == "/api/embed"
        payload = json.loads(request.content)
        assert payload["model"] == "nomic-embed-text"
        assert payload["input"] == ["first", "second"]

        return httpx.Response(
            200,
            json={
                "model": "nomic-embed-text",
                "embeddings": [
                    [0.1, 0.2, 0.3],
                    [0.4, 0.5, 0.6],
                ],
            },
            request=request,
        )

    client = make_client(handler)
    result = client.embed_texts(["first", "second"])

    assert result.dimension == 3
    assert result.model == "nomic-embed-text"
    assert len(result.vectors) == 2
    assert result.vectors[1] == [0.4, 0.5, 0.6]


def test_empty_input_returns_empty_batch():
    client = make_client(lambda request: httpx.Response(500))

    result = client.embed_texts([])

    assert result.vectors == []
    assert result.dimension == 0


def test_batching_preserves_order():
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload["input"])
        inputs = payload["input"]

        return httpx.Response(
            200,
            json={
                "embeddings": [
                    [float(len(text)), 0.0]
                    for text in inputs
                ],
            },
            request=request,
        )

    client = make_client(handler, batch_size=2)
    result = client.embed_texts(["a", "bb", "ccc"])

    assert requests == [["a", "bb"], ["ccc"]]
    assert result.vectors == [[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]


def test_invalid_embedding_count_is_rejected():
    def handler(request):
        return httpx.Response(
            200,
            json={"embeddings": [[0.1, 0.2]]},
            request=request,
        )

    with pytest.raises(EmbeddingResponseError):
        make_client(handler).embed_texts(["one", "two"])


def test_inconsistent_dimensions_are_rejected():
    def handler(request):
        return httpx.Response(
            200,
            json={"embeddings": [[0.1, 0.2], [0.3]]},
            request=request,
        )

    with pytest.raises(EmbeddingResponseError):
        make_client(handler).embed_texts(["one", "two"])


def test_model_not_found_is_actionable():
    def handler(request):
        return httpx.Response(
            404,
            json={"error": "model not found"},
            request=request,
        )

    with pytest.raises(OllamaModelNotFoundError) as exc_info:
        make_client(handler).embed_texts(["secret conversation text"])

    message = str(exc_info.value)
    assert "ollama pull nomic-embed-text" in message
    assert "secret conversation text" not in message


def test_unavailable_ollama_is_reported():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(OllamaUnavailableError):
        make_client(handler).embed_texts(["hello"])


def test_retry_recovers_from_transient_error():
    calls = []

    def handler(request):
        calls.append(request)

        if len(calls) == 1:
            return httpx.Response(503, request=request)

        return httpx.Response(
            200,
            json={"embeddings": [[0.1, 0.2]]},
            request=request,
        )

    client = make_client(handler, max_retries=1, retry_delay=0)
    result = client.embed_texts(["hello"])

    assert len(calls) == 2
    assert result.dimension == 2


def test_model_availability_check():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "nomic-embed-text:latest"},
                ],
            },
            request=request,
        )

    make_client(handler).assert_model_available()


def test_missing_model_availability_check():
    def handler(request):
        return httpx.Response(
            200,
            json={"models": [{"name": "another-model:latest"}]},
            request=request,
        )

    with pytest.raises(OllamaModelNotFoundError):
        make_client(handler).assert_model_available()
