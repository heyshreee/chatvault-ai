import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.database.repository import (
    get_all_conversation_ids,
    get_conversation,
    get_index_counts,
    get_or_create_index_state,
    reset_index_states,
)
from app.embeddings.ollama_embeddings import (
    EmbeddingResponseError,
    OllamaEmbeddingClient,
    OllamaEmbeddingError,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
)
from app.processing.chunker import (
    TOKEN_COUNTING_METHOD,
    Chunk,
    chunk_conversation,
)
from app.processing.index_status import IndexStatus
from app.vectorstore.chroma_store import (
    ChromaStore,
    VectorStoreConfigurationError,
    VectorStoreError,
    VectorStoreUnavailableError,
)


logger = logging.getLogger(__name__)


class IndexingError(Exception):
    """Base exception for indexing failures."""


class ConversationNotFoundError(IndexingError):
    """Raised when a conversation does not exist."""


class IndexingBusyError(IndexingError):
    """Raised when another indexing operation is already running."""


class IndexConfigurationError(IndexingError):
    """Raised when the index must be rebuilt for the current settings."""


class NoIndexableContentError(IndexingError):
    """Raised when a conversation has no usable text."""


@dataclass(frozen=True)
class IndexResult:
    conversation_id: str
    status: str
    chunks: int
    error: str | None = None
    indexed_at: datetime | None = None


@dataclass(frozen=True)
class IndexAllResult:
    status: str
    total: int
    indexed: int
    skipped: int
    failed: int
    results: list[IndexResult]


@dataclass(frozen=True)
class IndexStatusSummary:
    collection: str
    embedding_model: str
    embedding_dimension: int | None
    chunking_version: str
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    chunk_min_tokens: int
    token_counting: str
    total: int
    indexed: int
    not_indexed: int
    indexing: int
    failed: int
    stale: int
    chunks_recorded: int
    vectors: int | None
    vector_store_available: bool
    vector_store_error: str | None
    rebuild_required: bool
    rebuild_reason: str | None


