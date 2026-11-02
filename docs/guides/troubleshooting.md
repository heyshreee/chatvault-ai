# Troubleshooting

Start with the health and status endpoints. They separate failures in the
frontend, backend, SQLite, ChromaDB, and Ollama.

```bash
curl http://127.0.0.1:8000/api/v1/health
curl http://127.0.0.1:8000/api/v1/models/status
curl http://127.0.0.1:8000/api/v1/index/status
curl http://localhost:11434/api/tags
```

`GET /api/v1/models/status` returns HTTP `200` even when Ollama is down; inspect
`ollama.available`, `chat_model.available`, `embedding_model.available`, and
`vector_store.available` instead of relying on the status code.

## The frontend cannot reach the API

Symptoms: the Dashboard shows an error panel, requests fail with a network error,
or the browser console reports CORS.

Check:

1. The backend is running on `127.0.0.1:8000`:

    ```bash
    curl -i http://127.0.0.1:8000/api/v1/health
    ```

2. `frontend/.env` points at the right base URL:

    ```dotenv
    VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
    ```

3. The browser origin is allowed. Defaults allow only
   `http://localhost:5173` and `http://127.0.0.1:5173`.
4. Restart Vite after changing `frontend/.env`; the value is embedded at build
   time.

To add another origin, edit `CORS_ORIGINS` in the root `.env` as a JSON array and
restart the backend:

```dotenv
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:4173"]
```

A comma-separated value is not valid JSON and prevents startup.

## Ollama is unavailable

API message:

```text
Ollama is unavailable. Start Ollama and try again.
```

Check the service and the configured URL:

```bash
curl http://localhost:11434/api/tags
```

If it fails:

```bash
ollama serve
```

Confirm `OLLAMA_BASE_URL` in `.env`. ChatVault's Ollama clients use
`trust_env=False`, so `HTTP_PROXY` and similar variables are ignored for these
requests.

## A model is missing

API messages:

```text
Embedding model 'nomic-embed-text' is not available. Run: ollama pull nomic-embed-text
Chat model 'llama3.2:3b' is not available. Run: ollama pull llama3.2:3b
```

Fix:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Both must appear in `ollama list`. Model matching accepts an unversioned
configured name against a tagged installed name, but explicit tags are easier to
reason about.

## Indexing returns 409

Common causes:

| Message | Cause | Fix |
| --- | --- | --- |
| `Another indexing operation is already running.` | A process-wide lock is held | Wait for the current request; retry |
| `This conversation is already being indexed.` | Same conversation state is `indexing` | Wait or restart if the state is left over |
| `The embedding model has changed. Rebuild the index.` | Collection provenance differs from `.env` | `POST /api/v1/index/rebuild` |
| `The ChromaDB collection has unknown embedding provenance. Rebuild the index.` | Collection has vectors but no model metadata | Rebuild |
| `The embedding dimension has changed. Rebuild the index.` | New model has a different dimension | Rebuild |
| `The existing ChromaDB collection does not use cosine distance. Rebuild the index.` | Collection was created with another metric | Rebuild |

A rebuild deletes and recreates the ChromaDB collection. SQLite conversations
are untouched.

## Indexing returns 422

```text
Conversation has no indexable text.
```

The conversation exists but produced no chunks. This can happen if the stored
messages are empty after cleaning. Delete and re-import the conversation, or
inspect it with `GET /api/v1/conversations/{id}`.

## Indexing returns 503

Either Ollama or ChromaDB is unavailable. `GET /api/v1/index/status` includes a
public `vector_store_error` when ChromaDB cannot be read. Check:

```bash
curl http://127.0.0.1:8000/api/v1/index/status
ls -la storage/chroma
```

If the collection directory is corrupt, stop the backend, back up
`storage/chatvault.db`, remove `storage/chroma/`, then rebuild the index. Never
delete the SQLite database to fix the vector index.

## Search returns no results

`POST /api/v1/search` returns HTTP `200` with `"total": 0` when the collection is
empty or no chunks are available. Check:

