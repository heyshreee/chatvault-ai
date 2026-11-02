# Indexing

Indexing turns stored messages into embeddings and writes them to ChromaDB. All
indexing operations are synchronous and protected by a process-wide lock.

## Index state

Each conversation has one state:

| State | Meaning |
| --- | --- |
| `not_indexed` | No current vectors |
| `indexing` | An operation is in progress |
| `indexed` | Vectors exist and the signature matches |
| `failed` | The last attempt failed; `last_error` is stored |

A conversation is **stale** when it is `indexed` but its stored signature differs
from the current configuration. Stale conversations are reported separately and
are not counted as `indexed`.

The signature is:

```text
<OLLAMA_EMBED_MODEL>|<CHUNKING_VERSION>|<CHUNK_SIZE_TOKENS>|<CHUNK_OVERLAP_TOKENS>|<CHUNK_MIN_TOKENS>
```

## `POST /api/v1/index/{conversation_id}`

Indexes one conversation.

### Path parameter

| Parameter | Description |
| --- | --- |
| `conversation_id` | Stored ChatGPT share ID |

### Query parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `force` | boolean | `false` | Reindex even when the signature matches |

### Behavior

1. Acquires the indexing lock or returns `409`.
2. Loads the conversation or returns `404`.
3. Checks collection model compatibility.
4. If not forced, the state is `indexed`, the signature matches, and the live
   vector count equals the recorded chunk count, returns `already_indexed`.
5. Marks the state `indexing`.
6. Chunks and embeds the conversation.
7. Verifies or records collection provenance.
8. Deletes old vectors, then upserts the new ones.
9. Marks the state `indexed` and records the signature, chunk count, model,
   dimension, and timestamp.

Old vectors are deleted only after all new embeddings are generated. A failed
upsert triggers a best-effort delete of that conversation's vectors.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Share ID |
| `status` | `indexed` or `already_indexed` | Result |
| `chunks` | integer | Chunk count |
| `embedding_model` | string | Current embedding model |
| `chunking_version` | string | Current chunking version |
| `indexed_at` | string or null | UTC timestamp of the last successful index |

### Example

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/index/abc123'
```

```json
{
  "conversation_id": "abc123",
  "status": "indexed",
  "chunks": 11,
  "embedding_model": "nomic-embed-text",
  "chunking_version": "message-aware-v1",
  "indexed_at": "2026-11-02T07:31:08.412931+00:00"
}
```

Repeat without `force`:

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/index/abc123'
```

```json
{
  "conversation_id": "abc123",
  "status": "already_indexed",
  "chunks": 11,
  "embedding_model": "nomic-embed-text",
  "chunking_version": "message-aware-v1",
  "indexed_at": "2026-11-02T07:31:08.412931+00:00"
}
```

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | Indexed or already indexed | Not set |
| `404` | Conversation not found | `Conversation not found.` |
| `409` | Another indexing operation is running | `Another indexing operation is already running.` |
| `409` | Conversation state is already `indexing` | `This conversation is already being indexed.` |
| `409` | Collection model, dimension, or distance is incompatible | Rebuild message |
| `422` | No usable text after cleaning | `Conversation has no indexable text.` |
| `502` | Ollama returned invalid embeddings | `Ollama returned an invalid embedding response.` |
| `503` | Ollama unavailable or embedding model missing | Public Ollama message |
| `503` | ChromaDB unavailable | `ChromaDB is unavailable.` |
| `500` | ChromaDB write/read failure | `ChromaDB operation failed.` |
| `500` | Other indexing failure | `Indexing failed.` |

## `POST /api/v1/index/all`

Indexes multiple conversations.

### Query parameters

| Parameter | Type | Default | Range | Description |
| --- | --- | --- | --- | --- |
| `force` | boolean | `false` | | Reindex conversations that already match |
| `limit` | integer or null | `null` | `1`-`1000` | Index only the first N conversations |
| `fail_fast` | boolean | `false` | | Stop after the first per-conversation failure |

Conversations are selected in insertion order (oldest first).

### Behavior

- If the library is empty, returns `nothing_to_do` without contacting Ollama.
- Otherwise verifies the embedding model and collection compatibility before
  starting.
- Per-conversation failures are captured in `results` and do not abort the run
  unless `fail_fast` is true.
- A failure in the initial model or collection check returns an error status
  instead of a result list.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `status` | `completed`, `partial`, `failed`, or `nothing_to_do` | Aggregate result |
| `total` | integer | Number of conversations selected |
| `indexed` | integer | Newly indexed count |
| `skipped` | integer | `already_indexed` count |
| `failed` | integer | Failed count |
| `results` | array | Per-conversation results |

Result item:

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Share ID |
| `status` | `indexed`, `already_indexed`, or `failed` | Outcome |
| `chunks` | integer | Chunk count, `0` on failure |
| `error` | string or null | Public error message on failure |

Aggregate status:

| Value | Condition |
| --- | --- |
| `completed` | At least one indexed or skipped, no failures |
| `partial` | Some successes and some failures |
| `failed` | Failures and no successes |
| `nothing_to_do` | No conversations selected, or nothing indexed/skipped |

