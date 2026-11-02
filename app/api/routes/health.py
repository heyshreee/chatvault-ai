from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(
    tags=["Health"]
)


@router.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION
    }