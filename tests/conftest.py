from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_chat_client
from app.api.routes.indexing import (
    get_chroma_store,
    get_embedding_client,
)
from app.database import models  # noqa: F401 - register ORM models
from app.database.connection import Base, get_db
from app.database.repository import save_conversation
from app.ingestion.extractor import Conversation, Message
from app.main import app
from app.vectorstore.chroma_store import ChromaStore
from tests.fakes import FakeChatClient, FakeEmbeddingClient


@pytest.fixture
def test_engine(tmp_path):
    database_path = tmp_path / "test_chatvault.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    yield engine

    engine.dispose()


@pytest.fixture(autouse=True)
def isolated_database(test_engine) -> Generator[None, None, None]:
    """Keep every test away from the real SQLite database."""

    testing_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = testing_session()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    testing_session = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    db = testing_session()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_conversation(db_session):
    conversation = Conversation(
        conversation_id="phase5-test-conversation",
        title="Phase 5 test conversation",
        source_url="https://chatgpt.com/share/phase5-test-conversation",
        messages=[
            Message(
                role="user",
                content="How do I reset Shell-GPT after entering a wrong API key?",
                position=0,
            ),
            Message(
                role="assistant",
                content=(
                    "You do not need to reinstall Shell-GPT. Reset its "
                    "configuration and enter the correct API key again."
                ),
                position=1,
            ),
            Message(
                role="user",
                content="Where is the configuration stored on Kali Linux?",
                position=2,
            ),
            Message(
                role="assistant",
                content=(
                    "The Shell-GPT configuration is stored in the user's "
                    "configuration directory. Use `sgpt --show-config` to "
                    "inspect the active values."
                ),
                position=3,
            ),
        ],
    )

    saved, _ = save_conversation(db_session, conversation)
    return saved


@pytest.fixture
def chroma_store(tmp_path):
    store = ChromaStore(
        path=tmp_path / "chroma",
        collection_name=f"test_{uuid4().hex}",
    )

    yield store

    store.close()


@pytest.fixture
def fake_embedding_client():
    return FakeEmbeddingClient()


@pytest.fixture
def fake_chat_client():
    return FakeChatClient()


@pytest.fixture
def api_client(
    fake_embedding_client,
    fake_chat_client,
    chroma_store,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_embedding_client] = (
        lambda: fake_embedding_client
    )
    app.dependency_overrides[get_chat_client] = lambda: fake_chat_client
    app.dependency_overrides[get_chroma_store] = lambda: chroma_store

    client = TestClient(app)

    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_embedding_client, None)
        app.dependency_overrides.pop(get_chat_client, None)
        app.dependency_overrides.pop(get_chroma_store, None)
