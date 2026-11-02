from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    APP_NAME: str = "ChatVault AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2:3b"
    OLLAMA_CHAT_TIMEOUT: float = Field(default=180.0, gt=0)
    OLLAMA_CHAT_TEMPERATURE: float = Field(default=0.2, ge=0, le=2)
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_EMBED_TIMEOUT: float = Field(default=120.0, gt=0)
    OLLAMA_EMBED_BATCH_SIZE: int = Field(default=16, ge=1, le=128)

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    CHAT_TOP_K: int = Field(default=5, ge=1, le=10)
    CHAT_MAX_HISTORY_MESSAGES: int = Field(default=10, ge=0, le=50)
    CHAT_MAX_CONTEXT_CHARS: int = Field(default=12000, ge=1000, le=100000)

    CHROMA_DB_PATH: str = "storage/chroma"
    CHROMA_COLLECTION_NAME: str = "chatvault_conversations"
    CHROMA_TELEMETRY: bool = False

    DATABASE_URL: str = "sqlite:///./storage/chatvault.db"
    SQL_ECHO: bool = False

    CHUNK_SIZE_TOKENS: int = Field(default=500, ge=50, le=2000)
    CHUNK_OVERLAP_TOKENS: int = Field(default=75, ge=0)
    CHUNK_MIN_TOKENS: int = Field(default=30, ge=0)
    CHUNKING_VERSION: str = "message-aware-v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_chunking_settings(self):
        if self.CHUNK_OVERLAP_TOKENS >= self.CHUNK_SIZE_TOKENS:
            raise ValueError(
                "CHUNK_OVERLAP_TOKENS must be smaller than "
                "CHUNK_SIZE_TOKENS."
            )

        if self.CHUNK_MIN_TOKENS > self.CHUNK_SIZE_TOKENS:
            raise ValueError(
                "CHUNK_MIN_TOKENS cannot exceed CHUNK_SIZE_TOKENS."
            )

        if not self.CHUNKING_VERSION.strip():
            raise ValueError("CHUNKING_VERSION cannot be empty.")

        return self


settings = Settings()
