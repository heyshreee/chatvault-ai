# Requirements

## Supported platform

ChatVault AI is developed and tested on Linux, and the CI workflow runs on
Ubuntu with Python 3.13 and Node.js 22. The application is a local web stack and
does not contain platform-specific backend code, but two practical limits matter:

- **PDF export assumes Linux font paths.** The PDF generator loads DejaVu fonts
  from `/usr/share/fonts/truetype/dejavu`. On Debian/Ubuntu, install
  `fonts-dejavu-core`. If those files are absent, PDF export returns HTTP 500.
  DOCX export does not require the font files.
- **CI does not exercise macOS or Windows.** DOCX export, the API, SQLite, and
  ChromaDB are expected to work anywhere Python 3.13 and the dependencies
  install, but only Linux is continuously verified.

## Version matrix

| Dependency | Required version | Why |
| --- | --- | --- |
| Python | **3.13.x** | `pyproject.toml` declares `>=3.13,<3.14`; ChromaDB's `grpcio` dependency has no cp314 wheel for the tested stack |
| Node.js | **20+** | Frontend toolchain; CI uses Node.js 22 |
| npm | Bundled with Node.js | `npm ci` uses `frontend/package-lock.json` |
| Ollama | Current release | Local embedding and chat runtime |
| ChromaDB | `1.5.9` | Pinned in `requirements.txt` and `pyproject.toml` |
| SQLite | Bundled with Python | No external database server |

## Python packages

The backend installs from `requirements.txt`:

```text
fastapi[standard]
pydantic-settings
python-dotenv
httpx
beautifulsoup4
pytest
sqlalchemy>=2.0
reportlab
python-docx
chromadb==1.5.9
```

`pyproject.toml` also exposes the package with these runtime dependencies and
the optional `dev` extra (`pytest`, `pytest-cov`). The normal test suite uses
fake embedding and chat clients, so it does not need Ollama.

## Frontend packages

The React frontend uses:

| Package | Role |
| --- | --- |
| React 19 and React DOM 19 | UI runtime |
| Vite 8 and `@vitejs/plugin-react` | Development server and production build |
| TypeScript 7 | Type checking during `npm run build` |
| Tailwind CSS 4 | Styling |
| TanStack Query 5 | API data fetching and cache invalidation |
| React Router 7 | Client routes |
| axios | HTTP client |
| react-markdown and remark-gfm | Markdown rendering |
| prism-react-renderer | Code highlighting |
| lucide-react | Icons |
| oxlint | Linting |

## Ollama models

The defaults in `app/core/config.py` are:

| Purpose | Model | Pull command |
| --- | --- | --- |
| Embeddings | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| Chat | `llama3.2:3b` | `ollama pull llama3.2:3b` |

Both can be changed with `OLLAMA_EMBED_MODEL` and `OLLAMA_CHAT_MODEL`. Changing
the embedding model requires a full index rebuild because existing vectors are
incompatible. Changing the chat model does not require reindexing. See
[Model Configuration](../guides/model-configuration.md).

## Hardware and disk

No specific CPU, GPU, or memory figures are enforced by the application. Local
model performance and memory use are determined by Ollama and the selected
models. Plan for:

- Ollama model downloads and runtime memory.
- The SQLite database under `storage/chatvault.db`.
- ChromaDB persistence under `storage/chroma/`, which grows with the number of
  indexed chunks.
- Generated PDF/DOCX files under `storage/generated/`.

The backend fetches at most **5 MB** per imported share page and applies a
**20 second** request timeout.

## Network and ports

| Port | Service | Default binding |
| --- | --- | --- |
| `8000` | FastAPI backend | `127.0.0.1` via `run.py`; Uvicorn defaults to `127.0.0.1` |
| `5173` | Vite frontend | Local development server |
| `11434` | Ollama | Local service |

The browser must be able to reach the backend, and the backend must be able to
reach Ollama and `chatgpt.com` during an import. CORS defaults allow only
`http://localhost:5173` and `http://127.0.0.1:5173`.

## What is not required

- No ChatGPT account or API key. Only public share pages are fetched.
- No hosted vector database.
- No hosted model provider or API key.
- No Docker setup is documented or shipped.
- No Node.js server is needed in production; `npm run build` produces static
  assets that can be served by any static file server.

## Next

- [Installation](installation.md)
- [Configuration](configuration.md)
- [Ollama Setup](../guides/ollama-setup.md)
