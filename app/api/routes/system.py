from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_chat_client
from app.api.routes.indexing import get_indexing_service
from app.api.schemas import (
    DatabaseStatus,
    IndexSummary,
    ModelAvailability,
    ModelStatusResponse,
    OllamaModelInfo,
    OllamaStatus,
    VectorStoreStatus,
)
from app.core.config import settings
from app.database.connection import get_db
from app.database.repository import get_database_counts
from app.processing.indexing_service import IndexingService
from app.rag.ollama_chat import (
    OllamaChatClient,
    OllamaChatError,
    OllamaChatResponseError,
    OllamaChatUnavailableError,
    model_is_installed,
)

router = APIRouter(prefix="/models", tags=["System"])


@router.get("/status", response_model=ModelStatusResponse)
def model_status(
    db: Session = Depends(get_db),
    service: IndexingService = Depends(get_indexing_service),
    chat: OllamaChatClient = Depends(get_chat_client),
):
    index_status = service.get_status()
    counts = get_database_counts(db)

    installed: list[OllamaModelInfo] = []
    ollama_available = True
    ollama_error = None

    try:
        installed = [
            OllamaModelInfo(
                name=model.name,
                size=model.size,
                modified_at=model.modified_at,
            )
            for model in chat.list_models()
        ]
    except OllamaChatError as exc:
        ollama_available = False
        ollama_error = _public_ollama_error(exc)

    installed_names = [model.name for model in installed]
    chat_available = ollama_available and any(
        model_is_installed(settings.OLLAMA_CHAT_MODEL, name)
        for name in installed_names
    )
    embedding_available = ollama_available and any(
        model_is_installed(settings.OLLAMA_EMBED_MODEL, name)
        for name in installed_names
    )

    return ModelStatusResponse(
        ollama=OllamaStatus(
            base_url=settings.OLLAMA_BASE_URL.rstrip("/"),
            available=ollama_available,
            error=ollama_error,
        ),
        chat_model=ModelAvailability(
            name=settings.OLLAMA_CHAT_MODEL,
            available=chat_available,
        ),
        embedding_model=ModelAvailability(
            name=settings.OLLAMA_EMBED_MODEL,
            available=embedding_available,
        ),
        installed_models=installed,
        vector_store=VectorStoreStatus(
            collection=index_status.collection,
            available=index_status.vector_store_available,
            vectors=index_status.vectors,
            embedding_dimension=index_status.embedding_dimension,
            error=index_status.vector_store_error,
        ),
        database=DatabaseStatus(
            engine="sqlite",
            conversations=counts["conversations"],
            messages=counts["messages"],
        ),
        index=IndexSummary(
            total=index_status.total,
            indexed=index_status.indexed,
            not_indexed=index_status.not_indexed,
            indexing=index_status.indexing,
            failed=index_status.failed,
            stale=index_status.stale,
            chunks_recorded=index_status.chunks_recorded,
            rebuild_required=index_status.rebuild_required,
            rebuild_reason=index_status.rebuild_reason,
        ),
    )


def _public_ollama_error(exc: OllamaChatError) -> str:
    if isinstance(exc, OllamaChatUnavailableError):
        return "Ollama is unavailable. Start Ollama and try again."

    if isinstance(exc, OllamaChatResponseError):
        return "Ollama returned an invalid model list."

    return "Ollama status check failed."
