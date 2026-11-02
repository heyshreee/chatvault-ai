import math
import time
from dataclasses import dataclass
from typing import Sequence

import httpx

from app.core.config import settings


class OllamaEmbeddingError(Exception):
    """Base exception for Ollama embedding failures."""


class OllamaUnavailableError(OllamaEmbeddingError):
    """Raised when Ollama cannot be reached."""


class OllamaModelNotFoundError(OllamaEmbeddingError):
    """Raised when the configured embedding model is missing."""


class EmbeddingResponseError(OllamaEmbeddingError):
    """Raised when Ollama returns an invalid embedding response."""


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    model: str
    dimension: int


class OllamaEmbeddingClient:
    """Small client for Ollama's batch embedding endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        batch_size: int | None = None,
        max_retries: int = 2,
        retry_delay: float = 0.25,
        client: httpx.Client | None = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_EMBED_MODEL
        self.timeout = timeout or settings.OLLAMA_EMBED_TIMEOUT
        self.batch_size = batch_size or settings.OLLAMA_EMBED_BATCH_SIZE
        self.max_retries = max(0, max_retries)
        self.retry_delay = max(0.0, retry_delay)

        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(
                self.timeout,
                connect=min(5.0, self.timeout),
            ),
            trust_env=False,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self._owns_client:
            self._client.close()

    # --------------------------------------------------
    # Embedding
    # --------------------------------------------------

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingBatch:
        if not texts:
            return EmbeddingBatch(vectors=[], model=self.model, dimension=0)

        clean_texts = list(texts)

        if any(not isinstance(text, str) or not text.strip() for text in clean_texts):
            raise ValueError("Embedding inputs must be non-empty strings.")

        vectors: list[list[float]] = []
        response_model = self.model

        for start in range(0, len(clean_texts), self.batch_size):
            batch = clean_texts[start:start + self.batch_size]
            batch_vectors, response_model = self._embed_batch(batch)
            vectors.extend(batch_vectors)

        dimension = self._validate_vectors(vectors)

        return EmbeddingBatch(
            vectors=vectors,
            model=response_model,
            dimension=dimension,
        )

    def _embed_batch(
        self,
        texts: list[str],
    ) -> tuple[list[list[float]], str]:
        payload = {
            "model": self.model,
            "input": texts,
        }

        response = self._request_with_retries(
            method="POST",
            url=f"{self.base_url}/api/embed",
            json=payload,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingResponseError(
                "Ollama returned a non-JSON embedding response."
            ) from exc

        embeddings = data.get("embeddings")

        if not isinstance(embeddings, list):
            raise EmbeddingResponseError(
                "Ollama returned an invalid embedding response."
            )

        if len(embeddings) != len(texts):
            raise EmbeddingResponseError(
                "Ollama returned an unexpected number of embeddings."
            )

        vectors = []

        for vector in embeddings:
            if not isinstance(vector, list):
                raise EmbeddingResponseError(
                    "Ollama returned a malformed embedding vector."
                )

            validated = []

            for value in vector:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise EmbeddingResponseError(
                        "Ollama returned a non-numeric embedding value."
                    )

                numeric = float(value)

                if not math.isfinite(numeric):
                    raise EmbeddingResponseError(
                        "Ollama returned a non-finite embedding value."
                    )

                validated.append(numeric)

            vectors.append(validated)

        response_model = data.get("model")

        if not isinstance(response_model, str) or not response_model:
            response_model = self.model

        return vectors, response_model

    @staticmethod
    def _validate_vectors(vectors: list[list[float]]) -> int:
        if not vectors:
            return 0

        dimension = len(vectors[0])

        if dimension == 0:
            raise EmbeddingResponseError(
                "Ollama returned empty embedding vectors."
            )

        for vector in vectors:
            if len(vector) != dimension:
                raise EmbeddingResponseError(
                    "Ollama returned embeddings with inconsistent dimensions."
                )

        return dimension

    # --------------------------------------------------
    # Model availability
    # --------------------------------------------------

    def assert_model_available(self) -> None:
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise OllamaUnavailableError(
                "Ollama is unavailable. Start Ollama and try again."
            ) from exc

        if response.status_code >= 400:
            raise OllamaUnavailableError(
                f"Ollama returned HTTP {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingResponseError(
                "Ollama returned an invalid model list."
            ) from exc

        models = data.get("models")

        if not isinstance(models, list):
            raise EmbeddingResponseError(
                "Ollama returned an invalid model list."
            )

        available_names = {
            item.get("name", "")
            for item in models
            if isinstance(item, dict)
        }

        found = any(
            name == self.model or name.startswith(f"{self.model}:")
            for name in available_names
        )

        if not found:
            raise OllamaModelNotFoundError(
                f"Embedding model '{self.model}' is not available. "
                f"Run: ollama pull {self.model}"
            )

    # --------------------------------------------------
    # HTTP
    # --------------------------------------------------

    def _request_with_retries(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

                raise OllamaUnavailableError(
                    "Ollama is unavailable. Start Ollama and try again."
                ) from exc

            if response.status_code in {429, 500, 502, 503, 504}:
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

                raise OllamaUnavailableError(
                    f"Ollama returned HTTP {response.status_code}."
                )

            if response.status_code == 404:
                raise OllamaModelNotFoundError(
                    f"Embedding model '{self.model}' is not available. "
                    f"Run: ollama pull {self.model}"
                )

            if response.status_code >= 400:
                error_text = self._error_message(response)

                if "not found" in error_text.lower() or "model" in error_text.lower():
                    raise OllamaModelNotFoundError(
                        f"Embedding model '{self.model}' is not available. "
                        f"Run: ollama pull {self.model}"
                    )

                raise OllamaEmbeddingError(
                    f"Ollama rejected the embedding request "
                    f"(HTTP {response.status_code})."
                )

            return response

        raise OllamaUnavailableError(
            "Ollama is unavailable. Start Ollama and try again."
        ) from last_error

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return ""

        if isinstance(data, dict):
            error = data.get("error")

            if isinstance(error, str):
                return error

        return ""
