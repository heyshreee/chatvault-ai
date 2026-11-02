# Search

## `POST /api/v1/search`

Embeds a query and returns the closest indexed chunks. This is semantic search,
not title search. There is no dedicated frontend screen; call the API directly or
use [AI Chat](../user-guide/ai-chat.md).

### Request body

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `query` | string | Yes | 1-2,000 characters, not blank after trimming | Text to embed |
| `limit` | integer | No | 1-20, default `5` | Maximum results |
| `conversation_id` | string or null | No | Any stored conversation ID | Restrict to one conversation |

### Example

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "reset the Shell-GPT API key",
    "limit": 5
  }'
```

### Response

| Field | Type | Description |
| --- | --- | --- |
| `query` | string | Trimmed query echoed back |
| `total` | integer | Number of results returned |
| `results` | array | Ranked chunks |

Each result:

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Source conversation |
| `conversation_title` | string | Current title from SQLite |
| `role` | string | `user`, `assistant`, or `unknown` |
| `message_position` | integer | Zero-based message position |
| `chunk_index` | integer | Zero-based chunk index within the message |
| `text` | string | Cleaned chunk text |
| `distance` | number | Raw cosine distance; lower is closer |

### Example response

```json
{
  "query": "reset the Shell-GPT API key",
  "total": 2,
  "results": [
    {
      "conversation_id": "abc123",
      "conversation_title": "Shell-GPT setup notes",
      "role": "user",
      "message_position": 4,
      "chunk_index": 0,
      "text": "How do I reset the Shell-GPT API key?",
      "distance": 0.1823
    },
    {
      "conversation_id": "def456",
      "conversation_title": "API key rotation",
      "role": "assistant",
      "message_position": 7,
      "chunk_index": 1,
      "text": "Remove the saved key and run sgpt --api-key again.",
      "distance": 0.2417
    }
  ]
}
```

### Behavior

1. The query is trimmed and validated.
2. ChromaDB checks collection model compatibility.
3. The query is embedded with `OLLAMA_EMBED_MODEL`.
4. ChromaDB queries `max(limit * 4, limit)` candidates with cosine distance.
5. Candidate conversation IDs are validated against SQLite.
6. Orphaned vectors and records with missing text are dropped.
7. Up to `limit` results are returned.

The 4× over-fetch preserves the caller's result budget when stale vectors exist.

### Filtering by conversation

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Docker compose volume",
    "limit": 3,
    "conversation_id": "abc123"
  }'
```

The filter is applied inside ChromaDB. A non-existent `conversation_id` returns
HTTP `200` with `"total": 0`, not `404`.

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | Search completed; `total` may be `0` | Not set |
| `422` | Blank query, out-of-range limit, or invalid body | Validation message or array |
| `409` | Collection model, dimension, or distance is incompatible | Rebuild message |
| `502` | Ollama returned invalid embeddings | `Ollama returned an invalid embedding response.` |
| `503` | Ollama or ChromaDB unavailable, or embedding model missing | Public message |
| `500` | ChromaDB query failed | `ChromaDB operation failed.` |

An empty collection returns `200` with `"total": 0`.

### Notes

- `distance` is not a percentage and is not normalized.
- No similarity threshold is applied.
- No keyword, BM25, hybrid, or reranking stage exists.
- Results are limited by `limit` only; there is no pagination.
- The response uses the current SQLite title and cleans text again before
  returning it.

## Related pages

- [Search and Retrieval](../user-guide/search-and-retrieval.md)
- [Vector Search](../concepts/vector-search.md)
- [Chat](chat.md)
- [Errors](errors.md)
