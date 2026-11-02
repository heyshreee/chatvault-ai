import pytest

from app.core.config import Settings
from app.database.repository import (
    get_conversation,
    get_index_state,
    get_or_create_index_state,
    mark_interrupted_index_states,
    save_conversation,
)
from app.ingestion.extractor import Conversation, Message
from app.processing.index_status import IndexStatus
from app.processing.indexing_service import (
    ConversationNotFoundError,
    IndexConfigurationError,
    IndexingService,
    NoIndexableContentError,
)
from app.vectorstore.chroma_store import (
    StoreInfo,
    VectorStoreUnavailableError,
)
from tests.fakes import FakeEmbeddingClient


def make_settings(**overrides):
    options = {
        "OLLAMA_EMBED_MODEL": "nomic-embed-text",
        "CHUNK_SIZE_TOKENS": 100,
        "CHUNK_OVERLAP_TOKENS": 20,
        "CHUNK_MIN_TOKENS": 10,
        "CHUNKING_VERSION": "test-v1",
    }
    options.update(overrides)
    return Settings(**options)


def make_service(
    db_session,
    chroma_store,
    fake_embedding_client,
    **settings_overrides,
):
    return IndexingService(
        db_session,
        fake_embedding_client,
        chroma_store,
        config=make_settings(**settings_overrides),
    )


def test_index_conversation_and_status(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )

    result = service.index_conversation(
        sample_conversation.conversation_id
    )

    assert result.status == "indexed"
    assert result.chunks > 0

    state = get_index_state(db_session, sample_conversation.id)
    assert state.status == IndexStatus.INDEXED.value
    assert state.signature is not None
    assert state.chunk_count == result.chunks

    status = service.get_status()
    assert status.total == 1
    assert status.indexed == 1
    assert status.not_indexed == 0
    assert status.vectors == result.chunks
    assert status.chunks_recorded == result.chunks
    assert status.vector_store_available is True


