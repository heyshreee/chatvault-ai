from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

class ImportURLRequest(BaseModel):
    url: HttpUrl


class MessageResponse(BaseModel):
    role: str
    content: str
    position: int


class ImportURLResponse(BaseModel):
    status: str
    conversation_id: str
    title: str
    message_count: int
    messages: list[MessageResponse]

class StoredMessageResponse(BaseModel):
    role: str
    content: str
    position: int


class ConversationDetailResponse(BaseModel):
    conversation_id: str
    title: str
    source_url: str
    created_at: datetime
    message_count: int
    messages: list[StoredMessageResponse]


class ConversationListItem(BaseModel):
    conversation_id: str
    title: str
    created_at: datetime
    message_count: int


class ConversationListResponse(BaseModel):
    total: int
    items: list[ConversationListItem]


# --------------------------------------------------
# Indexing
# --------------------------------------------------

class IndexConversationResponse(BaseModel):
    conversation_id: str
    status: Literal["indexed", "already_indexed"]
    chunks: int
    embedding_model: str
    chunking_version: str
    indexed_at: datetime | None = None


class IndexResultResponse(BaseModel):
    conversation_id: str
    status: Literal["indexed", "already_indexed", "failed"]
    chunks: int = 0
    error: str | None = None


class IndexAllResponse(BaseModel):
    status: Literal["completed", "partial", "failed", "nothing_to_do"]
    total: int
    indexed: int
    skipped: int
    failed: int
    results: list[IndexResultResponse]


class RebuildIndexResponse(IndexAllResponse):
    collection: str


class IndexConversationCounts(BaseModel):
    total: int
    indexed: int
    not_indexed: int
    indexing: int
    failed: int
    stale: int


class IndexStatusResponse(BaseModel):
    collection: str
    embedding_model: str
    embedding_dimension: int | None
    chunking_version: str
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    chunk_min_tokens: int
    token_counting: str
    conversations: IndexConversationCounts
    chunks_recorded: int
    vectors: int | None
    vector_store_available: bool
    vector_store_error: str | None = None
    rebuild_required: bool
    rebuild_reason: str | None = None


class DeleteIndexResponse(BaseModel):
    conversation_id: str
    status: Literal["not_indexed"]
    deleted_chunks: int


# --------------------------------------------------
# Conversation management and dashboard
# --------------------------------------------------

class DeleteConversationResponse(BaseModel):
    conversation_id: str
    status: Literal["deleted"]
    deleted_messages: int
    deleted_vectors: int | None = None


class DashboardStatsResponse(BaseModel):
    conversations_total: int
    messages_total: int
    indexed_conversations: int
    not_indexed_conversations: int
    indexing_conversations: int
    failed_conversations: int
    stale_conversations: int
    chunks_indexed: int
    vectors: int | None = None
    vector_store_available: bool
    vector_store_error: str | None = None
    recent_imports: list[ConversationListItem]


# --------------------------------------------------
# Semantic search
# --------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    conversation_id: str | None = None

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Query cannot be blank.")

        return value


class SearchResultItem(BaseModel):
    conversation_id: str
    conversation_title: str
    role: str
    message_position: int
    chunk_index: int
    text: str
    distance: float


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultItem]


# --------------------------------------------------
# Retrieval-augmented chat
# --------------------------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Message cannot be blank.")

        return value


class ChatSourceItem(SearchResultItem):
    index: int


class ChatResponse(BaseModel):
    status: Literal["answered", "no_sources"]
    answer: str
    model: str | None = None
    sources: list[ChatSourceItem]


# --------------------------------------------------
# System and model status
# --------------------------------------------------

class OllamaModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class OllamaStatus(BaseModel):
    base_url: str
    available: bool
    error: str | None = None


class ModelAvailability(BaseModel):
    name: str
    available: bool


class VectorStoreStatus(BaseModel):
    collection: str
    available: bool
    vectors: int | None = None
    embedding_dimension: int | None = None
    error: str | None = None


class DatabaseStatus(BaseModel):
    engine: Literal["sqlite"]
    conversations: int
    messages: int


class IndexSummary(BaseModel):
    total: int
    indexed: int
    not_indexed: int
    indexing: int
    failed: int
    stale: int
    chunks_recorded: int
    rebuild_required: bool
    rebuild_reason: str | None = None


class ModelStatusResponse(BaseModel):
    ollama: OllamaStatus
    chat_model: ModelAvailability
    embedding_model: ModelAvailability
    installed_models: list[OllamaModelInfo]
    vector_store: VectorStoreStatus
    database: DatabaseStatus
    index: IndexSummary