class IndexingService:
    """Coordinate chunking, embeddings, ChromaDB and index state."""

    # Phase 5 runs in a single local process. A non-blocking process-wide
    # lock prevents two index operations from racing.
    _lock = threading.Lock()

    def __init__(
        self,
        db: Session,
        embeddings: OllamaEmbeddingClient,
        store: ChromaStore,
        config: Settings | None = None,
    ):
        self.db = db
        self.embeddings = embeddings
        self.store = store
        self.config = config or settings

    # --------------------------------------------------
    # Public operations
    # --------------------------------------------------

    def index_conversation(
        self,
        conversation_id: str,
        force: bool = False,
    ) -> IndexResult:
        self._acquire_lock()

        try:
            return self._index_conversation_locked(
                conversation_id,
                force=force,
            )
        finally:
            self._lock.release()

    def index_all(
        self,
        force: bool = False,
        limit: int | None = None,
        fail_fast: bool = False,
    ) -> IndexAllResult:
        self._acquire_lock()

        try:
            conversation_ids = self._get_conversation_ids(limit)

            if not conversation_ids:
                return IndexAllResult(
                    status="nothing_to_do",
                    total=0,
                    indexed=0,
                    skipped=0,
                    failed=0,
                    results=[],
                )

            self.embeddings.assert_model_available()

            try:
                self.store.check_model_compatibility(
                    self.config.OLLAMA_EMBED_MODEL
                )
            except VectorStoreConfigurationError as exc:
                raise IndexConfigurationError(str(exc)) from exc

            return self._index_all_locked(
                conversation_ids,
                force=force,
                fail_fast=fail_fast,
            )
        finally:
            self._lock.release()

    def rebuild(
        self,
        fail_fast: bool = False,
    ) -> IndexAllResult:
        self._acquire_lock()

        try:
            self.embeddings.assert_model_available()
            self.store.reset()
            reset_index_states(self.db)

            conversation_ids = self._get_conversation_ids(None)

            if not conversation_ids:
                return IndexAllResult(
                    status="nothing_to_do",
                    total=0,
                    indexed=0,
                    skipped=0,
                    failed=0,
                    results=[],
                )

            return self._index_all_locked(
                conversation_ids,
                force=True,
                fail_fast=fail_fast,
            )
        finally:
            self._lock.release()

    def delete_index(self, conversation_id: str) -> int:
        self._acquire_lock()

        try:
            conversation = get_conversation(self.db, conversation_id)

            if conversation is None:
                raise ConversationNotFoundError(
                    "Conversation not found."
                )

            deleted = self.store.delete_conversation(conversation_id)
            state = get_or_create_index_state(
                self.db,
                conversation.id,
            )

            state.status = IndexStatus.NOT_INDEXED.value
            state.signature = None
            state.chunk_count = 0
            state.embedding_model = None
            state.embedding_dimension = None
            state.indexed_at = None
            state.last_error = None
            self.db.commit()

            return deleted
        finally:
            self._lock.release()

    def get_status(self) -> IndexStatusSummary:
        counts = get_index_counts(self.db, self._signature())
        vector_store_available = True
        vector_store_error = None
        vectors = None
        embedding_dimension = None
        metadata: dict[str, Any] = {}

        try:
            info = self.store.info()
            vectors = info.count
            metadata = info.metadata
            stored_dimension = metadata.get("embedding_dimension")

            if stored_dimension is not None:
                embedding_dimension = int(stored_dimension)
        except VectorStoreError as exc:
            vector_store_available = False
            vector_store_error = self._public_error(exc)

        rebuild_required = False
        rebuild_reason = None
        stored_model = metadata.get("embedding_model")

        if vector_store_available and vectors and vectors > 0:
            if not stored_model:
                rebuild_required = True
                rebuild_reason = (
                    "The vector index has unknown embedding provenance."
                )
            elif stored_model != self.config.OLLAMA_EMBED_MODEL:
                rebuild_required = True
                rebuild_reason = (
                    "The embedding model has changed. Rebuild the index."
                )
            elif metadata.get("embedding_dimension") is None:
                rebuild_required = True
                rebuild_reason = (
                    "The vector index has unknown embedding dimensions."
                )
        elif (
            vector_store_available
            and vectors == 0
            and counts["indexed"] + counts["stale"] > 0
        ):
            rebuild_required = True
            rebuild_reason = (
                "The vector index is empty but conversations are marked "
                "as indexed."
            )

        return IndexStatusSummary(
            collection=self.store.collection_name,
            embedding_model=self.config.OLLAMA_EMBED_MODEL,
            embedding_dimension=embedding_dimension,
            chunking_version=self.config.CHUNKING_VERSION,
            chunk_size_tokens=self.config.CHUNK_SIZE_TOKENS,
            chunk_overlap_tokens=self.config.CHUNK_OVERLAP_TOKENS,
            chunk_min_tokens=self.config.CHUNK_MIN_TOKENS,
            token_counting=TOKEN_COUNTING_METHOD,
            total=counts["total"],
            indexed=counts["indexed"],
            not_indexed=counts["not_indexed"],
            indexing=counts["indexing"],
            failed=counts["failed"],
            stale=counts["stale"],
            chunks_recorded=counts["chunks_recorded"],
            vectors=vectors,
            vector_store_available=vector_store_available,
            vector_store_error=vector_store_error,
            rebuild_required=rebuild_required,
            rebuild_reason=rebuild_reason,
        )

    # --------------------------------------------------
    # Internal operations
    # --------------------------------------------------

    def _index_conversation_locked(
        self,
        conversation_id: str,
        force: bool = False,
    ) -> IndexResult:
        conversation = get_conversation(self.db, conversation_id)

        if conversation is None:
            raise ConversationNotFoundError("Conversation not found.")

        state = get_or_create_index_state(self.db, conversation.id)
        signature = self._signature()

        if state.status == IndexStatus.INDEXING.value:
            raise IndexingBusyError(
                "This conversation is already being indexed."
            )

        try:
            self.store.check_model_compatibility(
                self.config.OLLAMA_EMBED_MODEL
            )
        except VectorStoreConfigurationError as exc:
            raise IndexConfigurationError(str(exc)) from exc

        if (
            not force
            and state.status == IndexStatus.INDEXED.value
            and state.signature == signature
        ):
            # SQLite says this conversation is indexed. Verify that its
            # derived vectors still exist before short-circuiting; ChromaDB
            # can be wiped independently of SQLite.
            stored_chunks = self.store.count_conversation(conversation_id)

            if stored_chunks > 0 and stored_chunks == state.chunk_count:
                return IndexResult(
                    conversation_id=conversation.conversation_id,
                    status="already_indexed",
                    chunks=state.chunk_count,
                    indexed_at=state.indexed_at,
                )

        state.status = IndexStatus.INDEXING.value
        state.last_error = None
        self.db.commit()

        try:
            chunks = chunk_conversation(
                conversation,
                size_tokens=self.config.CHUNK_SIZE_TOKENS,
                overlap_tokens=self.config.CHUNK_OVERLAP_TOKENS,
                min_tokens=self.config.CHUNK_MIN_TOKENS,
                chunking_version=self.config.CHUNKING_VERSION,
            )

            if not chunks:
                raise NoIndexableContentError(
                    "Conversation has no indexable text."
                )

            embedding_inputs = [
                self._build_embedding_text(chunk)
                for chunk in chunks
            ]
            batch = self.embeddings.embed_texts(embedding_inputs)

            self.store.ensure_provenance(
                self.config.OLLAMA_EMBED_MODEL,
                batch.dimension,
            )

            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [
                self._build_metadata(chunk)
                for chunk in chunks
            ]

            # The old vectors are only removed after all new embeddings
            # have been generated successfully.
            self.store.delete_conversation(conversation_id)

            try:
                self.store.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=batch.vectors,
                    metadatas=metadatas,
                )
            except Exception:
                # Best effort cleanup of a partial write.
                try:
                    self.store.delete_conversation(conversation_id)
                except VectorStoreError:
                    pass
                raise

        except (IndexingError, OllamaEmbeddingError, VectorStoreError) as exc:
            message = self._public_error(exc)
            self._mark_failed(state, message)
            logger.warning(
                "Indexing failed for conversation %s: %s",
                conversation_id,
                type(exc).__name__,
            )

            if isinstance(exc, IndexingError):
                raise

            if isinstance(exc, (OllamaEmbeddingError, VectorStoreError)):
                raise

            raise IndexingError(message) from exc

        except Exception as exc:
            self._mark_failed(state, "Indexing failed.")
            # Log the type only: exception messages and tracebacks can contain
            # conversation text or metadata values.
            logger.error(
                "Unexpected indexing failure for conversation %s: %s",
                conversation_id,
                type(exc).__name__,
            )
            raise IndexingError("Indexing failed.") from exc

        state.status = IndexStatus.INDEXED.value
        state.signature = signature
        state.chunk_count = len(chunks)
        state.embedding_model = self.config.OLLAMA_EMBED_MODEL
        state.embedding_dimension = batch.dimension
        state.indexed_at = datetime.now(timezone.utc)
        state.last_error = None
        self.db.commit()

        return IndexResult(
            conversation_id=conversation.conversation_id,
            status="indexed",
            chunks=len(chunks),
            indexed_at=state.indexed_at,
        )

    def _index_all_locked(
        self,
        conversation_ids: list[str],
        force: bool,
        fail_fast: bool,
    ) -> IndexAllResult:
        results: list[IndexResult] = []

        for conversation_id in conversation_ids:
            try:
                result = self._index_conversation_locked(
                    conversation_id,
                    force=force,
                )
            except Exception as exc:
                message = self._public_error(exc)
                results.append(
                    IndexResult(
                        conversation_id=conversation_id,
                        status="failed",
                        chunks=0,
                        error=message,
                    )
                )

                if fail_fast:
                    break
            else:
                results.append(result)

        indexed = sum(1 for item in results if item.status == "indexed")
        skipped = sum(
            1 for item in results if item.status == "already_indexed"
        )
        failed = sum(1 for item in results if item.status == "failed")

        if failed and (indexed or skipped):
            status = "partial"
        elif failed:
            status = "failed"
        elif not indexed and not skipped:
            status = "nothing_to_do"
        else:
            status = "completed"

        return IndexAllResult(
            status=status,
            total=len(conversation_ids),
            indexed=indexed,
            skipped=skipped,
            failed=failed,
            results=results,
        )

    def _get_conversation_ids(
        self,
        limit: int | None,
    ) -> list[str]:
        conversation_ids = get_all_conversation_ids(self.db)

        if limit is not None:
            return conversation_ids[:limit]

        return conversation_ids

    def _mark_failed(self, state, message: str) -> None:
        state.status = IndexStatus.FAILED.value
        state.last_error = message[:1000]

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _signature(self) -> str:
        return (
            f"{self.config.OLLAMA_EMBED_MODEL}|"
            f"{self.config.CHUNKING_VERSION}|"
            f"{self.config.CHUNK_SIZE_TOKENS}|"
            f"{self.config.CHUNK_OVERLAP_TOKENS}|"
            f"{self.config.CHUNK_MIN_TOKENS}"
        )

    @staticmethod
    def _build_embedding_text(chunk: Chunk) -> str:
        return (
            f"Conversation: {chunk.conversation_title}\n"
            f"Speaker: {chunk.role}\n\n"
            f"{chunk.content}"
        )

    def _build_metadata(self, chunk: Chunk) -> dict[str, Any]:
        return {
            "conversation_id": chunk.conversation_id,
            "conversation_db_id": chunk.conversation_db_id,
            "message_id": chunk.message_id,
            "message_position": chunk.message_position,
            "role": chunk.role,
            "chunk_index": chunk.chunk_index,
            "title": chunk.conversation_title,
            "chunking_version": self.config.CHUNKING_VERSION,
            "embedding_model": self.config.OLLAMA_EMBED_MODEL,
        }

    def _acquire_lock(self) -> None:
        if not self._lock.acquire(blocking=False):
            raise IndexingBusyError(
                "Another indexing operation is already running."
            )

    @staticmethod
    def _public_error(exc: Exception) -> str:
        if isinstance(exc, IndexConfigurationError):
            return str(exc)

        if isinstance(exc, OllamaModelNotFoundError):
            return str(exc)

        if isinstance(exc, OllamaUnavailableError):
            return "Ollama embedding service is unavailable."

        if isinstance(exc, EmbeddingResponseError):
            return "Ollama returned an invalid embedding response."

        if isinstance(exc, VectorStoreUnavailableError):
            return "ChromaDB is unavailable."

        if isinstance(exc, VectorStoreConfigurationError):
            return str(exc)

        if isinstance(exc, VectorStoreError):
            return "ChromaDB operation failed."

        if isinstance(exc, IndexingError):
            return str(exc)

        return "Indexing failed."
