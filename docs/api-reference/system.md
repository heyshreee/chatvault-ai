# System

Operational status endpoints for the dashboard, Settings page, and monitoring.

## `GET /api/v1/models/status`

Returns Ollama connectivity, model availability, ChromaDB state, SQLite counts,
and index summary.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `ollama` | object | Connection state |
| `chat_model` | object | Configured chat model availability |
| `embedding_model` | object | Configured embedding model availability |
| `installed_models` | array | Models reported by Ollama |
| `vector_store` | object | ChromaDB state |
| `database` | object | SQLite counts |
| `index` | object | Index counts and rebuild state |

`ollama`:

| Field | Type | Description |
| --- | --- | --- |
| `base_url` | string | Configured URL without a trailing slash |
| `available` | boolean | Whether `/api/tags` succeeded |
| `error` | string or null | Public error when unavailable |

`chat_model` and `embedding_model`:

| Field | Type | Description |
| --- | --- | --- |
| `name` | string | Configured model |
| `available` | boolean | Whether an installed model matches |

Each installed model:

| Field | Type | Description |
| --- | --- | --- |
| `name` | string | Model name with tag |
| `size` | integer or null | Size reported by Ollama |
| `modified_at` | string or null | Modification timestamp reported by Ollama |

`vector_store`:

| Field | Type | Description |
| --- | --- | --- |
| `collection` | string | Collection name |
| `available` | boolean | Whether the collection could be read |
| `vectors` | integer or null | Live vector count |
| `embedding_dimension` | integer or null | Recorded dimension |
| `error` | string or null | Public error when unavailable |

`database`:

| Field | Type | Description |
| --- | --- | --- |
| `engine` | string | `sqlite` |
| `conversations` | integer | Total conversations |
| `messages` | integer | Total messages |

`index`:

| Field | Type | Description |
| --- | --- | --- |
| `total` | integer | Total conversations |
| `indexed` | integer | Indexed with current signature |
| `not_indexed` | integer | Never indexed or no state |
| `indexing` | integer | In progress |
| `failed` | integer | Last attempt failed |
| `stale` | integer | Indexed with an older signature |
| `chunks_recorded` | integer | Sum of chunk counts for indexed conversations |
| `rebuild_required` | boolean | Whether a rebuild is needed |
| `rebuild_reason` | string or null | Reason |

### Example

```bash
curl -s http://127.0.0.1:8000/api/v1/models/status
```

```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "available": true,
    "error": null
  },
  "chat_model": {
    "name": "llama3.2:3b",
    "available": true
  },
  "embedding_model": {
    "name": "nomic-embed-text",
    "available": true
  },
  "installed_models": [
    {
      "name": "llama3.2:3b",
      "size": 2019393189,
      "modified_at": "2026-10-28T11:04:19.512Z"
    },
    {
      "name": "nomic-embed-text:latest",
      "size": 274302450,
      "modified_at": "2026-10-28T10:58:02.104Z"
    }
  ],
  "vector_store": {
    "collection": "chatvault_conversations",
    "available": true,
    "vectors": 143,
    "embedding_dimension": 768,
    "error": null
  },
  "database": {
    "engine": "sqlite",
    "conversations": 12,
    "messages": 86
  },
  "index": {
    "total": 12,
    "indexed": 10,
    "not_indexed": 1,
    "indexing": 0,
    "failed": 1,
    "stale": 0,
    "chunks_recorded": 143,
    "rebuild_required": false,
    "rebuild_reason": null
  }
}
```

### Behavior when Ollama is down

The endpoint still returns HTTP `200`:

```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "available": false,
    "error": "Ollama is unavailable. Start Ollama and try again."
  },
  "chat_model": {
    "name": "llama3.2:3b",
    "available": false
  },
  "embedding_model": {
    "name": "nomic-embed-text",
    "available": false
  },
  "installed_models": []
}
```

Check the booleans, not the HTTP status. ChromaDB and SQLite information is still
reported when Ollama is down.

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Status computed, including unavailable Ollama or ChromaDB |
| `500` | Unexpected failure outside handled dependency errors |

## `GET /api/v1/stats`

Returns dashboard counts, index coverage, vector-store health, and the five most
recent imports.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `conversations_total` | integer | Conversations in SQLite |
| `messages_total` | integer | Messages in SQLite |
| `indexed_conversations` | integer | Indexed with current signature |
| `not_indexed_conversations` | integer | Never indexed or no state |
| `indexing_conversations` | integer | In progress |
| `failed_conversations` | integer | Last attempt failed |
| `stale_conversations` | integer | Indexed with an older signature |
| `chunks_indexed` | integer | Recorded chunks for indexed conversations |
| `vectors` | integer or null | Live ChromaDB count |
| `vector_store_available` | boolean | Whether ChromaDB could be read |
| `vector_store_error` | string or null | Public error when unavailable |
| `recent_imports` | array | Five newest conversations |

Each recent import:

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Share ID |
| `title` | string | Title |
| `created_at` | string | ISO 8601 timestamp |
| `message_count` | integer | Message count |

### Example

```bash
curl -s http://127.0.0.1:8000/api/v1/stats
```

```json
{
  "conversations_total": 12,
  "messages_total": 86,
  "indexed_conversations": 10,
  "not_indexed_conversations": 1,
  "indexing_conversations": 0,
  "failed_conversations": 1,
  "stale_conversations": 0,
  "chunks_indexed": 143,
  "vectors": 143,
  "vector_store_available": true,
  "vector_store_error": null,
  "recent_imports": [
    {
      "conversation_id": "abc123",
      "title": "Shell-GPT setup notes",
      "created_at": "2026-11-02T06:12:41",
      "message_count": 8
    }
  ]
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Stats computed, including vector-store errors |
| `500` | Unexpected database failure |

## Related pages

- [Dashboard](../user-guide/dashboard.md)
- [Settings](../user-guide/settings.md)
- [Indexing](indexing.md)
- [Troubleshooting](../guides/troubleshooting.md)
