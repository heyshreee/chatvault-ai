# Contributing to ChatVault AI

Thanks for taking the time to improve ChatVault AI. This project is a
local-first tool, so contributions should preserve the guarantees that make it
useful: conversation data stays on the user's machine, SQLite remains the source
of truth, and ChromaDB remains a rebuildable derived index.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- Search existing [issues](https://github.com/heyshreee/chatvault-ai/issues)
  before opening a new one.
- For security problems, **do not open a public issue**. Follow
  [SECURITY.md](SECURITY.md).
- For large features or behavior changes, open an issue first so the approach
  can be discussed.

## Development setup

Requirements:

- Python 3.13 (Python 3.14 is not supported yet because ChromaDB's `grpcio`
  dependency does not have a cp314 wheel).
- Node.js 20+ and npm.
- Ollama for real embeddings and chat. The normal test suite uses fakes and does
  not require Ollama.

Clone your fork and install dependencies:

```bash
git clone https://github.com/<your-user>/chatvault-ai.git
cd chatvault-ai
git remote add upstream https://github.com/makitdev/chatvault-ai.git
make install
```

`make install` creates `.venv`, installs `requirements.txt`, installs frontend
dependencies with `npm ci`, and copies the example environment files when they
are missing.

Pull the default models:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

## Running locally

Backend:

```bash
make run
# or: make dev   # auto-reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>. API documentation is available at
<http://127.0.0.1:8000/docs>.

## Checks

Run the same checks as CI before opening a pull request:

```bash
make check
```

That runs:

- Python bytecode compilation for `app/`, `run.py`, and `tests/`.
- Frontend linting with oxlint.
- The backend pytest suite.
- The production frontend build.

Individual commands:

```bash
make test
make lint
make build
make test-ollama   # requires a running Ollama with nomic-embed-text
```

The real Ollama integration test is opt-in:

```bash
RUN_OLLAMA_TESTS=1 .venv/bin/python -m pytest tests/test_ollama_integration.py -q
```

## Project layout

| Path | Purpose |
| --- | --- |
| `app/api/` | FastAPI routes, schemas, and dependency wiring. |
| `app/ingestion/` | ChatGPT share URL validation, fetching, and extraction. |
| `app/database/` | SQLAlchemy models, connection setup, and repository functions. |
| `app/processing/` | Chunking, indexing state, and ChatGPT annotation cleanup. |
| `app/embeddings/` | Ollama embedding client. |
| `app/vectorstore/` | ChromaDB persistence and queries. |
| `app/rag/` | Retrieval, prompt assembly, and Ollama chat client. |
| `app/generators/` | PDF/DOCX rendering and shared Markdown block parsing. |
| `frontend/src/` | React pages, components, hooks, services, and types. |
| `tests/` | Backend unit and contract tests. |

## Coding guidelines

- Use Python 3.13 syntax and keep type hints on public functions.
- Keep API response shapes stable; update `app/api/schemas.py` and the frontend
  types together when a contract changes.
- Add or update tests for behavior changes. Prefer the existing fake clients in
  `tests/fakes.py` over live Ollama calls.
- Preserve the local-first security model:
  - Do not send conversation text to hosted services.
  - Treat imported conversation content as untrusted data.
  - Do not log conversation text or secrets.
  - Keep SSRF protections in the fetcher and URL validator intact.
- Keep generated artifacts out of Git: `storage/chatvault.db`,
  `storage/chroma/`, `storage/generated/`, `.env`, and `frontend/dist/` are
  ignored.
- Match the existing frontend style: TypeScript, functional components,
  Tailwind utilities, TanStack Query, and accessible labels.
- Keep documentation and `.env.example` in sync with configuration changes.

## Branches and commits

Use a short, descriptive branch name:

```text
feat/streaming-chat
fix/docx-table-width
docs/release-checklist
```

Write commits in the imperative mood and keep each commit focused:

```text
feat: add conversation export retry
fix: preserve code indentation in PDF exports
docs: document the Ollama model override
```

## Pull requests

A good pull request:

- Explains the problem and the chosen approach.
- Links the related issue, when one exists.
- Includes tests for new behavior and regression fixes.
- Updates documentation for user-visible changes.
- Passes `make check`.
- Avoids unrelated formatting churn.

Open the pull request against `main` on
[heyshreee/chatvault-ai](https://github.com/heyshreee/chatvault-ai). Maintainers
may ask for changes before merging.

## License

By contributing, you agree that your contributions are licensed under the
[GNU General Public License v3.0](LICENSE).
