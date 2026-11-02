import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import ConversationModel
from app.processing.text_cleaner import clean_chatgpt_text
from app.database.repository import (
    delete_conversation as delete_conversation_record,
    get_conversation,
    get_conversations,
)
from app.api.schemas import (
    ConversationDetailResponse,
    ConversationListItem,
    ConversationListResponse,
    DeleteConversationResponse,
    StoredMessageResponse,
)
from app.vectorstore.chroma_store import (
    ChromaStore,
    VectorStoreError,
    get_chroma_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.scalar(
        select(func.count()).select_from(ConversationModel)
    ) or 0

    conversations = get_conversations(db, skip, limit)

    items = [
        ConversationListItem(
            conversation_id=item.conversation_id,
            title=item.title,
            created_at=item.created_at,
            message_count=len(item.messages),
        )
        for item in conversations
    ]

    return ConversationListResponse(
        total=total,
        items=items,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def conversation_detail(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return ConversationDetailResponse(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        source_url=conversation.source_url,
        created_at=conversation.created_at,
        message_count=len(conversation.messages),
        messages=[
            StoredMessageResponse(
                role=message.role,
                content=clean_chatgpt_text(message.content),
                position=message.position,
            )
            for message in conversation.messages
        ],
    )


@router.delete(
    "/{conversation_id}",
    response_model=DeleteConversationResponse,
)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    store: ChromaStore = Depends(get_chroma_store),
):
    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    deleted_messages = len(conversation.messages)
    deleted_vectors: int | None = None

    # SQLite is the source of truth: a vector-store outage must not block
    # deleting the conversation. Any surviving vectors are ignored by search
    # because retrieval verifies conversation IDs against SQLite.
    try:
        deleted_vectors = store.delete_conversation(conversation_id)
    except VectorStoreError as exc:
        logger.warning(
            "Vector cleanup failed for conversation %s: %s",
            conversation_id,
            type(exc).__name__,
        )

    try:
        deleted = delete_conversation_record(db, conversation_id)
    except Exception as exc:
        logger.error(
            "Conversation deletion failed for %s: %s",
            conversation_id,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to delete conversation.",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return DeleteConversationResponse(
        conversation_id=conversation_id,
        status="deleted",
        deleted_messages=deleted_messages,
        deleted_vectors=deleted_vectors,
    )
