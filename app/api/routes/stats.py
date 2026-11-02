from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes.indexing import get_indexing_service
from app.api.schemas import (
    ConversationListItem,
    DashboardStatsResponse,
)
from app.database.connection import get_db
from app.database.repository import (
    get_conversations,
    get_database_counts,
)
from app.processing.indexing_service import IndexingService

router = APIRouter(tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats(
    db: Session = Depends(get_db),
    service: IndexingService = Depends(get_indexing_service),
):
    counts = get_database_counts(db)
    status = service.get_status()
    recent = get_conversations(db, skip=0, limit=5)

    return DashboardStatsResponse(
        conversations_total=counts["conversations"],
        messages_total=counts["messages"],
        indexed_conversations=status.indexed,
        not_indexed_conversations=status.not_indexed,
        indexing_conversations=status.indexing,
        failed_conversations=status.failed,
        stale_conversations=status.stale,
        chunks_indexed=status.chunks_recorded,
        vectors=status.vectors,
        vector_store_available=status.vector_store_available,
        vector_store_error=status.vector_store_error,
        recent_imports=[
            ConversationListItem(
                conversation_id=item.conversation_id,
                title=item.title,
                created_at=item.created_at,
                message_count=len(item.messages),
            )
            for item in recent
        ],
    )
