import os

import pytest

from app.core.config import settings
from app.embeddings.ollama_embeddings import OllamaEmbeddingClient
from app.processing.indexing_service import IndexingService


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_OLLAMA_TESTS") != "1",
    reason="Set RUN_OLLAMA_TESTS=1 to run real Ollama integration tests.",
)


def test_real_ollama_index_and_retrieve(
    db_session,
    sample_conversation,
    chroma_store,
):
    """Index and retrieve with the real Ollama embedding model.

    This test is opt-in so the normal suite never requires a running Ollama
    instance and never downloads a model.
    """

    conversation_id = sample_conversation.conversation_id
    client = OllamaEmbeddingClient()

    try:
        client.assert_model_available()

        service = IndexingService(db_session, client, chroma_store)
        result = service.index_conversation(conversation_id, force=True)

        assert result.status == "indexed"
        assert result.chunks > 0

        status = service.get_status()
        assert status.embedding_model == settings.OLLAMA_EMBED_MODEL
        assert status.embedding_dimension is not None
        assert status.embedding_dimension > 0
        assert status.vectors == result.chunks

        query = "How do I reset Shell-GPT after entering a wrong API key?"
        query_batch = client.embed_texts([query])
        hits = chroma_store.query(query_batch.vectors[0], n_results=3)

        assert hits
        assert hits[0].metadata["conversation_id"] == conversation_id

        retrieved_text = " ".join(
            (hit.document or "").lower() for hit in hits
        )
        assert any(
            keyword in retrieved_text
            for keyword in ("api key", "shell-gpt", "configuration")
        )
    finally:
        client.close()
