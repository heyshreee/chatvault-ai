# Installation

These instructions install ChatVault AI from source. Run all commands from the
repository root unless a step says otherwise.

## 1. Clone the repository

```bash
git clone https://github.com/heyshreee/chatvault-ai.git
cd chatvault-ai
```

To work against the upstream project:

```bash
git clone https://github.com/makitdev/chatvault-ai.git
cd chatvault-ai
```

## 2. Install backend and frontend dependencies

The supported shortcut is:

```bash
make install
```

`make install` runs `make setup` and `make frontend-install`:

- `uv venv --python 3.13 .venv`
- `uv pip install --python .venv/bin/python -r requirements.txt`
- Copies `.env.example` to `.env` if `.env` is missing
- `npm ci` in `frontend/`
- Copies `frontend/.env.example` to `frontend/.env` if it is missing

### Manual backend install

If you do not want to use `make`:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
```

The backend uses Python 3.13. Do not use Python 3.14: the pinned ChromaDB stack
does not have a compatible `grpcio` wheel.

### Manual frontend install

```bash
cd frontend
npm ci
cp .env.example .env
cd ..
```

`npm ci` requires `frontend/package-lock.json`, which is committed.

## 3. Install PDF fonts on Linux

PDF export loads DejaVu fonts from `/usr/share/fonts/truetype/dejavu`:

```bash
sudo apt-get install fonts-dejavu-core
```

Without those font files, PDF export returns `500 Unable to generate PDF.`
DOCX export still works. This path is a current implementation limitation, not a
configurable option.

## 4. Configure the environment

The root `.env` is read by `pydantic-settings`. The defaults match local
development:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_EMBED_MODEL=nomic-embed-text
DATABASE_URL=sqlite:///./storage/chatvault.db
CHROMA_DB_PATH=storage/chroma
```

The frontend reads `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

If `VITE_API_BASE_URL` is omitted, the frontend falls back to
`http://127.0.0.1:8000/api/v1`. If you serve the frontend from another origin,
add that origin to `CORS_ORIGINS` in the root `.env` and restart the backend.

Every setting is documented in [Configuration](configuration.md).

## 5. Start Ollama and pull models

```bash
ollama serve
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Verify Ollama is reachable:

```bash
curl http://localhost:11434/api/tags
```

`ollama serve` is usually not needed if the Ollama desktop application is
already running.

## 6. Start the backend

```bash
.venv/bin/uvicorn app.main:app --reload
```

Or use the packaged launcher:

```bash
.venv/bin/python run.py
# equivalent to: make run
```

`run.py` accepts `--host`, `--port`, `--reload`, `--log-level`, and `--version`:

```bash
.venv/bin/python run.py --host 0.0.0.0 --port 8000 --reload
```

Check the API:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "application": "ChatVault AI",
  "version": "1.0.0"
}
```

Swagger UI: <http://127.0.0.1:8000/docs>  
OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## 7. Start the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>.

## 8. Production frontend build

```bash
cd frontend
npm run build
npm run preview
```

`npm run build` runs `tsc -b` and `vite build`, producing `frontend/dist/`. The
backend does not serve this directory; use a static file server or the Vite
preview server.

## Verify the installation

1. The health endpoint returns `200` with `"status": "healthy"`.
2. The frontend loads and the sidebar shows Dashboard, AI Chat, Library, Import,
   and Settings.
3. Settings reports Ollama as connected and both configured models as available.
4. Import a public share URL and confirm that indexing completes.

If a check fails, see [Troubleshooting](../guides/troubleshooting.md).

## Updating

```bash
git pull --ff-only origin main
make install
```

Restart both processes after changing `.env`. If the embedding model or chunking
configuration changed, rebuild the index from Settings or with
`POST /api/v1/index/rebuild`.
