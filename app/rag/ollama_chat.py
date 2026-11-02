import time
from dataclasses import dataclass

import httpx

from app.core.config import settings


class OllamaChatError(Exception):
    """Base exception for Ollama chat failures."""


class OllamaChatUnavailableError(OllamaChatError):
    """Raised when Ollama cannot be reached."""


class OllamaChatModelNotFoundError(OllamaChatError):
    """Raised when the configured chat model is missing."""


class OllamaChatResponseError(OllamaChatError):
    """Raised when Ollama returns an invalid chat response."""


@dataclass(frozen=True)
class OllamaModel:
    name: str
    size: int | None = None
    modified_at: str | None = None


@dataclass(frozen=True)
class ChatCompletion:
    content: str
    model: str


def model_is_installed(configured: str, installed: str) -> bool:
    """Treat an unversioned model name as matching its latest tag."""

    return installed == configured or installed.startswith(f"{configured}:")


class OllamaChatClient:
    """Minimal non-streaming Ollama chat client."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
        client: httpx.Client | None = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_CHAT_MODEL
        self.timeout = timeout or settings.OLLAMA_CHAT_TIMEOUT
        self.temperature = (
            settings.OLLAMA_CHAT_TEMPERATURE
            if temperature is None
            else temperature
        )

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

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # --------------------------------------------------
    # Model discovery
    # --------------------------------------------------

    def list_models(self) -> list[OllamaModel]:
        response = self._request("GET", f"{self.base_url}/api/tags")

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaChatResponseError(
                "Ollama returned an invalid model list."
            ) from exc

        models = data.get("models")

        if not isinstance(models, list):
            raise OllamaChatResponseError(
                "Ollama returned an invalid model list."
            )

        result: list[OllamaModel] = []

        for item in models:
            if not isinstance(item, dict):
                continue

            name = item.get("name") or item.get("model")

            if not isinstance(name, str) or not name:
                continue

            size = item.get("size")
            modified_at = item.get("modified_at")

            result.append(
                OllamaModel(
                    name=name,
                    size=size if isinstance(size, int) else None,
                    modified_at=(
                        modified_at
                        if isinstance(modified_at, str)
                        else None
                    ),
                )
            )

        return result

    def assert_model_available(self) -> None:
        models = self.list_models()
        names = [item.name for item in models]

        if not any(
            model_is_installed(self.model, name)
            for name in names
        ):
            raise OllamaChatModelNotFoundError(
                f"Chat model '{self.model}' is not available. "
                f"Run: ollama pull {self.model}"
            )

    # --------------------------------------------------
    # Chat
    # --------------------------------------------------

    def chat(self, messages: list[dict[str, str]]) -> ChatCompletion:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        response = self._request(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaChatResponseError(
                "Ollama returned an invalid chat response."
            ) from exc

        message = data.get("message")

        if not isinstance(message, dict):
            raise OllamaChatResponseError(
                "Ollama returned an invalid chat response."
            )

        content = message.get("content")

        if not isinstance(content, str):
            raise OllamaChatResponseError(
                "Ollama returned an invalid chat response."
            )

        content = content.strip()

        if not content:
            raise OllamaChatResponseError(
                "Ollama returned an empty chat response."
            )

        response_model = data.get("model")

        if not isinstance(response_model, str) or not response_model:
            response_model = self.model

        return ChatCompletion(
            content=content,
            model=response_model,
        )

    # --------------------------------------------------
    # HTTP
    # --------------------------------------------------

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(2):
            try:
                response = self._client.request(method, url, **kwargs)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc

                if attempt == 0:
                    time.sleep(0.25)
                    continue

                raise OllamaChatUnavailableError(
                    "Ollama is unavailable. Start Ollama and try again."
                ) from exc

            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                time.sleep(0.25)
                continue

            if response.status_code == 404:
                raise OllamaChatModelNotFoundError(
                    f"Chat model '{self.model}' is not available. "
                    f"Run: ollama pull {self.model}"
                )

            if response.status_code >= 400:
                error_text = self._error_message(response)

                if (
                    "not found" in error_text.lower()
                    or "model" in error_text.lower()
                ):
                    raise OllamaChatModelNotFoundError(
                        f"Chat model '{self.model}' is not available. "
                        f"Run: ollama pull {self.model}"
                    )

                raise OllamaChatError(
                    f"Ollama rejected the request "
                    f"(HTTP {response.status_code})."
                )

            return response

        raise OllamaChatUnavailableError(
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