### Example

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/index/all?limit=25&force=false'
```

```json
{
  "status": "completed",
  "total": 2,
  "indexed": 1,
  "skipped": 1,
  "failed": 0,
  "results": [
    {
      "conversation_id": "abc123",
      "status": "already_indexed",
      "chunks": 11,
      "error": null
    },
    {
      "conversation_id": "def456",
      "status": "indexed",
      "chunks": 7,
      "error": null
    }
  ]
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Run completed, including partial or failed per-item results |
| `409` | Indexing busy or collection incompatible |
| `503` | Ollama or ChromaDB unavailable, or model missing |
| `502` | Invalid embedding response |
| `500` | Unexpected indexing or ChromaDB failure |

## `POST /api/v1/index/rebuild`

Deletes and recreates the ChromaDB collection, resets every index state, and
indexes every conversation with `force=True`.

### Query parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `fail_fast` | boolean | `false` | Stop after the first per-conversation failure |

### Behavior

1. Acquires the indexing lock.
2. Verifies the embedding model is available.
3. Deletes and recreates the collection.
4. Resets all index states to `not_indexed` and clears signatures and counts.
5. Indexes every conversation.

If the library is empty, the collection is still reset, then the response is
`nothing_to_do`.

With `fail_fast=true`, `total` still reports the number of selected
conversations, but `results` stops at the failed item.

### Response

The same fields as `/index/all`, plus:

| Field | Type | Description |
| --- | --- | --- |
| `collection` | string | Current ChromaDB collection name |

### Example

```bash
curl -s -X POST 'http://127.0.0.1:8000/api/v1/index/rebuild'
```

```json
{
  "status": "completed",
  "total": 2,
  "indexed": 2,
  "skipped": 0,
  "failed": 0,
  "results": [
    {
      "conversation_id": "abc123",
      "status": "indexed",
      "chunks": 11,
      "error": null
    },
    {
      "conversation_id": "def456",
      "status": "indexed",
      "chunks": 7,
      "error": null
    }
  ],
  "collection": "chatvault_conversations"
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Rebuild completed, including partial results |
| `409` | Indexing busy or collection incompatible |
| `503` | Ollama or ChromaDB unavailable, or model missing |
| `502` | Invalid embedding response |
| `500` | Unexpected indexing or ChromaDB failure |

A rebuild can take minutes on a large library. The request does not stream
progress.

## `GET /api/v1/index/status`

Returns configuration, counts, collection health, and rebuild state.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `collection` | string | Collection name |
| `embedding_model` | string | Configured embedding model |
| `embedding_dimension` | integer or null | Dimension recorded in collection metadata |
| `chunking_version` | string | Configured version |
| `chunk_size_tokens` | integer | Configured size |
| `chunk_overlap_tokens` | integer | Configured overlap |
| `chunk_min_tokens` | integer | Configured minimum |
| `token_counting` | string | `approximate_char4` |
| `conversations` | object | Counts by state |
| `chunks_recorded` | integer | Sum of chunk counts for indexed conversations |
| `vectors` | integer or null | Live ChromaDB vector count |
| `vector_store_available` | boolean | Whether the collection could be read |
| `vector_store_error` | string or null | Public error when unavailable |
| `rebuild_required` | boolean | Whether a rebuild is needed |
| `rebuild_reason` | string or null | Human-readable reason |

`conversations`:

| Field | Description |
| --- | --- |
| `total` | Total conversations |
| `indexed` | Indexed with the current signature |
| `not_indexed` | Never indexed, plus conversations with no state row |
| `indexing` | Currently indexing |
| `failed` | Last attempt failed |
| `stale` | Indexed with an older signature |

### Example

```bash
curl -s http://127.0.0.1:8000/api/v1/index/status
```

```json
{
  "collection": "chatvault_conversations",
  "embedding_model": "nomic-embed-text",
  "embedding_dimension": 768,
  "chunking_version": "message-aware-v1",
  "chunk_size_tokens": 500,
  "chunk_overlap_tokens": 75,
  "chunk_min_tokens": 30,
  "token_counting": "approximate_char4",
  "conversations": {
    "total": 12,
    "indexed": 10,
    "not_indexed": 1,
    "indexing": 0,
    "failed": 1,
    "stale": 0
  },
  "chunks_recorded": 143,
  "vectors": 143,
  "vector_store_available": true,
  "vector_store_error": null,
  "rebuild_required": false,
  "rebuild_reason": null
}
```

### Rebuild conditions

`rebuild_required` is `true` when the collection is readable and any of these is
true:

- The collection has vectors but no `embedding_model` metadata.
- The stored model differs from `OLLAMA_EMBED_MODEL`.
- The collection has no `embedding_dimension`.
- The collection is empty while conversations are marked indexed or stale.

`vector_store_available: false` means the collection could not be read; inspect
`vector_store_error`. The endpoint still returns HTTP `200` in that case.

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Status computed, including vector-store errors |
| `500` | Unexpected failure outside the handled vector-store error path |

## `DELETE /api/v1/index/{conversation_id}`

Deletes one conversation's vectors and resets its index state. The conversation
and messages remain.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Share ID |
| `status` | string | Always `not_indexed` |
| `deleted_chunks` | integer | Vectors removed |

### Example

```bash
curl -s -X DELETE http://127.0.0.1:8000/api/v1/index/abc123
```

```json
{
  "conversation_id": "abc123",
  "status": "not_indexed",
  "deleted_chunks": 11
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Deleted or nothing to delete |
| `404` | Conversation not found |
| `409` | Indexing operation busy |
| `503` | ChromaDB unavailable |
| `500` | ChromaDB deletion failed |

## Concurrency

All indexing operations share one non-blocking process lock. If a lock is held,
the API returns:

```json
{
  "detail": "Another indexing operation is already running."
}
```

with HTTP `409`. This is a local single-process lock, not a distributed lock.

## Related pages

- [Document Processing](../guides/document-processing.md)
- [Vector Search](../concepts/vector-search.md)
- [Model Configuration](../guides/model-configuration.md)
- [Settings](../user-guide/settings.md)