def test_indexing_is_idempotent(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    conversation_id = sample_conversation.conversation_id

    first = service.index_conversation(conversation_id)
    second = service.index_conversation(conversation_id)

    assert first.status == "indexed"
    assert second.status == "already_indexed"
    assert second.chunks == first.chunks
    assert chroma_store.count() == first.chunks


def test_indexing_recreates_vectors_missing_from_chroma(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    conversation_id = sample_conversation.conversation_id

    first = service.index_conversation(conversation_id)
    chroma_store.reset()

    status = service.get_status()
    assert status.vectors == 0
    assert status.rebuild_required is True

    second = service.index_conversation(conversation_id)

    assert second.status == "indexed"
    assert second.chunks == first.chunks
    assert chroma_store.count() == first.chunks


def test_force_reindex_replaces_vectors(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    conversation_id = sample_conversation.conversation_id

    first = service.index_conversation(conversation_id)
    second = service.index_conversation(conversation_id, force=True)

    assert second.status == "indexed"
    assert second.chunks == first.chunks
    assert chroma_store.count() == first.chunks


def test_embedding_failure_preserves_previous_vectors(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    conversation_id = sample_conversation.conversation_id

    first = service.index_conversation(conversation_id)
    service.embeddings = FakeEmbeddingClient(fail=True)

    with pytest.raises(Exception):
        service.index_conversation(conversation_id, force=True)

    assert chroma_store.count() == first.chunks

    state = get_index_state(db_session, sample_conversation.id)
    assert state.status == IndexStatus.FAILED.value


def test_model_change_requires_rebuild(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    first_service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
        OLLAMA_EMBED_MODEL="model-a",
    )
    first_service.index_conversation(
        sample_conversation.conversation_id
    )

    second_service = make_service(
        db_session,
        chroma_store,
        FakeEmbeddingClient(),
        OLLAMA_EMBED_MODEL="model-b",
    )

    with pytest.raises(IndexConfigurationError):
        second_service.index_conversation(
            sample_conversation.conversation_id,
            force=True,
        )

    with pytest.raises(IndexConfigurationError):
        second_service.index_all()


def test_chunking_change_marks_index_stale(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    first_service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    first_service.index_conversation(
        sample_conversation.conversation_id
    )

    second_service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
        CHUNK_SIZE_TOKENS=120,
    )
    status = second_service.get_status()

    assert status.indexed == 0
    assert status.stale == 1


def test_index_all_skips_current_conversations(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )

    first = service.index_all()
    second = service.index_all()

    assert first.status == "completed"
    assert first.indexed == 1
    assert second.status == "completed"
    assert second.skipped == 1
    assert second.failed == 0


def test_rebuild_recreates_the_index(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    first = service.index_conversation(
        sample_conversation.conversation_id
    )

    result = service.rebuild()

    assert result.status == "completed"
    assert result.indexed == 1
    assert chroma_store.count() == first.chunks


def test_delete_index_resets_state(
    db_session,
    sample_conversation,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )
    service.index_conversation(sample_conversation.conversation_id)

    deleted = service.delete_index(
        sample_conversation.conversation_id
    )

    assert deleted > 0
    assert chroma_store.count() == 0

    state = get_index_state(db_session, sample_conversation.id)
    assert state.status == IndexStatus.NOT_INDEXED.value
    assert state.chunk_count == 0
    assert state.indexed_at is None


def test_index_unknown_conversation(
    db_session,
    chroma_store,
    fake_embedding_client,
):
    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )

    with pytest.raises(ConversationNotFoundError):
        service.index_conversation("does-not-exist")


def test_empty_conversation_is_rejected(
    db_session,
    chroma_store,
    fake_embedding_client,
):
    saved, _ = save_conversation(
        db_session,
        Conversation(
            conversation_id="empty-content",
            title="Empty content",
            source_url="https://chatgpt.com/share/empty-content",
            messages=[
                Message(role="user", content="   ", position=0),
            ],
        ),
    )

    service = make_service(
        db_session,
        chroma_store,
        fake_embedding_client,
    )

    with pytest.raises(NoIndexableContentError):
        service.index_conversation(saved.conversation_id)

    state = get_index_state(db_session, saved.id)
    assert state.status == IndexStatus.FAILED.value


def test_index_all_continues_after_failure(
    db_session,
    sample_conversation,
    chroma_store,
):
    service = make_service(
        db_session,
        chroma_store,
        FakeEmbeddingClient(fail=True),
    )

    result = service.index_all()

    assert result.status == "failed"
    assert result.failed == 1
    assert result.indexed == 0


def test_status_when_vector_store_is_unavailable(
    db_session,
    fake_embedding_client,
):
    class UnavailableStore:
        collection_name = "unavailable"

        def info(self):
            raise VectorStoreUnavailableError("not available")

    service = IndexingService(
        db_session,
        fake_embedding_client,
        UnavailableStore(),
        config=make_settings(),
    )

    status = service.get_status()

    assert status.vector_store_available is False
    assert status.vectors is None
    assert status.vector_store_error == "ChromaDB is unavailable."


def test_startup_reconciliation_marks_interrupted_as_failed(
    db_session,
    sample_conversation,
):
    state = get_or_create_index_state(db_session, sample_conversation.id)
    state.status = IndexStatus.INDEXING.value
    db_session.commit()

    updated = mark_interrupted_index_states(db_session)

    assert updated == 1

    db_session.expire_all()
    state = get_index_state(db_session, sample_conversation.id)
    assert state.status == IndexStatus.FAILED.value
    assert state.last_error == "Indexing was interrupted before completion."


def test_startup_reconciliation_leaves_other_states_alone(
    db_session,
    sample_conversation,
):
    state = get_or_create_index_state(db_session, sample_conversation.id)
    state.status = IndexStatus.NOT_INDEXED.value
    db_session.commit()

    assert mark_interrupted_index_states(db_session) == 0

    db_session.expire_all()
    state = get_index_state(db_session, sample_conversation.id)
    assert state.status == IndexStatus.NOT_INDEXED.value
