from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_embedding_client
from app.api.schemas import (
    DeleteIndexResponse,
    IndexAllResponse,
    IndexConversationCounts,
    IndexConversationResponse,
    IndexResultResponse,
    IndexStatusResponse,
    RebuildIndexResponse,
)
from app.database.connection import get_db
from app.embeddings.ollama_embeddings import (
    EmbeddingResponseError,
    OllamaEmbeddingClient,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)
from app.processing.indexing_service import (
    ConversationNotFoundError,
    IndexAllResult,
    IndexConfigurationError,
    IndexingBusyError,
    IndexingError,
    IndexingService,
    NoIndexableContentError,
)
from app.vectorstore.chroma_store import (
    ChromaStore,
    VectorStoreConfigurationError,
    VectorStoreError,
    VectorStoreUnavailableError,
    get_chroma_store,
)


router = APIRouter(
    prefix="/index",
    tags=["Indexing"],
)


def get_indexing_service(
    db: Session = Depends(get_db),
    embeddings: OllamaEmbeddingClient = Depends(get_embedding_client),
    store: ChromaStore = Depends(get_chroma_store),
) -> IndexingService:
    return IndexingService(db, embeddings, store)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, ConversationNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if isinstance(exc, (IndexingBusyError, IndexConfigurationError)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if isinstance(exc, NoIndexableContentError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if isinstance(
        exc,
        (
            OllamaUnavailableError,
            OllamaModelNotFoundError,
        ),
    ):
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if isinstance(exc, EmbeddingResponseError):
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an invalid embedding response.",
        ) from exc

    if isinstance(exc, (VectorStoreUnavailableError,)):
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if isinstance(exc, VectorStoreConfigurationError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if isinstance(exc, VectorStoreError):
        raise HTTPException(
            status_code=500,
            detail="ChromaDB operation failed.",
        ) from exc

    if isinstance(exc, IndexingError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(
        status_code=500,
        detail="Indexing failed.",
    ) from exc


def _build_all_response(result: IndexAllResult) -> IndexAllResponse:
    return IndexAllResponse(
        status=result.status,
        total=result.total,
        indexed=result.indexed,
        skipped=result.skipped,
        failed=result.failed,
        results=[
            IndexResultResponse(
                conversation_id=item.conversation_id,
                status=item.status,
                chunks=item.chunks,
                error=item.error,
            )
            for item in result.results
        ],
    )


# Static routes must be declared before /{conversation_id}.


@router.post("/all", response_model=IndexAllResponse)
def index_all_conversations(
    force: bool = Query(False),
    limit: int | None = Query(None, ge=1, le=1000),
    fail_fast: bool = Query(False),
    service: IndexingService = Depends(get_indexing_service),
):
    try:
        result = service.index_all(
            force=force,
            limit=limit,
            fail_fast=fail_fast,
        )
    except Exception as exc:
        _raise_http_error(exc)

    return _build_all_response(result)


@router.post("/rebuild", response_model=RebuildIndexResponse)
def rebuild_index(
    fail_fast: bool = Query(False),
    service: IndexingService = Depends(get_indexing_service),
):
    try:
        result = service.rebuild(fail_fast=fail_fast)
    except Exception as exc:
        _raise_http_error(exc)

    response = _build_all_response(result)

    return RebuildIndexResponse(
        **response.model_dump(),
        collection=service.store.collection_name,
    )


@router.get("/status", response_model=IndexStatusResponse)
def index_status(
    service: IndexingService = Depends(get_indexing_service),
):
    status = service.get_status()

    return IndexStatusResponse(
        collection=status.collection,
        embedding_model=status.embedding_model,
        embedding_dimension=status.embedding_dimension,
        chunking_version=status.chunking_version,
        chunk_size_tokens=status.chunk_size_tokens,
        chunk_overlap_tokens=status.chunk_overlap_tokens,
        chunk_min_tokens=status.chunk_min_tokens,
        token_counting=status.token_counting,
        conversations=IndexConversationCounts(
            total=status.total,
            indexed=status.indexed,
            not_indexed=status.not_indexed,
            indexing=status.indexing,
            failed=status.failed,
            stale=status.stale,
        ),
        chunks_recorded=status.chunks_recorded,
        vectors=status.vectors,
        vector_store_available=status.vector_store_available,
        vector_store_error=status.vector_store_error,
        rebuild_required=status.rebuild_required,
        rebuild_reason=status.rebuild_reason,
    )


@router.post(
    "/{conversation_id}",
    response_model=IndexConversationResponse,
)
def index_conversation(
    conversation_id: str,
    force: bool = Query(False),
    service: IndexingService = Depends(get_indexing_service),
):
    try:
        result = service.index_conversation(
            conversation_id,
            force=force,
        )
    except Exception as exc:
        _raise_http_error(exc)

    return IndexConversationResponse(
        conversation_id=result.conversation_id,
        status=result.status,
        chunks=result.chunks,
        embedding_model=service.config.OLLAMA_EMBED_MODEL,
        chunking_version=service.config.CHUNKING_VERSION,
        indexed_at=result.indexed_at,
    )


@router.delete(
    "/{conversation_id}",
    response_model=DeleteIndexResponse,
)
def delete_conversation_index(
    conversation_id: str,
    service: IndexingService = Depends(get_indexing_service),
):
    try:
        deleted = service.delete_index(conversation_id)
    except Exception as exc:
        _raise_http_error(exc)

    return DeleteIndexResponse(
        conversation_id=conversation_id,
        status="not_indexed",
        deleted_chunks=deleted,
    )
