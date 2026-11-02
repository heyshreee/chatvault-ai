import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from app.core.config import settings


class VectorStoreError(Exception):
    """Base exception for vector-store failures."""


class VectorStoreUnavailableError(VectorStoreError):
    """Raised when ChromaDB cannot be initialized."""


class VectorStoreConfigurationError(VectorStoreError):
    """Raised when the collection is incompatible with current settings."""


@dataclass(frozen=True)
class QueryHit:
    id: str
    document: str | None
    metadata: dict[str, Any]
    distance: float


@dataclass(frozen=True)
class StoreInfo:
    collection_name: str
    count: int
    metadata: dict[str, Any]


class ChromaStore:
    """Persistent ChromaDB collection used as the derived search index."""

    def __init__(
        self,
        path: str | Path | None = None,
        collection_name: str | None = None,
        client=None,
    ):
        self.path = str(
            Path(path or settings.CHROMA_DB_PATH).expanduser().resolve()
        )
        self.collection_name = (
            collection_name or settings.CHROMA_COLLECTION_NAME
        )
        self._client = client
        self._collection = None
        self._lock = threading.RLock()

    # --------------------------------------------------
    # Collection lifecycle
    # --------------------------------------------------

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except ImportError as exc:
            raise VectorStoreUnavailableError(
                "ChromaDB is not installed. Install project dependencies."
            ) from exc

        try:
            Path(self.path).mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.path,
                settings=ChromaSettings(
                    anonymized_telemetry=settings.CHROMA_TELEMETRY,
                ),
            )
        except Exception as exc:
            raise VectorStoreUnavailableError(
                "Unable to initialize the ChromaDB storage."
            ) from exc

        return self._client

    def _get_collection(self):
        with self._lock:
            if self._collection is not None:
                return self._collection

            client = self._get_client()

            try:
                collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={
                        "hnsw:space": "cosine",
                        "distance_metric": "cosine",
                    },
                    # Phase 5 always supplies embeddings explicitly. Setting
                    # None prevents ChromaDB from instantiating its default
                    # ONNX embedding function.
                    embedding_function=None,
                )
            except Exception as exc:
                raise VectorStoreError(
                    "Unable to initialize the ChromaDB collection."
                ) from exc

            metadata = collection.metadata or {}
            space = (
                metadata.get("distance_metric")
                or metadata.get("hnsw:space")
                or metadata.get("space")
            )

            if space and str(space).lower() != "cosine":
                raise VectorStoreConfigurationError(
                    "The existing ChromaDB collection does not use cosine "
                    "distance. Rebuild the index."
                )

            self._collection = collection
            return collection

    def reset(self) -> None:
        """Delete and recreate the collection."""

        with self._lock:
            client = self._get_client()

            try:
                client.delete_collection(self.collection_name)
            except Exception as exc:
                try:
                    from chromadb.errors import NotFoundError
                except ImportError:
                    raise VectorStoreError(
                        "Unable to reset the ChromaDB collection."
                    ) from exc

                # A missing collection is already in the desired state.
                if not isinstance(exc, NotFoundError):
                    raise VectorStoreError(
                        "Unable to reset the ChromaDB collection."
                    ) from exc

            self._collection = None
            self._get_collection()

    def close(self) -> None:
        self._collection = None
        self._client = None

    # --------------------------------------------------
    # Provenance and metadata
    # --------------------------------------------------

    def info(self) -> StoreInfo:
        collection = self._get_collection()
        metadata = dict(collection.metadata or {})

        try:
            count = collection.count()
        except Exception as exc:
            raise VectorStoreError(
                "Unable to read the ChromaDB collection."
            ) from exc

        return StoreInfo(
            collection_name=self.collection_name,
            count=count,
            metadata=metadata,
        )

    def collection_metadata(self) -> dict[str, Any]:
        return dict(self._get_collection().metadata or {})

    def check_model_compatibility(self, embedding_model: str) -> None:
        """Reject partial indexing when the collection uses another model."""

        collection = self._get_collection()

        try:
            count = collection.count()
        except Exception as exc:
            raise VectorStoreError(
                "Unable to read the ChromaDB collection."
            ) from exc

        if count == 0:
            return

        metadata = collection.metadata or {}
        stored_model = metadata.get("embedding_model")

        if not stored_model:
            raise VectorStoreConfigurationError(
                "The ChromaDB collection has unknown embedding provenance. "
                "Rebuild the index."
            )

        if stored_model != embedding_model:
            raise VectorStoreConfigurationError(
                "The embedding model has changed. Rebuild the index."
            )

    def ensure_provenance(
        self,
        embedding_model: str,
        embedding_dimension: int,
    ) -> None:
        """Record or verify the embedding model and dimension."""

        collection = self._get_collection()

        try:
            count = collection.count()
        except Exception as exc:
            raise VectorStoreError(
                "Unable to read the ChromaDB collection."
            ) from exc

        metadata = dict(collection.metadata or {})
        stored_model = metadata.get("embedding_model")
        stored_dimension = metadata.get("embedding_dimension")

        if count > 0:
            if not stored_model:
                raise VectorStoreConfigurationError(
                    "The ChromaDB collection has unknown embedding "
                    "provenance. Rebuild the index."
                )

            if stored_model != embedding_model:
                raise VectorStoreConfigurationError(
                    "The embedding model has changed. Rebuild the index."
                )

            if stored_dimension is None:
                raise VectorStoreConfigurationError(
                    "The ChromaDB collection has unknown embedding "
                    "dimensions. Rebuild the index."
                )

            if int(stored_dimension) != embedding_dimension:
                raise VectorStoreConfigurationError(
                    "The embedding dimension has changed. Rebuild the index."
                )

            return

        # An empty collection is safe to label with the current model.
        # ChromaDB does not allow the distance function to be changed through
        # modify(), so the immutable hnsw settings must be omitted here.
        metadata.pop("hnsw:space", None)
        metadata.pop("space", None)
        metadata["distance_metric"] = "cosine"
        metadata["embedding_model"] = embedding_model
        metadata["embedding_dimension"] = int(embedding_dimension)

        try:
            collection.modify(metadata=metadata)
        except Exception as exc:
            raise VectorStoreError(
                "Unable to record ChromaDB collection metadata."
            ) from exc

    # --------------------------------------------------
    # Writes
    # --------------------------------------------------

    def upsert(
        self,
        ids: Sequence[str],
        documents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        if not ids:
            return 0

        if not (
            len(ids)
            == len(documents)
            == len(embeddings)
            == len(metadatas)
        ):
            raise ValueError("Vector record fields have inconsistent lengths.")

        collection = self._get_collection()

        self._check_embedding_dimension(collection, embeddings[0])

        written = 0

        try:
            for start in range(0, len(ids), batch_size):
                end = start + batch_size
                collection.upsert(
                    ids=list(ids[start:end]),
                    documents=list(documents[start:end]),
                    embeddings=[
                        list(vector) for vector in embeddings[start:end]
                    ],
                    metadatas=list(metadatas[start:end]),
                )
                written += len(ids[start:end])
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                "Unable to write vectors to ChromaDB."
            ) from exc

        return written

    def _check_embedding_dimension(self, collection, vector) -> None:
        if not vector:
            raise ValueError("Embedding vectors cannot be empty.")

        metadata = collection.metadata or {}
        stored_dimension = metadata.get("embedding_dimension")

        if (
            stored_dimension is not None
            and int(stored_dimension) != len(vector)
        ):
            raise VectorStoreConfigurationError(
                "The embedding dimension does not match the collection. "
                "Rebuild the index."
            )

    def delete_conversation(self, conversation_id: str) -> int:
        collection = self._get_collection()

        try:
            result = collection.get(
                where={"conversation_id": conversation_id},
                include=[],
            )
            ids = result.get("ids") or []
            collection.delete(
                where={"conversation_id": conversation_id}
            )
        except Exception as exc:
            raise VectorStoreError(
                "Unable to delete vectors from ChromaDB."
            ) from exc

        return len(ids)

    def count_conversation(self, conversation_id: str) -> int:
        """Return how many vectors currently belong to a conversation."""

        collection = self._get_collection()

        try:
            result = collection.get(
                where={"conversation_id": conversation_id},
                include=[],
            )
        except Exception as exc:
            raise VectorStoreError(
                "Unable to read vectors from ChromaDB."
            ) from exc

        return len(result.get("ids") or [])

    # --------------------------------------------------
    # Reads
    # --------------------------------------------------

    def count(self) -> int:
        return self.info().count

    def query(
        self,
        query_embedding: Sequence[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[QueryHit]:
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty.")

        if n_results <= 0:
            return []

        collection = self._get_collection()

        try:
            count = collection.count()
        except Exception as exc:
            raise VectorStoreError(
                "Unable to read the ChromaDB collection."
            ) from exc

        if count == 0:
            return []

        limit = min(n_results, count)

        try:
            result = collection.query(
                query_embeddings=[list(query_embedding)],
                n_results=limit,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(
                "Unable to query ChromaDB."
            ) from exc

        ids = (result.get("ids") or [[]])[0] or []
        documents = (result.get("documents") or [[]])[0] or []
        metadatas = (result.get("metadatas") or [[]])[0] or []
        distances = (result.get("distances") or [[]])[0] or []

        hits = []

        for index, record_id in enumerate(ids):
            distance = (
                distances[index]
                if index < len(distances)
                else 0.0
            )

            try:
                distance_value = float(distance)
            except (TypeError, ValueError):
                distance_value = 0.0

            if not math.isfinite(distance_value):
                distance_value = 0.0

            hits.append(
                QueryHit(
                    id=record_id,
                    document=(
                        documents[index]
                        if index < len(documents)
                        else None
                    ),
                    metadata=(
                        metadatas[index]
                        if index < len(metadatas)
                        else {}
                    ),
                    distance=distance_value,
                )
            )

        return hits


_shared_store: ChromaStore | None = None
_shared_store_lock = threading.Lock()


def get_chroma_store() -> ChromaStore:
    """Return the process-wide ChromaDB adapter."""

    global _shared_store

    with _shared_store_lock:
        if _shared_store is None:
            _shared_store = ChromaStore()

        return _shared_store


def reset_chroma_store() -> None:
    """Clear the process-wide adapter; used by tests and maintenance."""

    global _shared_store
    _shared_store = None
