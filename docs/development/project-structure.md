# Project Structure

The repository separates the backend, frontend, documentation, and test suite.
Generated data and local configuration are ignored by Git.

```text
chatvault-ai/
├── app/
│   ├── main.py                     FastAPI app, CORS, lifespan, routers
│   ├── api/
│   │   ├── dependencies.py         Embedding, chat, retriever, store wiring
│   │   ├── schemas.py              Pydantic request/response models
│   │   └── routes/
│   │       ├── health.py           GET /health
│   │       ├── import_chat.py      POST /import/url
│   │       ├── conversations.py    List, detail, delete
│   │       ├── exports.py          PDF and DOCX downloads
│   │       ├── indexing.py         Index, index all, rebuild, status, delete
│   │       ├── stats.py            GET /stats
│   │       ├── search.py           POST /search
│   │       ├── chat.py             POST /chat
│   │       └── system.py           GET /models/status
│   ├── core/
│   │   └── config.py               Pydantic settings and validation
│   ├── database/
│   │   ├── connection.py           Engine, session, init_db, SQLite pragmas
│   │   ├── models.py               Conversation, Message, IndexState
│   │   └── repository.py           Queries and mutations
│   ├── embeddings/
│   │   └── ollama_embeddings.py    Batch embedding client
│   ├── generators/
│   │   ├── pdf_generator.py        ReportLab PDF renderer
│   │   ├── docx_generator.py       python-docx renderer
│   │   ├── markdown_blocks.py      Shared Markdown block parser
│   │   └── utils.py                Output paths, block splitting
│   ├── ingestion/
│   │   ├── url_validator.py        HTTPS/host/path validation
│   │   ├── fetcher.py              Safe HTTP fetch with limits
│   │   └── extractor.py            Serialized payload and HTML extraction
│   ├── processing/
│   │   ├── text_cleaner.py         ChatGPT annotation cleanup
│   │   ├── chunker.py              Message-aware chunking
│   │   ├── index_status.py         Index status enum
│   │   └── indexing_service.py     Lock, state machine, embed/upsert
│   ├── rag/
│   │   ├── retriever.py            Query embedding and ChromaDB search
│   │   ├── chat_service.py         Context, history, prompt, answer
│   │   └── ollama_chat.py          Non-streaming chat client
│   └── vectorstore/
│       └── chroma_store.py         Persistent cosine collection adapter
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 Lazy routes
│   │   ├── main.tsx                React root
│   │   ├── index.css               Tailwind theme
│   │   ├── components/             Layout, common, chat, dashboard
│   │   ├── hooks/queries.ts        TanStack Query hooks
│   │   ├── lib/                    Class names and formatting
│   │   ├── pages/                  Dashboard, AIChat, Library, Import,
│   │   │                           Conversation, Settings, NotFound
│   │   ├── services/               axios API clients
│   │   └── types/api.ts            Frontend API types
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
├── docs/                           MkDocs source
│   ├── getting-started/
│   ├── user-guide/
│   ├── guides/
│   ├── concepts/
│   ├── api-reference/
│   ├── development/
│   ├── releases/
│   └── assets/
├── tests/
│   ├── conftest.py                 Isolated DB and dependency overrides
│   ├── fakes.py                    Fake embedding and chat clients
│   ├── fixtures/                   HTML and payload fixtures
│   └── test_*.py                   Unit and API contract tests
├── .github/workflows/
│   ├── ci.yml                      Backend tests, frontend lint/build
│   ├── release.yml                 GitHub release on v* tags
│   └── docs.yml                    Strict docs build and gh-pages publish
├── mkdocs.yml
├── requirements-docs.txt
├── requirements.txt
├── pyproject.toml
├── Makefile
├── run.py
├── setup.py
├── .env.example
├── CHANGELOG.md
├── CONTRIBUTING.md
├── RELEASE.md
├── SECURITY.md
└── README.md
```

## Backend module boundaries

| Package | Depends on | Should not own |
| --- | --- | --- |
| `api` | schemas, database, processing, rag, vectorstore | Network parsing or model prompts |
| `ingestion` | text cleaner | HTTP routing or database sessions |
| `processing` | config, embeddings, vectorstore, repository | HTTP responses |
| `rag` | embeddings, vectorstore, database | HTTP status mapping |
| `vectorstore` | config | Conversation records |
| `database` | config | Embeddings or prompts |
| `generators` | text cleaner, SQLAlchemy models | Retrieval or models |

Routers translate domain exceptions to HTTP. The domain modules raise typed
exceptions such as `OllamaUnavailableError`, `VectorStoreConfigurationError`, and
`NoIndexableContentError`.

## Frontend boundaries

- Pages own layout and user interaction.
- Hooks own cache keys and invalidation.
- Services own HTTP paths and response typing.
- Components stay presentational where practical.

API types are duplicated in `frontend/src/types/api.ts` and
`app/api/schemas.py`. Change both together when a contract changes.

## Generated and ignored paths

| Path | Status |
| --- | --- |
| `.venv/` | Ignored |
| `.env`, `frontend/.env` | Ignored |
| `storage/chatvault.db` | Ignored |
| `storage/chroma/` | Ignored |
| `storage/generated/` | Ignored contents |
| `frontend/dist/` | Ignored |
| `site/` | MkDocs build output, ignored |
| `__pycache__/`, `.pytest_cache/` | Ignored |
| `brag-output-*/` | Ignored demo artifacts |

`docs/` is source and belongs on `main`. The generated `site/` directory is not
committed; the documentation workflow publishes it to the `gh-pages` branch.

## Related pages

- [Development Setup](development-setup.md)
- [Testing](testing.md)
- [Architecture](../concepts/architecture.md)
