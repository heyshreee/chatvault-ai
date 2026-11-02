# Getting Started

ChatVault AI runs as two local processes: a FastAPI backend on port `8000` and
a Vite development server on port `5173`. Ollama runs separately on port
`11434`.

## What you need

| Component | Requirement |
| --- | --- |
| Python | **3.13** exactly; Python 3.14 is not supported by the current ChromaDB dependency chain |
| Node.js | **20 or newer** with npm |
| Ollama | Reachable at `http://localhost:11434` |
| Models | `nomic-embed-text` for embeddings and `llama3.2:3b` for chat |
| Disk | Room for the SQLite database, ChromaDB files, Ollama models, and generated PDF/DOCX files |

See [Requirements](requirements.md) for platform notes and known limitations.

## Five-step start

1. **Install dependencies**

    ```bash
    make install
    ```

    This creates `.venv`, installs the backend requirements, runs `npm ci` in
    `frontend/`, and copies the example environment files when they are missing.

2. **Start Ollama and pull the models**

    ```bash
    ollama serve
    ollama pull nomic-embed-text
    ollama pull llama3.2:3b
    ```

3. **Start the backend**

    ```bash
    make run
    ```

    The API is available at <http://127.0.0.1:8000>. Swagger UI is at
    <http://127.0.0.1:8000/docs>.

4. **Start the frontend**

    ```bash
    cd frontend
    npm run dev
    ```

5. **Import your first conversation**

    Open <http://127.0.0.1:5173>, go to **Import**, and paste a public
    `https://chatgpt.com/share/<share-id>` link. The backend fetches and stores
    the conversation, then the frontend asks it to build the vector index.

## Where your data lives

| Path | Contents | Can it be rebuilt? |
| --- | --- | --- |
| `storage/chatvault.db` | Conversations, messages, index state | No; back it up |
| `storage/chroma/` | Derived embeddings and vector metadata | Yes, from SQLite |
| `storage/generated/` | PDF and DOCX files produced by exports | Yes, by exporting again |
| `.env` | Backend configuration and secrets | No; keep it private |
| `frontend/.env` | Frontend API base URL | Trivial to recreate |

SQLite is the source of truth. Deleting `storage/chroma/` or using the index
rebuild action removes only the derived search index, not your conversations.
See [Backup and Restore](../guides/backup-and-restore.md) for safe copies.

## Choose your path

<div class="cv-grid" markdown>

<div class="cv-card" markdown>
### I want to run it
Follow [Installation](installation.md), then the
[Quickstart](quickstart.md).
</div>

<div class="cv-card" markdown>
### I need to change defaults
Read [Configuration](configuration.md) for every environment variable and
constraint.
</div>

<div class="cv-card" markdown>
### Ollama is not working
Use [Ollama Setup](../guides/ollama-setup.md) and
[Troubleshooting](../guides/troubleshooting.md).
</div>

<div class="cv-card" markdown>
### I want to understand the design
Start with [Architecture](../concepts/architecture.md) and
[RAG Explained](../concepts/rag-explained.md).
</div>

</div>

## Next steps

- [Requirements](requirements.md)
- [Installation](installation.md)
- [Configuration](configuration.md)
- [Quickstart](quickstart.md)
