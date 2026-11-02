
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.database.models import (
    ConversationIndexStateModel,
    ConversationModel,
    MessageModel,
)
from app.ingestion.extractor import Conversation
from app.processing.index_status import IndexStatus


def save_conversation(
    db: Session,
    conversation: Conversation,
) -> tuple[ConversationModel, bool]:
    """
    Save a conversation and its messages.

    Returns:
        (conversation, created)

    If the conversation already exists, return the existing record.
    """

    existing = db.scalar(
        select(ConversationModel)
        .where(
            ConversationModel.conversation_id
            == conversation.conversation_id
        )
        .options(selectinload(ConversationModel.messages))
    )

    if existing:
        return existing, False

    db_conversation = ConversationModel(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        source_url=conversation.source_url,
        messages=[
            MessageModel(
                role=message.role,
                content=message.content,
                position=message.position,
            )
            for message in conversation.messages
        ],
    )

    try:
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)

        return db_conversation, True

    except Exception:
        db.rollback()
        raise


def get_conversation(
    db: Session,
    conversation_id: str,
) -> ConversationModel | None:

    return db.scalar(
        select(ConversationModel)
        .where(
            ConversationModel.conversation_id == conversation_id
        )
        .options(selectinload(ConversationModel.messages))
    )


def get_conversations(
    db: Session,
    skip: int = 0,
    limit: int = 20,
) -> list[ConversationModel]:

    statement = (
        select(ConversationModel)
        .options(selectinload(ConversationModel.messages))
        .order_by(ConversationModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).unique().all())


def get_database_counts(db: Session) -> dict[str, int]:
    conversations = db.scalar(
        select(func.count()).select_from(ConversationModel)
    ) or 0
    messages = db.scalar(
        select(func.count()).select_from(MessageModel)
    ) or 0

    return {
        "conversations": int(conversations),
        "messages": int(messages),
    }


def get_conversation_titles(
    db: Session,
    conversation_ids: list[str],
) -> dict[str, str]:
    if not conversation_ids:
        return {}

    rows = db.execute(
        select(
            ConversationModel.conversation_id,
            ConversationModel.title,
        ).where(
            ConversationModel.conversation_id.in_(conversation_ids)
        )
    ).all()

    return {conversation_id: title for conversation_id, title in rows}


def delete_conversation(
    db: Session,
    conversation_id: str,
) -> bool:

    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        return False

    try:
        db.delete(conversation)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Index state
# --------------------------------------------------

def get_all_conversation_ids(db: Session) -> list[str]:
    statement = (
        select(ConversationModel.conversation_id)
        .order_by(ConversationModel.id)
    )

    return list(db.scalars(statement).all())


def get_index_state(
    db: Session,
    conversation_db_id: int,
) -> ConversationIndexStateModel | None:

    return db.get(ConversationIndexStateModel, conversation_db_id)


def get_or_create_index_state(
    db: Session,
    conversation_db_id: int,
) -> ConversationIndexStateModel:

    state = get_index_state(db, conversation_db_id)

    if state is None:
        state = ConversationIndexStateModel(
            conversation_db_id=conversation_db_id,
            status=IndexStatus.NOT_INDEXED.value,
        )
        db.add(state)
        db.flush()

    return state


def mark_interrupted_index_states(db: Session) -> int:
    """Mark index attempts left running after a server restart as failed."""

    result = db.execute(
        update(ConversationIndexStateModel)
        .where(ConversationIndexStateModel.status == IndexStatus.INDEXING.value)
        .values(
            status=IndexStatus.FAILED.value,
            last_error="Indexing was interrupted before completion.",
            updated_at=func.now(),
        )
    )
    db.commit()

    return int(result.rowcount or 0)


def reset_index_states(db: Session) -> int:
    """Reset every conversation's index state."""

    result = db.execute(
        update(ConversationIndexStateModel)
        .values(
            status=IndexStatus.NOT_INDEXED.value,
            signature=None,
            chunk_count=0,
            embedding_model=None,
            embedding_dimension=None,
            indexed_at=None,
            last_error=None,
            updated_at=func.now(),
        )
    )
    db.commit()

    return int(result.rowcount or 0)


def get_index_counts(
    db: Session,
    current_signature: str,
) -> dict:
    """Return conversation index counts for the status endpoint."""

    total_conversations = db.scalar(
        select(func.count()).select_from(ConversationModel)
    ) or 0

    rows = db.execute(
        select(
            ConversationIndexStateModel.status,
            func.count(),
        ).group_by(ConversationIndexStateModel.status)
    ).all()

    counts = {status: count for status, count in rows}
    total_states = sum(counts.values())

    stale = db.scalar(
        select(func.count())
        .select_from(ConversationIndexStateModel)
        .where(
            ConversationIndexStateModel.status == IndexStatus.INDEXED.value,
            or_(
                ConversationIndexStateModel.signature.is_(None),
                ConversationIndexStateModel.signature != current_signature,
            ),
        )
    ) or 0

    indexed_total = counts.get(IndexStatus.INDEXED.value, 0)
    indexed_current = max(0, indexed_total - stale)

    chunks_recorded = db.scalar(
        select(
            func.coalesce(func.sum(ConversationIndexStateModel.chunk_count), 0)
        ).where(
            ConversationIndexStateModel.status == IndexStatus.INDEXED.value
        )
    ) or 0

    missing_states = max(0, total_conversations - total_states)

    not_indexed = counts.get(IndexStatus.NOT_INDEXED.value, 0)
    not_indexed += missing_states

    return {
        "total": total_conversations,
        "indexed": indexed_current,
        "not_indexed": not_indexed,
        "indexing": counts.get(IndexStatus.INDEXING.value, 0),
        "failed": counts.get(IndexStatus.FAILED.value, 0),
        "stale": int(stale),
        "chunks_recorded": int(chunks_recorded),
    }
