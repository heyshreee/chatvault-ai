# Conversations

## `GET /api/v1/conversations`

Lists stored conversations, newest first.

### Query parameters

| Parameter | Type | Default | Range | Description |
| --- | --- | --- | --- | --- |
| `skip` | integer | `0` | `>= 0` | Number of records to skip |
| `limit` | integer | `20` | `1`-`100` | Page size |

### Response

| Field | Type | Description |
| --- | --- | --- |
| `total` | integer | Total conversations in SQLite |
| `items` | array | Requested page |

Each item:

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Share ID |
| `title` | string | Conversation title |
| `created_at` | string | ISO 8601 creation timestamp |
| `message_count` | integer | Stored message count |

### Example

```bash
curl -s 'http://127.0.0.1:8000/api/v1/conversations?skip=0&limit=2'
```

```json
{
  "total": 12,
  "items": [
    {
      "conversation_id": "abc123",
      "title": "Shell-GPT setup notes",
      "created_at": "2026-11-02T06:12:41",
      "message_count": 8
    },
    {
      "conversation_id": "def456",
      "title": "Docker compose volumes",
      "created_at": "2026-11-01T19:03:10",
      "message_count": 14
    }
  ]
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | Success, including an empty library |
| `422` | `skip` or `limit` outside the allowed range |

The frontend requests `limit=100` and performs title filtering in the browser.

## `GET /api/v1/conversations/{conversation_id}`

Returns one conversation with its full message list.

### Path parameter

| Parameter | Description |
| --- | --- |
| `conversation_id` | ChatGPT share ID |

### Response

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Share ID |
| `title` | string | Conversation title |
| `source_url` | string | Normalized share URL |
| `created_at` | string | ISO 8601 creation timestamp |
| `message_count` | integer | Number of messages |
| `messages` | array | Messages ordered by `position` |

Each message:

| Field | Type | Description |
| --- | --- | --- |
| `role` | string | `user` or `assistant` |
| `content` | string | Cleaned message text |
| `position` | integer | Zero-based order |

### Example

```bash
curl -s http://127.0.0.1:8000/api/v1/conversations/abc123
```

```json
{
  "conversation_id": "abc123",
  "title": "Shell-GPT setup notes",
  "source_url": "https://chatgpt.com/share/abc123",
  "created_at": "2026-11-02T06:12:41",
  "message_count": 2,
  "messages": [
    {
      "role": "user",
      "content": "How do I install Shell-GPT?",
      "position": 0
    },
    {
      "role": "assistant",
      "content": "Install it with pipx.",
      "position": 1
    }
  ]
}
```

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | Found | Not set |
| `404` | Not found | `Conversation not found.` |

## `DELETE /api/v1/conversations/{conversation_id}`

Deletes a conversation, its messages, and its index state. It first attempts to
delete the conversation's ChromaDB vectors.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `conversation_id` | string | Deleted share ID |
| `status` | string | Always `deleted` |
| `deleted_messages` | integer | Number of cascade-deleted messages |
| `deleted_vectors` | integer or null | Vectors removed, or `null` if ChromaDB cleanup failed |

### Example

```bash
curl -s -X DELETE http://127.0.0.1:8000/api/v1/conversations/abc123
```

```json
{
  "conversation_id": "abc123",
  "status": "deleted",
  "deleted_messages": 8,
  "deleted_vectors": 11
}
```

If ChromaDB is unavailable:

```json
{
  "conversation_id": "abc123",
  "status": "deleted",
  "deleted_messages": 8,
  "deleted_vectors": null
}
```

SQLite deletion still succeeds. Stale vectors are ignored by retrieval because
their conversation no longer exists in SQLite.

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | Deleted | Not set |
| `404` | Not found | `Conversation not found.` |
| `500` | SQLite deletion failed | `Unable to delete conversation.` |

### Notes

- Deletion cannot be undone.
- Exports already written to `storage/generated/` are not deleted.
- Deleting a conversation does not automatically rebuild the index.

## Related pages

- [Library Management](../user-guide/library-management.md)
- [Export](export.md)
- [Indexing](indexing.md)
- [Errors](errors.md)
