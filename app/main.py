from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

from app.api.routes.health import router as health_router
from app.api.routes.import_chat import router as import_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.exports import router as exports_router
from app.api.routes.indexing import router as indexing_router
from app.api.routes.stats import router as stats_router
from app.api.routes.search import router as search_router
from app.api.routes.chat import router as chat_router
from app.api.routes.system import router as system_router

from app.database.connection import SessionLocal, init_db
from app.database.repository import mark_interrupted_index_states

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    db = SessionLocal()

    try:
        mark_interrupted_index_states(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health API
app.include_router(
    health_router,
    prefix=settings.API_V1_PREFIX
)


# Conversation import API
app.include_router(
    import_router,
    prefix=settings.API_V1_PREFIX
)

app.include_router(
    conversations_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    exports_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    indexing_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    stats_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    search_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    chat_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    system_router,
    prefix=settings.API_V1_PREFIX,
)

@app.get("/")
async def root():

    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "documentation": "/docs"
    }