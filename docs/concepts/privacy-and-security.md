# Privacy and Security

ChatVault AI is a local, single-user application with no hosted service. Its
security model is built around that deployment: keep the backend on loopback,
treat imported conversations as untrusted content, and protect the storage
directory with operating-system controls.

This page describes what the code actually enforces and what it does not.

## Data at rest

| Data | Location | Protection |
| --- | --- | --- |
| Conversations and messages | `storage/chatvault.db` | Filesystem permissions; no application-level encryption |
| Embeddings and chunk metadata | `storage/chroma/` | Filesystem permissions; derived from conversation text |
| PDF and DOCX exports | `storage/generated/` | Filesystem permissions |
| Configuration | `.env` | Filesystem permissions; ignored by Git |
| Chat history | Browser memory | Cleared on reload; not stored by the backend |

There is no encryption at rest, per-user key, or secure enclave. Use full-disk
encryption and a protected user account if the device is shared or portable.

## Network egress

| Destination | When | What is sent |
| --- | --- | --- |
| `chatgpt.com` | Import | The public share URL and a ChatVault user agent |
| `OLLAMA_BASE_URL` | Indexing, search, chat, status | Chunk text, queries, prompts, or `/api/tags` requests |
| Browser to backend | Every UI action | API requests and responses |

The default Ollama URL is `http://localhost:11434`. If you change it to a remote
host, conversation text leaves your machine.

The application has no analytics, crash reporting, telemetry endpoint, or hosted
model provider. ChromaDB telemetry is disabled by default through
`CHROMA_TELEMETRY=false`.

## Import security

The importer is the main network-facing attack surface. It enforces:

- HTTPS only.
- Host exactly `chatgpt.com`.
- Path `/share/<id>` with a restricted ID character set.
- No URL credentials.
- No custom port.
- At most three redirects, each revalidated.
- A 20-second timeout.
- A 5 MB response cap.
- HTML content types only.
- No automatic redirect following.

These controls prevent the importer from being used as a general SSRF proxy. They
do not make ChatGPT content trustworthy.

## Rendering safety

- Conversation text is rendered as Markdown in the React app.
- Raw HTML is not enabled in the Markdown renderer, so imported HTML is not
  executed as markup.
- Code blocks are highlighted and escaped by the renderer.
- API errors return public messages rather than tracebacks.

Treat generated answers with the same caution as any model output. A local model
can repeat or transform malicious text from a conversation.

## Prompt injection

Imported conversations are data, but a language model can confuse data with
instructions. ChatVault's system prompt states that context and history are data
and must not be followed as instructions. The prompt also requires the model to
answer only from supplied passages and to cite them.

This reduces risk but does not eliminate it. A retrieved message can still
influence the answer. Do not place secrets, credentials, or sensitive personal
data in conversations you import, and review answers before acting on them.

## Logging

The application avoids logging conversation text:

- Indexing failures log the exception type, not the message or traceback.
- Conversation deletion logs the exception type when vector cleanup fails.
- API errors return fixed public messages for internal failures.

Operational caveats:

- Uvicorn access logs record request paths, status codes, and timings. Import
  requests use `POST /api/v1/import/url`, so the share URL is in the request body,
  not the path. Conversation IDs appear in paths for detail, export, index, and
  delete requests.
- Setting `SQL_ECHO=true` makes SQLAlchemy log SQL statements and may include
  bound parameters such as message content. Keep it `false` when logs are
  collected or shared.
- Reverse proxies, process supervisors, and browser developer tools may log
  request bodies independently of ChatVault.

## Authentication and access control

There is no authentication. Anyone who can reach the API can read, import,
delete, index, and export conversations.

Recommended posture:

- Keep the default bind address `127.0.0.1`.
- Do not expose the backend to an untrusted network.
- If remote access is required, put it behind a trusted reverse proxy with
  authentication and TLS, and restrict `CORS_ORIGINS`.
- Do not reuse the development server as a public service.

`CORS_ORIGINS` controls which browser origins may call the API. It does not stop
non-browser clients such as `curl`.

## Debug mode

`DEBUG=True` is the default for local development and is passed to FastAPI. Do not
run a debug backend on an untrusted network. Set `DEBUG=False` for any shared
deployment.

## File path safety

Exports build paths from the conversation ID after validating it against:

```text
[A-Za-z0-9_-]{1,100}
```

Only `.pdf` and `.docx` are accepted by the output path builder. This blocks path
traversal through IDs. Share IDs are restricted to the same character class at
import time.

## Deletion and residual data

Deleting a conversation:

1. Attempts to delete its vectors from ChromaDB.
2. Deletes the SQLite conversation and cascades messages and index state.

If ChromaDB is unavailable, vectors may remain on disk. They are filtered from
retrieval because their conversation no longer exists in SQLite, but they are not
physically removed until a rebuild or manual deletion of `storage/chroma/`.

Generated PDF/DOCX files are not deleted automatically when a conversation is
deleted. Remove `storage/generated/` contents if the exports are sensitive.

## Dependency and supply-chain risk

ChatVault AI depends on FastAPI, SQLAlchemy, ChromaDB, Ollama, ReportLab,
python-docx, React, and the npm ecosystem. It does not vendor a model. Review
dependency updates and run the test suite before upgrading.

The backend installs from `requirements.txt`; the frontend uses
`frontend/package-lock.json` with `npm ci` in CI. Python package versions are
mostly lower-bounded, except ChromaDB, which is pinned to `1.5.9`.

## Reporting a vulnerability

Do not open a public issue for a security problem. Use GitHub Security
Advisories:

<https://github.com/makitdev/chatvault-ai/security/advisories/new>

Include the affected version, impact, reproduction steps, and any preconditions.
Do not include private conversation content or secrets in the first message.
See the repository's [SECURITY.md](https://github.com/makitdev/chatvault-ai/blob/main/SECURITY.md)
for the full policy.

## Hardening checklist

- [ ] Backend bound to `127.0.0.1`.
- [ ] `CORS_ORIGINS` limited to the frontend origins you use.
- [ ] `DEBUG=False` for shared use.
- [ ] `SQL_ECHO=false` when logs are retained.
- [ ] `.env` and `storage/` excluded from Git and backups are encrypted.
- [ ] Full-disk encryption enabled on portable devices.
- [ ] Ollama kept local unless remote processing is intentional.
- [ ] Backups tested by restoring into a separate directory.
- [ ] Answers reviewed before acting on them.

## Note about this documentation site

The documentation site is a static MkDocs Material site separate from the
application. It may load web fonts from Google Fonts and does not contain your
conversation data. The application itself does not load those fonts.

## Related pages

- [Local-First Design](local-first-design.md)
- [Architecture](architecture.md)
- [Troubleshooting](../guides/troubleshooting.md)
- [Backup and Restore](../guides/backup-and-restore.md)
