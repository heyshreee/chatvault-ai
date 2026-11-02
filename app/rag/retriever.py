from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.database.repository import get_conversation_titles
from app.processing.text_cleaner import clean_chatgpt_text
from app.embeddings.ollama_embeddings import OllamaEmbeddingClient
from app.vectorstore.chroma_store import ChromaStore


@dataclass(frozen=True)
class RetrievedChunk:
    conversation_id: str
    conversation_title: str
    role: str
    message_position: int
    chunk_index: int
    text: str
    distance: float


class SemanticRetriever:
    """Embed a question and retrieve the closest indexed chunks."""

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

    def search(
        self,
        query: str,
        limit: int = 5,
        conversation_id: str | None = None,
    ) -> list[RetrievedChunk]:
        query = query.strip()

        if not query:
            raise ValueError("Query cannot be blank.")

        if limit <= 0:
            return []

        self.store.check_model_compatibility(
            self.config.OLLAMA_EMBED_MODEL
        )

        batch = self.embeddings.embed_texts([query])

        if not batch.vectors:
            return []

        where = (
            {"conversation_id": conversation_id}
            if conversation_id
            else None
        )

        # Over-fetch so deleted conversations whose vectors could not be
        # cleaned up never consume the caller's result budget.
        hits = self.store.query(
            query_embedding=batch.vectors[0],
            n_results=max(limit * 4, limit),
            where=where,
        )

        candidate_ids = []

        for hit in hits:
            candidate_id = (hit.metadata or {}).get("conversation_id")

            if isinstance(candidate_id, str):
                candidate_ids.append(candidate_id)

        titles = get_conversation_titles(
            self.db,
            list(dict.fromkeys(candidate_ids)),
        )

        results: list[RetrievedChunk] = []

        for hit in hits:
            metadata = hit.metadata or {}
            candidate_id = metadata.get("conversation_id")
            text = hit.document

            if not isinstance(candidate_id, str) or not text:
                continue

            if conversation_id and candidate_id != conversation_id:
                continue

            title = titles.get(candidate_id)

            if title is None:
                # The SQLite conversation was deleted but stale vectors
                # remain. Never cite or return orphaned content.
                continue

            position = metadata.get("message_position")
            chunk_index = metadata.get("chunk_index")
            role = metadata.get("role")

            results.append(
                RetrievedChunk(
                    conversation_id=candidate_id,
                    conversation_title=title,
                    role=role if isinstance(role, str) else "unknown",
                    message_position=(
                        position if isinstance(position, int) else 0
                    ),
                    chunk_index=(
                        chunk_index if isinstance(chunk_index, int) else 0
                    ),
                    text=clean_chatgpt_text(text),
                    distance=hit.distance,
                )
            )

            if len(results) >= limit:
                break

        return results
