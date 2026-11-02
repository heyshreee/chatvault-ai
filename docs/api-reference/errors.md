# Errors

## Error envelope

Application errors return a JSON object with a `detail` string:

```json
{
  "detail": "Conversation not found."
}
```

FastAPI request validation returns `detail` as an array:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "url"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

The array shape and message text come from FastAPI and Pydantic and may change
between dependency versions. Branch on the HTTP status, not on `msg`.

## Status codes by meaning

| Code | Meaning | Typical causes |
| --- | --- | --- |
| `200` | Success | Includes `already_exists`, `no_sources`, and empty search |
| `400` | Application-level import validation | Non-HTTPS, wrong host, bad path, credentials, custom port |
| `404` | Missing conversation | Detail, delete, export, or index request for an unknown ID |
| `409` | Conflict | Indexing lock held, conversation already indexing, incompatible collection |
| `422` | Validation or no content | Schema failure, out-of-range values, no indexable text |
| `500` | Internal failure | SQLite failure, ChromaDB failure, PDF/DOCX generation, unexpected indexing |
| `502` | Upstream failure | ChatGPT fetch/extraction, invalid Ollama payload |
| `503` | Dependency unavailable | Ollama down, model missing, ChromaDB unavailable |

## Operation matrix

| Operation | `400` | `404` | `409` | `422` | `500` | `502` | `503` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `GET /health` | | | | | | | |
| `POST /import/url` | ✓ | | | ✓ | ✓ | ✓ | |
| `GET /conversations` | | | | ✓ | | | |
| `GET /conversations/{id}` | | ✓ | | | | | |
| `DELETE /conversations/{id}` | | ✓ | | | ✓ | | |
| `GET .../export/pdf` | | ✓ | | | ✓ | | |
| `GET .../export/docx` | | ✓ | | | ✓ | | |
| `POST /index/{id}` | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /index/all` | | | ✓ | | ✓ | ✓ | ✓ |
| `POST /index/rebuild` | | | ✓ | | ✓ | ✓ | ✓ |
| `GET /index/status` | | | | | ✓ | | |
| `DELETE /index/{id}` | | ✓ | ✓ | | ✓ | | ✓ |
| `POST /search` | | | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /chat` | | | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /stats` | | | | | ✓ | | |
| `GET /models/status` | | | | | ✓ | | |

`✓` means the operation can return that code in normal operation. Unexpected
server failures can produce `500` anywhere.

## Common messages

### Import

| Message | Status | Cause |
| --- | --- | --- |
| `URL cannot be empty.` | `400` | Empty URL |
| `Only HTTPS URLs are allowed.` | `400` | `http://` URL |
| `Only chatgpt.com URLs are allowed.` | `400` | Other host |
| `URL credentials are not allowed.` | `400` | Username or password in URL |
| `Custom ports are not allowed.` | `400` | Non-default port |
| `Invalid ChatGPT shared conversation URL.` | `400` | Path not `/share/<id>` |
| `Unable to fetch shared conversation: ...` | `502` | Timeout, HTTP error, redirect, size, or content type |
| `Unable to extract conversation: ...` | `502` | No supported messages |
| `Unable to save conversation to database.` | `500` | SQLite write failed |

### Conversations and export

| Message | Status | Cause |
| --- | --- | --- |
| `Conversation not found.` | `404` | Unknown ID |
| `Unable to delete conversation.` | `500` | SQLite deletion failed |
| `Unable to generate PDF.` | `500` | PDF rendering failed, often missing fonts |
| `Unable to generate DOCX.` | `500` | DOCX rendering failed |

### Indexing

| Message | Status | Cause |
| --- | --- | --- |
| `Conversation not found.` | `404` | Unknown ID |
| `Another indexing operation is already running.` | `409` | Process lock held |
| `This conversation is already being indexed.` | `409` | State is `indexing` |
| `The embedding model has changed. Rebuild the index.` | `409` | Collection provenance mismatch |
| `The ChromaDB collection has unknown embedding provenance. Rebuild the index.` | `409` | Missing model metadata |
| `The embedding dimension does not match the collection. Rebuild the index.` | `409` | Dimension mismatch |
| `The existing ChromaDB collection does not use cosine distance. Rebuild the index.` | `409` | Wrong metric |
| `Conversation has no indexable text.` | `422` | Chunking produced nothing |
| `Ollama embedding service is unavailable.` | `503` | Connection failure during indexing |
| `Embedding model '<name>' is not available. Run: ollama pull <name>` | `503` | Missing model |
| `ChromaDB is unavailable.` | `503` | Collection could not be initialized |
| `Ollama returned an invalid embedding response.` | `502` | Malformed vectors |
| `ChromaDB operation failed.` | `500` | Read/write/query failure |
| `Indexing failed.` | `500` | Unexpected indexing error |

### Search and chat

| Message | Status | Cause |
| --- | --- | --- |
| `Query cannot be blank.` | `422` | Whitespace-only query |
| `Message cannot be blank.` | `422` | Whitespace-only message |
| `Ollama is unavailable. Start Ollama and try again.` | `503` | Embedding or chat connection failure |
| `Chat model '<name>' is not available. Run: ollama pull <name>` | `503` | Missing chat model |
| `Ollama returned an invalid chat response.` | `502` | Missing or empty assistant content |
| `Ollama rejected the request (HTTP n).` | `502` | Other Ollama chat error |
| `ChromaDB operation failed.` | `500` | Query failure |

### System

`GET /models/status` reports dependency problems in the body rather than as HTTP
errors:

| Field | Example |
| --- | --- |
| `ollama.error` | `Ollama is unavailable. Start Ollama and try again.` |
| `vector_store.error` | `ChromaDB is unavailable.` |

## Retry guidance

| Status | Retry? | Notes |
| --- | --- | --- |
| `400` | No | Fix the URL |
| `404` | No | The conversation does not exist |
| `409` busy | Yes, after the current operation | Indexing is synchronous |
| `409` incompatible | Only after a rebuild | Rebuild first |
| `422` | No | Fix the request or import different content |
| `500` | Maybe | Check disk, ChromaDB, and logs |
| `502` from ChatGPT | Maybe | The share page may be private or changed |
| `502` from Ollama | Maybe | Check the model and Ollama version |
| `503` | Yes, after starting Ollama or fixing the model | |

## Security of error messages

Application routes convert internal exceptions into fixed public messages for
unexpected failures. They avoid returning tracebacks or conversation text.

Operational logs are a separate concern:

- `SQL_ECHO=true` can log SQL parameters, potentially including message text.
- Uvicorn access logs include paths and status codes.
- Reverse proxies may log more.

See [Privacy and Security](../concepts/privacy-and-security.md).

## Related pages

- [API Overview](overview.md)
- [Troubleshooting](../guides/troubleshooting.md)
- [Indexing](indexing.md)
- [Chat](chat.md)
