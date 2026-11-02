
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repository import get_conversation
from app.generators.pdf_generator import generate_pdf
from app.generators.docx_generator import generate_docx

router = APIRouter(
    prefix="/conversations",
    tags=["Document Export"],
)


@router.get("/{conversation_id}/export/pdf")
def export_conversation_pdf(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    try:
        output_path = generate_pdf(conversation)

        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=Path(output_path).name,
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate PDF.",
        )


@router.get("/{conversation_id}/export/docx")
def export_conversation_docx(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    conversation = get_conversation(db, conversation_id)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    try:
        output_path = generate_docx(conversation)

        return FileResponse(
            path=output_path,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            filename=Path(output_path).name,
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate DOCX.",
        )
