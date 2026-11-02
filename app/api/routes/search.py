from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_retriever
from app.api.schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)
from app.embeddings.ollama_embeddings import (
    EmbeddingResponseError,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)
from app.rag.retriever import SemanticRetriever
from app.vectorstore.chroma_store import (
    VectorStoreConfigurationError,
    VectorStoreError,
    VectorStoreUnavailableError,
)

router = APIRouter(tags=["Search"])


@router.post("/search", response_model=SearchResponse)
def semantic_search(
    payload: SearchRequest,
    retriever: SemanticRetriever = Depends(get_retriever),
):
    try:
        hits = retriever.search(
            payload.query,
            limit=payload.limit,
            conversation_id=payload.conversation_id,
        )
    except (
        OllamaUnavailableError,
        OllamaModelNotFoundError,
        VectorStoreUnavailableError,
    ) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EmbeddingResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an invalid embedding response.",
        ) from exc
    except VectorStoreConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except VectorStoreError as exc:
        raise HTTPException(
            status_code=500,
            detail="ChromaDB operation failed.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    results = [
        SearchResultItem(
            conversation_id=hit.conversation_id,
            conversation_title=hit.conversation_title,
            role=hit.role,
            message_position=hit.message_position,
            chunk_index=hit.chunk_index,
            text=hit.text,
            distance=hit.distance,
        )
        for hit in hits
    ]

    return SearchResponse(
        query=payload.query,
        total=len(results),
        results=results,
    )
