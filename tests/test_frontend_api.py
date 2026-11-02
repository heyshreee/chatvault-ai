from app.vectorstore.chroma_store import VectorStoreUnavailableError

API = "/api/v1"
INDEX_PREFIX = f"{API}/index"
CONVERSATIONS_PREFIX = f"{API}/conversations"


def test_dashboard_stats_before_and_after_indexing(
    api_client,
    sample_conversation,
):
    before = api_client.get(f"{API}/stats")

    assert before.status_code == 200
    data = before.json()
    assert data["conversations_total"] == 1
    assert data["messages_total"] == 4
    assert data["indexed_conversations"] == 0
    assert data["not_indexed_conversations"] == 1
    assert data["chunks_indexed"] == 0
    assert data["vectors"] == 0
    assert data["vector_store_available"] is True
    assert len(data["recent_imports"]) == 1
    assert data["recent_imports"][0]["conversation_id"] == (
        sample_conversation.conversation_id
    )
    assert data["recent_imports"][0]["message_count"] == 4

    indexed = api_client.post(
        f"{INDEX_PREFIX}/{sample_conversation.conversation_id}"
    ).json()

    after = api_client.get(f"{API}/stats").json()
    assert after["indexed_conversations"] == 1
    assert after["not_indexed_conversations"] == 0
    assert after["chunks_indexed"] == indexed["chunks"]
    assert after["vectors"] == indexed["chunks"]


