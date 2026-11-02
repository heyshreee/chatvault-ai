from app.database.repository import save_conversation
from app.ingestion.extractor import Conversation, Message


INDEX_PREFIX = "/api/v1/index"


def test_index_one_conversation_and_repeat(api_client, sample_conversation):
    conversation_id = sample_conversation.conversation_id

    response = api_client.post(f"{INDEX_PREFIX}/{conversation_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert data["status"] == "indexed"
    assert data["chunks"] > 0
    assert data["embedding_model"] == "nomic-embed-text"
    assert data["indexed_at"] is not None

    repeat = api_client.post(f"{INDEX_PREFIX}/{conversation_id}")

    assert repeat.status_code == 200
    assert repeat.json()["status"] == "already_indexed"
    assert repeat.json()["chunks"] == data["chunks"]


def test_force_reindexes_existing_conversation(
    api_client,
    sample_conversation,
):
    conversation_id = sample_conversation.conversation_id

    first = api_client.post(f"{INDEX_PREFIX}/{conversation_id}")
    forced = api_client.post(
        f"{INDEX_PREFIX}/{conversation_id}",
        params={"force": "true"},
    )

    assert first.status_code == 200
    assert forced.status_code == 200
    assert forced.json()["status"] == "indexed"


def test_index_status_reports_counts(
    api_client,
    sample_conversation,
):
    indexed = api_client.post(
        f"{INDEX_PREFIX}/{sample_conversation.conversation_id}"
    ).json()

    response = api_client.get(f"{INDEX_PREFIX}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["embedding_model"] == "nomic-embed-text"
    assert data["embedding_dimension"] > 0
    assert data["token_counting"] == "approximate_char4"
    assert data["conversations"]["total"] == 1
    assert data["conversations"]["indexed"] == 1
    assert data["conversations"]["not_indexed"] == 0
    assert data["conversations"]["failed"] == 0
    assert data["chunks_recorded"] == indexed["chunks"]
    assert data["vectors"] == indexed["chunks"]
    assert data["vector_store_available"] is True
    assert data["rebuild_required"] is False


def test_index_all_skips_existing(api_client, sample_conversation):
    first = api_client.post(f"{INDEX_PREFIX}/all")
    second = api_client.post(f"{INDEX_PREFIX}/all")

    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    assert first.json()["indexed"] == 1
    assert first.json()["failed"] == 0

    assert second.status_code == 200
    assert second.json()["status"] == "completed"
    assert second.json()["indexed"] == 0
    assert second.json()["skipped"] == 1


def test_status_flags_missing_vectors(
    api_client,
    sample_conversation,
    chroma_store,
):
    api_client.post(
        f"{INDEX_PREFIX}/{sample_conversation.conversation_id}"
    )
    chroma_store.reset()

    status = api_client.get(f"{INDEX_PREFIX}/status").json()

    assert status["vectors"] == 0
    assert status["conversations"]["indexed"] == 1
    assert status["rebuild_required"] is True
    assert status["rebuild_reason"]


def test_rebuild_recreates_collection(api_client, sample_conversation):
    conversation_id = sample_conversation.conversation_id
    indexed = api_client.post(f"{INDEX_PREFIX}/{conversation_id}").json()

    response = api_client.post(f"{INDEX_PREFIX}/rebuild")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["indexed"] == 1
    assert data["collection"]
    assert data["results"][0]["chunks"] == indexed["chunks"]

    status = api_client.get(f"{INDEX_PREFIX}/status").json()
    assert status["vectors"] == indexed["chunks"]


def test_delete_index(api_client, sample_conversation):
    conversation_id = sample_conversation.conversation_id
    indexed = api_client.post(f"{INDEX_PREFIX}/{conversation_id}").json()

    response = api_client.delete(f"{INDEX_PREFIX}/{conversation_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation_id
    assert data["status"] == "not_indexed"
    assert data["deleted_chunks"] == indexed["chunks"]

    status = api_client.get(f"{INDEX_PREFIX}/status").json()
    assert status["conversations"]["indexed"] == 0
    assert status["conversations"]["not_indexed"] == 1
    assert status["vectors"] == 0
    assert status["chunks_recorded"] == 0


def test_delete_missing_index_is_idempotent(
    api_client,
    sample_conversation,
):
    conversation_id = sample_conversation.conversation_id

    response = api_client.delete(f"{INDEX_PREFIX}/{conversation_id}")

    assert response.status_code == 200
    assert response.json()["deleted_chunks"] == 0


def test_unknown_conversation_returns_404(api_client):
    indexed = api_client.post(f"{INDEX_PREFIX}/does-not-exist")
    deleted = api_client.delete(f"{INDEX_PREFIX}/does-not-exist")

    assert indexed.status_code == 404
    assert indexed.json()["detail"] == "Conversation not found."
    assert deleted.status_code == 404


def test_ollama_failure_returns_503(
    api_client,
    fake_embedding_client,
    sample_conversation,
):
    fake_embedding_client.fail = True

    response = api_client.post(
        f"{INDEX_PREFIX}/{sample_conversation.conversation_id}"
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()

    status = api_client.get(f"{INDEX_PREFIX}/status").json()
    assert status["conversations"]["failed"] == 1
    assert status["conversations"]["indexed"] == 0
    assert status["vectors"] == 0


def test_missing_embedding_model_returns_503(
    api_client,
    fake_embedding_client,
    sample_conversation,
):
    fake_embedding_client.model_available = False

    response = api_client.post(f"{INDEX_PREFIX}/all")

    assert response.status_code == 503
    assert "not available" in response.json()["detail"].lower()


def test_embedding_model_change_returns_409(
    api_client,
    chroma_store,
    sample_conversation,
):
    chroma_store.ensure_provenance("another-embedding-model", 8)
    chroma_store.upsert(
        ids=["other:0:0"],
        documents=["other conversation"],
        embeddings=[[0.0] * 8],
        metadatas=[{"conversation_id": "other"}],
    )

    response = api_client.post(
        f"{INDEX_PREFIX}/{sample_conversation.conversation_id}"
    )
    all_response = api_client.post(f"{INDEX_PREFIX}/all")

    assert response.status_code == 409
    assert "embedding model has changed" in response.json()["detail"].lower()
    assert all_response.status_code == 409


def test_empty_conversation_returns_422(api_client, db_session):
    saved, _ = save_conversation(
        db_session,
        Conversation(
            conversation_id="api-empty",
            title="API empty",
            source_url="https://chatgpt.com/share/api-empty",
            messages=[Message(role="user", content="   ", position=0)],
        ),
    )

    response = api_client.post(f"{INDEX_PREFIX}/{saved.conversation_id}")

    assert response.status_code == 422


def test_invalid_limit_returns_422(api_client):
    response = api_client.post(
        f"{INDEX_PREFIX}/all",
        params={"limit": 0},
    )

    assert response.status_code == 422
