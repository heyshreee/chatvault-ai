# Settings

Settings at `/settings` is an **operational status page**, not a configuration
editor. It reads the current environment, Ollama state, ChromaDB state, and
SQLite counts. The only mutation is a full vector index rebuild.

## Panels

### Ollama connection

Shows:

- Configured `OLLAMA_BASE_URL`.
- Whether the `/api/tags` request succeeded.
- Number of installed models.
- Time of the last status read.

If Ollama is unavailable, the panel displays a public error message and suggests
starting the service with `ollama serve`.

### Configured models

Shows the chat and embedding model names selected by the backend environment and
whether each is installed.

Model matching treats an unversioned name as matching its latest tag. For
example, configured `llama3.2:3b` matches installed `llama3.2:3b`; a configured
name without a tag also matches an installed `name:tag`.

If a model is missing, pull it:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### ChromaDB vector store

Shows the collection name, live vector count, embedding dimension, and
availability. If the store cannot be read, the error is shown.

Deleting `storage/chroma/` or rebuilding the index does not delete
conversations. SQLite remains the source of truth.

### SQLite database

Shows the engine (`sqlite`), conversation count, message count, and indexed chunk
count. The panel notes that message text is stored locally and that application
logs do not include conversation snippets.

### Indexing

Shows:

- Coverage percentage (`indexed / total`).
- Indexed, not indexed, failed, and stale counts.
- Chunk size, overlap, minimum, chunking version, token-counting method, and
  embedding dimension.
- Rebuild-required state and reason.
- The last rebuild result, if one was run in this session.

Chunking values are read from `GET /api/v1/index/status`. The summary above them
comes from `GET /api/v1/models/status`.

### Installed Ollama models

Lists every model reported by Ollama with size, modification date, and badges
showing whether it is the configured chat model or embedding model.

## Rebuild the index

**Rebuild index** opens a confirmation dialog. Confirming calls:

```text
POST /api/v1/index/rebuild
```

The operation:

1. Verifies the embedding model is available.
2. Deletes and recreates the ChromaDB collection.
3. Resets every conversation's index state to `not_indexed`.
4. Re-chunks and re-embeds every conversation.
5. Returns a summary with indexed, skipped, and failed counts.

SQLite conversations and messages are not modified. The request is synchronous
and can take minutes on a large library. The UI stays in a loading state until it
finishes.

Use a rebuild when:

- The embedding model changed.
- The embedding dimension changed.
- The collection has unknown provenance.
- The collection is empty but conversations are marked indexed.
- The chunking configuration changed and you want a full refresh.

Individual stale conversations can also be reindexed with
`POST /api/v1/index/{conversation_id}`; the UI does not expose a per-conversation
reindex action outside the Import retry flow.

## Refresh status

**Refresh status** refetches both `GET /api/v1/models/status` and
`GET /api/v1/index/status`. TanStack Query also marks the data stale after 15
seconds and refetches when the query is used again. The page does not poll on a
timer.

## What Settings cannot change

- Environment variables or `.env` values.
- Ollama base URL.
- Model names.
- Chunk sizes or chunking version.
- Database or ChromaDB paths.
- CORS origins.
- API port or host.
- Chat history or context limits.

Change these in the root `.env`, then restart the backend. See
[Configuration](../getting-started/configuration.md).

## Error handling

| Condition | UI behavior |
| --- | --- |
| `GET /models/status` fails | Full error panel with retry |
| `GET /index/status` fails | Warning notice; model summary still renders |
| Ollama unavailable | `models/status` still returns 200 with `ollama.available: false` |
| Rebuild fails | Error notice with the API message |
| Rebuild has failures | Success-style notice with warning variant and failed count |

## Related pages

- [Configuration](../getting-started/configuration.md)
- [Model Configuration](../guides/model-configuration.md)
- [Indexing API](../api-reference/indexing.md)
- [System API](../api-reference/system.md)
