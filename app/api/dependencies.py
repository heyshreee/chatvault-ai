from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.embeddings.ollama_embeddings import OllamaEmbeddingClient
from app.rag.chat_service import ChatService
from app.rag.ollama_chat import OllamaChatClient
from app.rag.retriever import SemanticRetriever
from app.vectorstore.chroma_store import ChromaStore, get_chroma_store


def get_embedding_client() -> Generator[OllamaEmbeddingClient, None, None]:
    client = OllamaEmbeddingClient()

    try:
        yield client
    finally:
        client.close()


def get_chat_client() -> Generator[OllamaChatClient, None, None]:
    client = OllamaChatClient()

    try:
        yield client
    finally:
        client.close()


def get_retriever(
    db: Session = Depends(get_db),
    embeddings: OllamaEmbeddingClient = Depends(get_embedding_client),
    store: ChromaStore = Depends(get_chroma_store),
) -> SemanticRetriever:
    return SemanticRetriever(db, embeddings, store)


def get_chat_service(
    db: Session = Depends(get_db),
    embeddings: OllamaEmbeddingClient = Depends(get_embedding_client),
    store: ChromaStore = Depends(get_chroma_store),
    chat: OllamaChatClient = Depends(get_chat_client),
) -> ChatService:
    return ChatService(db, embeddings, store, chat)
