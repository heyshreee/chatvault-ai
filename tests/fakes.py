import hashlib

from app.embeddings.ollama_embeddings import (
    EmbeddingBatch,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)
from app.rag.ollama_chat import (
    ChatCompletion,
    OllamaChatModelNotFoundError,
    OllamaChatResponseError,
    OllamaChatUnavailableError,
    OllamaModel,
)


class FakeEmbeddingClient:
    """Deterministic embedding client for tests."""

    def __init__(
        self,
        dimension: int = 8,
        model: str = "fake-embed",
        fail: bool = False,
        unavailable: bool = False,
        model_available: bool = True,
        vectors: list[list[float]] | None = None,
    ):
        self.dimension = dimension
        self.model = model
        self.fail = fail
        self.unavailable = unavailable
        self.model_available = model_available
        self.vectors = vectors
        self.calls: list[list[str]] = []

    def embed_texts(self, texts):
        self.calls.append(list(texts))

        if self.fail:
            raise OllamaUnavailableError("Ollama is unavailable.")

        if self.unavailable:
            raise OllamaUnavailableError("Ollama is unavailable.")

        if self.vectors is not None:
            if len(self.vectors) < len(texts):
                raise AssertionError("Not enough fake vectors.")

            return EmbeddingBatch(
                vectors=self.vectors[:len(texts)],
                model=self.model,
                dimension=len(self.vectors[0]),
            )

        return EmbeddingBatch(
            vectors=[self._vector(text) for text in texts],
            model=self.model,
            dimension=self.dimension,
        )

    def assert_model_available(self):
        if not self.model_available:
            raise OllamaModelNotFoundError(
                "Embedding model is not available."
            )

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()

        return [
            digest[index] / 255.0
            for index in range(self.dimension)
        ]

    def close(self):
        pass


class FakeChatClient:
    """Deterministic Ollama chat client for tests."""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        answer: str = "Reset Shell-GPT and enter the key again [1].",
        models: list[OllamaModel] | None = None,
        fail: bool = False,
        unavailable: bool = False,
        model_available: bool = True,
        response_error: bool = False,
    ):
        self.model = model
        self.answer = answer
        self.fail = fail
        self.unavailable = unavailable
        self.model_available = model_available
        self.response_error = response_error
        self.models = (
            models
            if models is not None
            else [
                OllamaModel(
                    name="llama3.2:3b",
                    size=1_900_000_000,
                    modified_at="2026-01-01T00:00:00Z",
                ),
                OllamaModel(
                    name="nomic-embed-text:latest",
                    size=274_000_000,
                    modified_at="2026-01-01T00:00:00Z",
                ),
            ]
        )
        self.calls: list[list[dict[str, str]]] = []

    def list_models(self):
        if self.fail or self.unavailable:
            raise OllamaChatUnavailableError("Ollama is unavailable.")

        return list(self.models)

    def chat(self, messages):
        self.calls.append(list(messages))

        if self.fail or self.unavailable:
            raise OllamaChatUnavailableError("Ollama is unavailable.")

        if not self.model_available:
            raise OllamaChatModelNotFoundError(
                f"Chat model '{self.model}' is not available."
            )

        if self.response_error:
            raise OllamaChatResponseError(
                "Ollama returned an invalid chat response."
            )

        return ChatCompletion(content=self.answer, model=self.model)

    def close(self):
        pass
