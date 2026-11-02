# Configuration

ChatVault AI reads backend configuration from environment variables and an
optional root `.env` file through `pydantic-settings`. The settings class lives
in `app/core/config.py`; it is the authoritative list.

The frontend has one build-time variable in `frontend/.env`.
Changing backend settings requires a restart. Changing frontend settings
requires a Vite restart or a new production build.

## Backend settings

| Variable | Default | Constraints | Effect |
| --- | --- | --- | --- |
| `APP_NAME` | `ChatVault AI` | string | FastAPI title and health response |
| `APP_VERSION` | `1.0.0` | string | FastAPI version, health response, launcher `--version` |
| `DEBUG` | `True` | boolean | Passed to `FastAPI(debug=...)` |
| `API_V1_PREFIX` | `/api/v1` | string | Prefix for every API router |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL string | Ollama endpoint for embeddings, chat, and model listing |
| `OLLAMA_CHAT_MODEL` | `llama3.2:3b` | model name | Chat generation model |
| `OLLAMA_CHAT_TIMEOUT` | `180.0` | `> 0` seconds | Chat request timeout |
| `OLLAMA_CHAT_TEMPERATURE` | `0.2` | `0` to `2` | Chat sampling temperature |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | model name | Embedding model; changing it requires an index rebuild |
| `OLLAMA_EMBED_TIMEOUT` | `120.0` | `> 0` seconds | Embedding request timeout |
| `OLLAMA_EMBED_BATCH_SIZE` | `16` | `1` to `128` texts | Batch size for `/api/embed` requests |
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | JSON array of origins | Browser origins allowed to call the API |
| `CHAT_TOP_K` | `5` | `1` to `10` | Default retrieved chunks for chat when the request omits `top_k` |
| `CHAT_MAX_HISTORY_MESSAGES` | `10` | `0` to `50` | Number of recent history turns included in the prompt |
| `CHAT_MAX_CONTEXT_CHARS` | `12000` | `1000` to `100000` | Approximate character budget for retrieved context |
| `CHROMA_DB_PATH` | `storage/chroma` | path | Persistent ChromaDB directory |
| `CHROMA_COLLECTION_NAME` | `chatvault_conversations` | string | ChromaDB collection name |
| `CHROMA_TELEMETRY` | `False` | boolean | Passed as `anonymized_telemetry` to ChromaDB |
| `DATABASE_URL` | `sqlite:///./storage/chatvault.db` | SQLAlchemy URL | Primary database |
| `SQL_ECHO` | `False` | boolean | SQLAlchemy statement logging |
| `CHUNK_SIZE_TOKENS` | `500` | `50` to `2000` | Target chunk size in approximate tokens |
| `CHUNK_OVERLAP_TOKENS` | `75` | `>= 0`, smaller than chunk size | Overlap between chunks within one message |
| `CHUNK_MIN_TOKENS` | `30` | `>= 0`, no larger than chunk size | Minimum chunk size before merging a tiny tail |
| `CHUNKING_VERSION` | `message-aware-v1` | non-empty string | Part of the index signature; changing it marks chunks stale |

Invalid values stop application startup with a Pydantic validation error. In
particular:

- `CHUNK_OVERLAP_TOKENS` must be smaller than `CHUNK_SIZE_TOKENS`.
- `CHUNK_MIN_TOKENS` cannot exceed `CHUNK_SIZE_TOKENS`.
- `CHUNKING_VERSION` cannot be blank.

## Example `.env`

```dotenv
APP_NAME=ChatVault AI
APP_VERSION=1.0.0
DEBUG=True

API_V1_PREFIX=/api/v1

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_CHAT_TIMEOUT=180
OLLAMA_CHAT_TEMPERATURE=0.2
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_EMBED_TIMEOUT=120
OLLAMA_EMBED_BATCH_SIZE=16

# JSON array of allowed browser origins.
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

# Retrieval-augmented chat.
CHAT_TOP_K=5
CHAT_MAX_HISTORY_MESSAGES=10
CHAT_MAX_CONTEXT_CHARS=12000

CHROMA_DB_PATH=storage/chroma
CHROMA_COLLECTION_NAME=chatvault_conversations
CHROMA_TELEMETRY=false

DATABASE_URL=sqlite:///./storage/chatvault.db
SQL_ECHO=false

CHUNK_SIZE_TOKENS=500
CHUNK_OVERLAP_TOKENS=75
CHUNK_MIN_TOKENS=30
CHUNKING_VERSION=message-aware-v1
```

`CORS_ORIGINS` must be valid JSON. Use double quotes. A comma-separated string is
not accepted.

## Frontend setting

| Variable | Default when omitted | Effect |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Base URL used by axios for every API call |

Example `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Vite embeds this value at build time. Rebuild the frontend after changing it.

## Paths and working directory

Relative paths such as `storage/chatvault.db` and `storage/chroma` are resolved
from the process working directory. Start the backend from the repository root,
or use absolute paths in `DATABASE_URL` and `CHROMA_DB_PATH`.

The database connection creates `storage/` at import time. ChromaDB creates its
directory when the collection is first opened.

## Configuration that affects indexing

The index signature is composed of:

```text
OLLAMA_EMBED_MODEL | CHUNKING_VERSION | CHUNK_SIZE_TOKENS |
CHUNK_OVERLAP_TOKENS | CHUNK_MIN_TOKENS
```

If the signature differs from a conversation's stored signature, the
conversation is reported as **stale** and can be reindexed. If the embedding
model or vector dimension changes, the whole collection must be rebuilt:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/index/rebuild
```

`OLLAMA_CHAT_MODEL`, `OLLAMA_CHAT_TEMPERATURE`, history limits, and context limits
do not affect stored vectors.

## Security-related settings

- Keep `DATABASE_URL` and `CHROMA_DB_PATH` inside a private directory.
- Keep `CORS_ORIGINS` limited to origins you actually use.
- `DEBUG=True` is convenient locally. Do not expose a debug backend to an
  untrusted network.
- There is no authentication layer. Run the backend on `127.0.0.1` unless you
  intentionally put it behind a trusted reverse proxy with authentication.
- `.env` is ignored by Git. Never commit model provider credentials or private
  conversation data.

## Related pages

- [Installation](installation.md)
- [Model Configuration](../guides/model-configuration.md)
- [Ollama Setup](../guides/ollama-setup.md)
- [Privacy and Security](../concepts/privacy-and-security.md)