def test_semantic_search_returns_indexed_chunks(
    api_client,
    sample_conversation,
):
    api_client.post(f"{INDEX_PREFIX}/{sample_conversation.conversation_id}")

    response = api_client.post(
        f"{API}/search",
        json={"query": "reset Shell-GPT API key", "limit": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "reset Shell-GPT API key"
    assert 0 < data["total"] <= 3
    assert len(data["results"]) == data["total"]

    result = data["results"][0]
    assert result["conversation_id"] == sample_conversation.conversation_id
    assert result["conversation_title"] == "Phase 5 test conversation"
    assert result["role"] in {"user", "assistant"}
    assert result["text"]
    assert isinstance(result["distance"], float)
    assert isinstance(result["message_position"], int)
    assert isinstance(result["chunk_index"], int)


def test_semantic_search_conversation_filter_and_empty_index(
    api_client,
    sample_conversation,
):
    empty = api_client.post(
        f"{API}/search",
        json={"query": "Shell-GPT"},
    )
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    api_client.post(f"{INDEX_PREFIX}/{sample_conversation.conversation_id}")

    other = api_client.post(
        f"{API}/search",
        json={
            "query": "Shell-GPT",
            "conversation_id": "missing-conversation",
        },
    )

    assert other.status_code == 200
    assert other.json()["results"] == []


def test_semantic_search_validation_and_ollama_failure(
    api_client,
    fake_embedding_client,
):
    blank = api_client.post(f"{API}/search", json={"query": "   "})
    assert blank.status_code == 422

    fake_embedding_client.fail = True
    failed = api_client.post(
        f"{API}/search",
        json={"query": "Shell-GPT"},
    )
    assert failed.status_code == 503
    assert "unavailable" in failed.json()["detail"].lower()


def test_chat_returns_answer_with_sources(
    api_client,
    sample_conversation,
    fake_chat_client,
):
    api_client.post(f"{INDEX_PREFIX}/{sample_conversation.conversation_id}")

    response = api_client.post(
        f"{API}/chat",
        json={
            "message": "How do I reset Shell-GPT?",
            "history": [
                {"role": "user", "content": "I am using Kali Linux."},
                {"role": "assistant", "content": "Understood."},
            ],
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["answer"] == fake_chat_client.answer
    assert data["model"] == "llama3.2:3b"
    assert 0 < len(data["sources"]) <= 3
    assert [source["index"] for source in data["sources"]] == list(
        range(1, len(data["sources"]) + 1)
    )
    assert data["sources"][0]["conversation_title"] == (
        "Phase 5 test conversation"
    )

    assert len(fake_chat_client.calls) == 1
    sent = fake_chat_client.calls[0]
    assert [message["role"] for message in sent] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert "Context passages:" in sent[-1]["content"]
    assert "How do I reset Shell-GPT?" in sent[-1]["content"]


def test_chat_without_sources_does_not_call_model(
    api_client,
    fake_chat_client,
):
    response = api_client.post(
        f"{API}/chat",
        json={"message": "What did I save about Nmap?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_sources"
    assert data["model"] is None
    assert data["sources"] == []
    assert "No indexed conversations" in data["answer"]
    assert fake_chat_client.calls == []


def test_chat_handles_missing_chat_model(
    api_client,
    sample_conversation,
    fake_chat_client,
):
    api_client.post(f"{INDEX_PREFIX}/{sample_conversation.conversation_id}")
    fake_chat_client.model_available = False

    response = api_client.post(
        f"{API}/chat",
        json={"message": "How do I reset Shell-GPT?"},
    )

    assert response.status_code == 503
    assert "not available" in response.json()["detail"].lower()


def test_chat_validation(api_client):
    blank = api_client.post(f"{API}/chat", json={"message": "  "})
    top_k = api_client.post(
        f"{API}/chat",
        json={"message": "hello", "top_k": 99},
    )

    assert blank.status_code == 422
    assert top_k.status_code == 422


def test_model_status_reports_real_components(
    api_client,
    sample_conversation,
):
    indexed = api_client.post(
        f"{INDEX_PREFIX}/{sample_conversation.conversation_id}"
    ).json()

    response = api_client.get(f"{API}/models/status")

    assert response.status_code == 200
    data = response.json()
    assert data["ollama"]["base_url"] == "http://localhost:11434"
    assert data["ollama"]["available"] is True
    assert data["chat_model"] == {
        "name": "llama3.2:3b",
        "available": True,
    }
    assert data["embedding_model"] == {
        "name": "nomic-embed-text",
        "available": True,
    }
    assert len(data["installed_models"]) == 2
    assert data["vector_store"]["available"] is True
    assert data["vector_store"]["vectors"] == indexed["chunks"]
    assert data["vector_store"]["embedding_dimension"] > 0
    assert data["database"] == {
        "engine": "sqlite",
        "conversations": 1,
        "messages": 4,
    }
    assert data["index"]["indexed"] == 1
    assert data["index"]["chunks_recorded"] == indexed["chunks"]
    assert data["index"]["rebuild_required"] is False


def test_model_status_degrades_when_ollama_is_down(
    api_client,
    fake_chat_client,
):
    fake_chat_client.unavailable = True

    response = api_client.get(f"{API}/models/status")

    assert response.status_code == 200
    data = response.json()
    assert data["ollama"]["available"] is False
    assert data["ollama"]["error"]
    assert data["chat_model"]["available"] is False
    assert data["embedding_model"]["available"] is False
    assert data["installed_models"] == []
    assert data["vector_store"]["available"] is True


def test_delete_conversation_removes_messages_and_vectors(
    api_client,
    sample_conversation,
    chroma_store,
):
    conversation_id = sample_conversation.conversation_id
    indexed = api_client.post(f"{INDEX_PREFIX}/{conversation_id}").json()

    response = api_client.delete(
        f"{CONVERSATIONS_PREFIX}/{conversation_id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "conversation_id": conversation_id,
        "status": "deleted",
        "deleted_messages": 4,
        "deleted_vectors": indexed["chunks"],
    }

    assert api_client.get(
        f"{CONVERSATIONS_PREFIX}/{conversation_id}"
    ).status_code == 404
    assert api_client.get(f"{CONVERSATIONS_PREFIX}").json()["total"] == 0
    assert chroma_store.count() == 0

    status = api_client.get(f"{INDEX_PREFIX}/status").json()
    assert status["conversations"]["total"] == 0
    assert status["vectors"] == 0


def test_delete_conversation_survives_vector_store_outage(
    api_client,
    sample_conversation,
    chroma_store,
    monkeypatch,
):
    def fail_delete(_conversation_id):
        raise VectorStoreUnavailableError("ChromaDB is unavailable.")

    monkeypatch.setattr(chroma_store, "delete_conversation", fail_delete)

    response = api_client.delete(
        f"{CONVERSATIONS_PREFIX}/{sample_conversation.conversation_id}"
    )

    assert response.status_code == 200
    assert response.json()["deleted_vectors"] is None
    assert api_client.get(
        f"{CONVERSATIONS_PREFIX}/{sample_conversation.conversation_id}"
    ).status_code == 404


def test_delete_missing_conversation_returns_404(api_client):
    response = api_client.delete(f"{CONVERSATIONS_PREFIX}/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found."


def test_cors_allows_local_frontend_origin(api_client):
    response = api_client.options(
        f"{API}/stats",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )

    denied = api_client.options(
        f"{API}/stats",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in denied.headers
