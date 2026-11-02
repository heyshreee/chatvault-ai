# Testing

ChatVault AI has a backend test suite built on pytest and FastAPI's `TestClient`,
plus frontend lint and production build checks. The normal suite uses fake model
clients and does not require Ollama.

## Commands

```bash
# Backend suite
make test
# equivalent:
.venv/bin/python -m pytest -q

# Frontend lint
cd frontend && npm run lint

# Frontend production build
cd frontend && npm run build

# Everything CI runs
make check
```

`make check` runs Python compilation, frontend lint, backend tests, and the
production build.

## Test layout

| File | Focus |
| --- | --- |
| `tests/conftest.py` | Temporary SQLite engine, dependency overrides, sample data |
| `tests/fakes.py` | Fake embedding and chat clients |
| `tests/test_health.py` | Health endpoint |
| `tests/test_url_validator.py` | HTTPS, host, path, credentials, port rules |
| `tests/test_fetcher.py` | Timeouts, redirects, size limits, content types |
| `tests/test_extractor.py` | HTML fallback extraction |
| `tests/test_serialized_extractor.py` | ChatGPT serialized payload extraction |
| `tests/test_import_chat.py` | Import API success, duplicate, and error mapping |
| `tests/test_chunker.py` | Message boundaries, splitting, overlap, size limits |
| `tests/test_chroma_store.py` | Collection lifecycle, provenance, upsert, query, delete |
| `tests/test_indexing_service.py` | Locking, state transitions, rebuild, signature |
| `tests/test_indexing_api.py` | Indexing endpoints and response contracts |
| `tests/test_ollama_embeddings.py` | Batching, validation, retries, model discovery |
| `tests/test_document_generators.py` | PDF/DOCX output and Markdown blocks |
| `tests/test_frontend_api.py` | API shapes used by the frontend |
| `tests/test_ollama_integration.py` | Opt-in live Ollama check |

Fixtures in `tests/fixtures/` contain saved HTML and serialized payload samples.

## Isolation

`tests/conftest.py` gives each test a temporary SQLite database:

1. Creates an engine on a `tmp_path` file.
2. Enables `PRAGMA foreign_keys=ON`.
3. Creates all tables with `Base.metadata.create_all`.
4. Overrides the `get_db` dependency.
5. Removes the override after the test.

No test should read or write the real `storage/chatvault.db`.

The suite also overrides the embedding and chat dependencies with fakes, so tests
are deterministic and offline.

## Fake clients

`tests/fakes.py` provides:

- A fake embedding client that returns deterministic vectors and can simulate
  failures.
- A fake chat client that returns canned answers and model names.

Use these fakes for route and service tests. Do not call a real Ollama instance
from the normal suite.

## Opt-in Ollama test

The live test is skipped unless explicitly enabled:

```bash
RUN_OLLAMA_TESTS=1 .venv/bin/python -m pytest -q tests/test_ollama_integration.py
```

Or:

```bash
make test-ollama
```

It requires:

- Ollama running at `OLLAMA_BASE_URL`.
- `OLLAMA_EMBED_MODEL` installed.
- `OLLAMA_CHAT_MODEL` installed for chat coverage.

This test verifies real embedding and chat payload compatibility. It is not part
of CI.

## Coverage

`pytest-cov` is in the `dev` extra:

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
```

There is no enforced coverage threshold in CI.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes and pull requests to `main`:

| Job | Steps |
| --- | --- |
| Backend tests | Checkout, Python 3.13, `pip install -e ".[dev]"`, `pytest -q` |
| Frontend lint and build | Checkout, Node.js 22, `npm ci`, `npm run lint`, `npm run build` |

Concurrency cancels superseded runs on the same ref. Both jobs have timeouts.

## Documentation checks

The documentation workflow runs `mkdocs build --strict`. Run the same check
locally before changing docs:

```bash
. .docs-venv/bin/activate
mkdocs build --strict
```

Strict mode fails on:

- A page in `nav` that does not exist.
- A broken relative link.
- An unrecognized anchor.
- A malformed configuration.

## Writing tests

Guidelines:

- Add a regression test for every bug fix.
- Prefer API contract tests for status codes and response fields.
- Prefer service tests for state transitions and error handling.
- Use `tmp_path` for storage; never touch the real database.
- Use the fake clients; make live Ollama tests opt-in.
- Assert public error messages that clients depend on.
- Keep tests deterministic. Do not depend on wall-clock time or network access.

Example shape:

```python
def test_import_rejects_http(client):
    response = client.post(
        "/api/v1/import/url",
        json={"url": "http://chatgpt.com/share/abc"},
    )

    assert response.status_code == 400
    assert "HTTPS" in response.json()["detail"]
```

## Related pages

- [Development Setup](development-setup.md)
- [Contributing](contributing.md)
- [CI workflow](https://github.com/heyshreee/chatvault-ai/blob/main/.github/workflows/ci.yml)
