
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ImportURLRequest,
    ImportURLResponse,
    MessageResponse,
)
from app.database.connection import get_db
from app.database.repository import save_conversation
from app.ingestion.url_validator import (
    validate_chatgpt_url,
    InvalidChatGPTURL,
)
from app.ingestion.fetcher import fetch_shared_page, FetchError
from app.ingestion.extractor import (
    extract_conversation,
    ExtractionError,
)

router = APIRouter(
    prefix="/import",
    tags=["Conversation Import"],
)


@router.post(
    "/url",
    response_model=ImportURLResponse,
    status_code=status.HTTP_200_OK,
)
async def import_conversation(
    payload: ImportURLRequest,
    db: Session = Depends(get_db),
):
    # 1. Validate URL
    try:
        validated_url = validate_chatgpt_url(str(payload.url))
    except InvalidChatGPTURL as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # 2. Fetch shared conversation
    try:
        page = await fetch_shared_page(validated_url)
    except FetchError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch shared conversation: {exc}",
        )

    # 3. Extract conversation
    try:
        conversation = extract_conversation(
            html=page.html,
            source_url=validated_url,
        )
    except ExtractionError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to extract conversation: {exc}",
        )

    # 4. Persist conversation and messages
    try:
        saved_conversation, created = save_conversation(
            db,
            conversation,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to save conversation to database.",
        )

    # 5. Return response
    return ImportURLResponse(
        status="success" if created else "already_exists",
        conversation_id=saved_conversation.conversation_id,
        title=saved_conversation.title,
        message_count=len(saved_conversation.messages),
        messages=[
            MessageResponse(
                role=message.role,
                content=message.content,
                position=message.position,
            )
            for message in saved_conversation.messages
        ],
    )
