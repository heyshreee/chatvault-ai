# Local-First Design

ChatVault AI is local-first in a specific, testable sense: the durable data lives
on your machine, the vector index is derived and disposable, and the default
model runtime is a local Ollama service. It is not a cloud application with an
offline mode.

## The two storage rules

1. **SQLite is the source of truth.** Conversations, messages, titles, source
   URLs, and index state live in `storage/chatvault.db`.
2. **ChromaDB is a derived index.** Every vector can be regenerated from SQLite
   with the configured embedding model.

This split determines how to recover from failures:

| Loss | Recovery |
| --- | --- |
| ChromaDB directory deleted or corrupt | Rebuild the index |
| Embedding model changed | Rebuild the index |
| Chunking configuration changed | Reindex; rebuild for a full refresh |
| SQLite database lost | Restore from backup; cannot be rebuilt |
| Generated PDF/DOCX lost | Export again |
| Ollama unavailable | Start it; conversations and exports still work |

## Where data lives

| Path | Data | Leaves the machine? |
| --- | --- | --- |
| `storage/chatvault.db` | Conversations and messages | No |
| `storage/chroma/` | Embeddings and chunk metadata | No |
| `storage/generated/` | PDF and DOCX exports | No |
| `.env` | Configuration | No |
| Browser memory | AI Chat history for the current page | No |

Back up the SQLite file. The other paths are replaceable. See
[Backup and Restore](../guides/backup-and-restore.md).

## Network boundaries

The backend makes outbound requests in only two situations:

1. **Import.** It fetches a public `https://chatgpt.com/share/<id>` page. The
   request reveals the share URL and a ChatVault user agent to ChatGPT, but no
   local conversation content.
2. **Ollama.** It sends chunk text for embeddings and prompts for chat. By
   default this goes to `http://localhost:11434`, which stays on the machine.

The React frontend talks only to the backend API. It does not call ChatGPT,
Ollama, analytics services, or a CDN at runtime. The production build is static
assets served from your own host.

There is no hosted account, sync service, telemetry endpoint, or model API key.

### If Ollama is remote

Setting `OLLAMA_BASE_URL` to another machine changes the privacy property.
Chunk text and prompts leave your computer and are processed by that host. Use a
remote Ollama only when you control the network and the host.

## Derived data is disposable

The index can always be rebuilt because it contains no unique source data. This
is why ChatVault can:

- Delete and recreate the collection during a rebuild.
- Ignore orphaned vectors at query time.
- Delete SQLite data even when ChromaDB is down.
- Change chunking settings and mark old indexes stale.

The trade-off is rebuild time: a large library must be re-chunked and re-embedded,
which is synchronous and can take minutes.

## Local trust model

ChatVault AI is a single-user local tool:

- No login, accounts, roles, or tenant isolation.
- The backend trusts any client that can reach it.
- CORS limits browser origins but is not authentication.
- The default bind address is `127.0.0.1`.

This is appropriate for a personal workstation. It is not appropriate to expose
the backend directly to a network. See
[Privacy and Security](privacy-and-security.md) for the threat model.

## What local-first does not mean

- **Not encrypted at rest.** SQLite, ChromaDB, and exports rely on filesystem
  permissions. Use full-disk encryption if the device may be lost.
- **Not sandboxed.** The backend can read and write its configured paths and can
  fetch `chatgpt.com`.
- **Not offline-only.** Import needs network access to ChatGPT.
- **Not multi-device.** There is no sync; copy the database manually.
- **Not a backup system.** You must back up `storage/chatvault.db` yourself.
- **Not immune to model behavior.** A local model can still produce incorrect or
  unsafe text.

## Design consequences

The local-first choice explains several product decisions:

- Import is limited to public share pages rather than account integration.
- Chat is non-streaming and synchronous; there is no job service.
- The index is rebuilt rather than migrated when the embedding model changes.
- Settings is a status page, not a remote configuration service.
- The API has no authentication because the intended deployment is loopback.

## Related pages

- [Architecture](architecture.md)
- [Privacy and Security](privacy-and-security.md)
- [Backup and Restore](../guides/backup-and-restore.md)
- [Configuration](../getting-started/configuration.md)
