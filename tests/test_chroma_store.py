import pytest

from app.vectorstore.chroma_store import (
    ChromaStore,
    VectorStoreConfigurationError,
)


def seed(store, dimension=3):
    store.ensure_provenance("fake-embed", dimension)
    store.upsert(
        ids=["c1:0:0", "c1:1:0", "c2:0:0"],
        documents=["alpha", "beta", "gamma"],
        embeddings=[
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0],
        ],
        metadatas=[
            {
                "conversation_id": "c1",
                "message_position": 0,
                "role": "user",
            },
            {
                "conversation_id": "c1",
                "message_position": 1,
                "role": "assistant",
            },
            {
                "conversation_id": "c2",
                "message_position": 0,
                "role": "user",
            },
        ],
    )


def test_upsert_and_query(chroma_store):
    seed(chroma_store)

    hits = chroma_store.query([1.0, 0.0, 0.0], n_results=2)

    assert len(hits) == 2
    assert hits[0].id == "c1:0:0"
    assert hits[0].document == "alpha"
    assert hits[0].metadata["conversation_id"] == "c1"
    assert hits[0].distance == pytest.approx(0.0)


def test_query_can_filter_by_conversation(chroma_store):
    seed(chroma_store)

    hits = chroma_store.query(
        [1.0, 0.0, 0.0],
        n_results=3,
        where={"conversation_id": "c2"},
    )

    assert [hit.id for hit in hits] == ["c2:0:0"]


def test_upsert_is_idempotent(chroma_store):
    seed(chroma_store)
    assert chroma_store.count() == 3

    seed(chroma_store)

    assert chroma_store.count() == 3


def test_delete_conversation_removes_only_its_vectors(chroma_store):
    seed(chroma_store)

    deleted = chroma_store.delete_conversation("c1")

    assert deleted == 2
    assert chroma_store.count() == 1
    assert chroma_store.query(
        [1.0, 0.0, 0.0],
        n_results=3,
    )[0].id == "c2:0:0"


def test_count_conversation(chroma_store):
    seed(chroma_store)

    assert chroma_store.count_conversation("c1") == 2
    assert chroma_store.count_conversation("c2") == 1
    assert chroma_store.count_conversation("missing") == 0


def test_empty_query_returns_no_results(chroma_store):
    assert chroma_store.query([1.0, 0.0, 0.0]) == []


def test_collection_has_no_default_embedding_function(chroma_store):
    # Phase 5 must never trigger ChromaDB's default ONNX embedding model.
    collection = chroma_store._get_collection()

    assert collection._embedding_function is None


def test_reset_clears_collection(chroma_store):
    seed(chroma_store)
    assert chroma_store.count() == 3

    chroma_store.reset()

    assert chroma_store.count() == 0


def test_provenance_is_checked(chroma_store):
    seed(chroma_store, dimension=3)

    chroma_store.check_model_compatibility("fake-embed")
    chroma_store.ensure_provenance("fake-embed", 3)

    with pytest.raises(VectorStoreConfigurationError):
        chroma_store.check_model_compatibility("another-model")

    with pytest.raises(VectorStoreConfigurationError):
        chroma_store.ensure_provenance("fake-embed", 4)


def test_dimension_mismatch_is_rejected(chroma_store):
    seed(chroma_store, dimension=3)

    with pytest.raises(VectorStoreConfigurationError):
        chroma_store.upsert(
            ids=["bad"],
            documents=["bad"],
            embeddings=[[0.1, 0.2]],
            metadatas=[{"conversation_id": "c3"}],
        )


def test_persistence_survives_reopen(tmp_path):
    path = tmp_path / "persistent-chroma"
    collection_name = "persistent_test"

    first = ChromaStore(path=path, collection_name=collection_name)
    seed(first)
    first.close()

    second = ChromaStore(path=path, collection_name=collection_name)

    try:
        assert second.count() == 3
        hits = second.query([1.0, 0.0, 0.0], n_results=1)
        assert hits[0].id == "c1:0:0"
    finally:
        second.close()
