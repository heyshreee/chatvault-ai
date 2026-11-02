# Development Setup

## Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Python | **3.13.x** | 3.14 is not supported by the pinned ChromaDB stack |
| uv | Current | Used by `make setup`; pip works too |
| Node.js | 20+ | CI uses Node.js 22 |
| npm | Bundled with Node.js | Uses `frontend/package-lock.json` |
| Ollama | Current | Required for real indexing and chat |
| Git | Current | |

The normal test suite does not require Ollama.

## Clone and install

```bash
git clone https://github.com/<your-user>/chatvault-ai.git
cd chatvault-ai

git remote add upstream https://github.com/makitdev/chatvault-ai.git

make install
```

`make install` runs:

1. `uv venv --python 3.13 .venv`
2. `uv pip install --python .venv/bin/python -r requirements.txt`
3. Copies `.env.example` to `.env` if missing.
4. `npm ci` in `frontend/`.
5. Copies `frontend/.env.example` to `frontend/.env` if missing.

Manual equivalent:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env

cd frontend
npm ci
cp .env.example .env
cd ..
```

## Pull models

```bash
ollama serve
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Verify:

```bash
curl http://localhost:11434/api/tags
```

## Run the backend

```bash
make run
# or with auto-reload:
make dev
```

`make run` calls `.venv/bin/python run.py` and binds `127.0.0.1:8000` by default.
`make dev` runs Uvicorn with `--reload`.

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Swagger UI: <http://127.0.0.1:8000/docs>

## Run the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>. The frontend reads
`VITE_API_BASE_URL` from `frontend/.env`, defaulting to
`http://127.0.0.1:8000/api/v1`.

## Environment files

| File | Purpose |
| --- | --- |
| `.env` | Backend settings read by `pydantic-settings` |
| `frontend/.env` | Vite API base URL |

Restart the backend after changing `.env`. Restart Vite after changing
`frontend/.env`, because Vite embeds the value at build time.

See [Configuration](../getting-started/configuration.md) for every variable.

## Documentation environment

The documentation dependencies are separate from the application requirements.
Use a dedicated environment:

```bash
python3.13 -m venv .docs-venv
. .docs-venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-docs.txt
```

Serve locally with live reload:

```bash
mkdocs serve
```

Build with the same strict validation used by CI:

```bash
mkdocs build --strict
```

Output goes to `site/`. The build fails on missing nav pages, broken internal
links, and unrecognized anchors.

The default `site_url` and repository links target the fork. To build for the
upstream mirror:

```bash
DOCS_SITE_URL=https://makitdev.github.io/chatvault-ai/ \
DOCS_REPO_URL=https://github.com/makitdev/chatvault-ai \
DOCS_REPO_NAME=makitdev/chatvault-ai \
mkdocs build --strict
```

## Checks

```bash
make check
```

This runs:

- Python bytecode compilation for `app/`, `run.py`, and `tests/`.
- Frontend lint with oxlint.
- Backend tests with pytest.
- Production frontend build (`tsc -b` and `vite build`).

Individual targets:

```bash
make test
make lint
make build
make test-ollama
```

## Common setup problems

| Problem | Fix |
| --- | --- |
| `uv: command not found` | Install uv, or use the manual `python -m venv` path |
| Python 3.14 selected | Recreate the venv with Python 3.13 |
| `npm ci` fails | Ensure `frontend/package-lock.json` exists and Node.js is 20+ |
| Frontend cannot reach API | Check `VITE_API_BASE_URL` and restart Vite |
| CORS error | Add the browser origin to `CORS_ORIGINS` and restart the backend |
| ChromaDB install fails | Confirm Python 3.13 and the pinned `chromadb==1.5.9` |
| `mkdocs: command not found` | Install `requirements-docs.txt` in the active environment |

## Related pages

- [Testing](testing.md)
- [Project Structure](project-structure.md)
- [Contributing](contributing.md)
- [Troubleshooting](../guides/troubleshooting.md)