1. At least one conversation is imported.
2. Its status is `indexed`, not `failed` or `stale`.
3. `GET /api/v1/index/status` reports `vectors > 0`.
4. The embedding model is installed.
5. The index does not require a rebuild.

Search has no similarity threshold. A query can return weakly related chunks;
distance values are raw cosine distances where lower is closer.

## Chat returns `no_sources`

This is not an error. Retrieval found no indexed chunks, so the chat model was
not called. Confirm the library is indexed and try a question that uses wording
close to the stored conversation. See [AI Chat](../user-guide/ai-chat.md).

## Chat returns 502

```text
Ollama returned an invalid chat response.
```

Ollama responded, but the payload did not contain a non-empty assistant message.
Check the Ollama version and test the model directly:

```bash
curl -X POST http://localhost:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

A generic `Ollama rejected the request (HTTP n).` message means Ollama returned
an error other than a missing model. Inspect the Ollama service logs.

## PDF export returns 500

The PDF generator loads fonts from:

```text
/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
```

On Debian or Ubuntu:

```bash
sudo apt-get install fonts-dejavu-core
```

The path is not configurable in `v1.0.0`. DOCX export works without these files.

## Import fails

| Message | Meaning |
| --- | --- |
| `Only HTTPS URLs are allowed.` | URL uses `http://` |
| `Only chatgpt.com URLs are allowed.` | Host is not `chatgpt.com` |
| `URL credentials are not allowed.` | URL contains a username or password |
| `Custom ports are not allowed.` | URL uses a non-default port |
| `Invalid ChatGPT shared conversation URL.` | Path is not `/share/<id>` |
| `Unable to fetch shared conversation: ChatGPT returned HTTP 404.` | Share link is wrong or removed |
| `Unable to fetch shared conversation: ChatGPT returned HTTP 403.` | Page is not public or the request was blocked |
| `Unable to fetch shared conversation: Response exceeds the 5 MB size limit.` | Page is too large |
| `Unable to extract conversation: ...` | Page format changed or has no supported text |
| `Unable to save conversation to database.` | SQLite write failed; check disk and permissions |

The importer does not retry failed imports automatically. It also does not update
an existing conversation. Delete it first if you need a fresh copy.

## Database or disk problems

Check free space and permissions:

```bash
df -h .
ls -la storage storage/chroma
```

SQLite needs write access to `storage/`. ChromaDB needs write access to
`storage/chroma/`. Generated exports go to `storage/generated/`.

If the database is locked, stop extra backend processes. ChatVault uses a single
local process model and does not coordinate writes across multiple servers.

## Server restarted during indexing

On startup, the lifespan handler marks any `indexing` state as `failed` with:

```text
Indexing was interrupted before completion.
```

Reindex that conversation, or run a full rebuild from Settings.

## Frontend build or lint failures

```bash
cd frontend
npm ci
npm run lint
npm run build
```

`npm run build` runs `tsc -b` before `vite build`. Type errors fail the build.
CI uses Node.js 22.

## Backend test failures

```bash
.venv/bin/python -m pytest -q
```

The normal suite uses fake embedding and chat clients and does not need Ollama.
The real integration test is opt-in:

```bash
RUN_OLLAMA_TESTS=1 .venv/bin/python -m pytest -q tests/test_ollama_integration.py
```

## Collecting a useful bug report

Include:

- ChatVault AI version and commit.
- Operating system, Python version, Node.js version, and Ollama version.
- Whether the problem affects the UI, API, indexing, or export.
- The HTTP status and `detail` message.
- Relevant output from `GET /api/v1/models/status` and
  `GET /api/v1/index/status`.
- Whether Ollama is local or remote.

Do not include conversation text, share links, API keys, or `.env` contents in a
public issue. Report security problems through the process in
[Privacy and Security](../concepts/privacy-and-security.md).

## Related pages

- [Requirements](../getting-started/requirements.md)
- [Ollama Setup](ollama-setup.md)
- [Backup and Restore](backup-and-restore.md)
- [Errors](../api-reference/errors.md)
