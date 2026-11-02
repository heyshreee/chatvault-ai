from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_chat_service
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSourceItem,
)
from app.embeddings.ollama_embeddings import (
    EmbeddingResponseError,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)
from app.rag.chat_service import ChatService
from app.rag.ollama_chat import (
    OllamaChatError,
    OllamaChatModelNotFoundError,
    OllamaChatResponseError,
    OllamaChatUnavailableError,
)
from app.vectorstore.chroma_store import (
    VectorStoreConfigurationError,
    VectorStoreError,
    VectorStoreUnavailableError,
)

router = APIRouter(tags=["AI Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
):
    try:
        result = service.answer(
            question=payload.message,
            history=[
                {"role": turn.role, "content": turn.content}
                for turn in payload.history
            ],
            top_k=payload.top_k,
        )
    except (OllamaChatModelNotFoundError, OllamaChatUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OllamaChatResponseError as exc:
        raise HTTPException(
            status_code=502,
            detail="Ollama returned an invalid chat response.",
        ) from exc
    except OllamaChatError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
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

    return ChatResponse(
        status=result.status,
        answer=result.answer,
        model=result.model,
        sources=[
            ChatSourceItem(
                index=index,
                conversation_id=source.conversation_id,
                conversation_title=source.conversation_title,
                role=source.role,
                message_position=source.message_position,
                chunk_index=source.chunk_index,
                text=source.text,
                distance=source.distance,
            )
            for index, source in enumerate(result.sources, start=1)
        ],
    )
