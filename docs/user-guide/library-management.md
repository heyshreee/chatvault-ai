# Library Management

The Library at `/library` lists conversations stored in SQLite and provides
title filtering, sorting, deletion, and links to the transcript viewer.

## What the Library loads

The frontend requests:

```text
GET /api/v1/conversations?limit=100&skip=0
```

It loads the **100 most recent conversations** in one request. The backend
maximum is 100 per page.

The header reports the total conversation count. If the database contains more
than 100 conversations, the Library shows a badge and a note that filters apply
only to the loaded set. There is no pagination control in the current UI.

## Search, filters, and sorting

All Library controls operate on the loaded list in the browser. They do not call
a search endpoint.

| Control | Behavior |
| --- | --- |
| Search by title | Case-insensitive substring match on the conversation title |
| All | No date or message-count filter |
| Last 7 days | Keeps conversations created within the last seven days |
| 10+ messages | Keeps conversations with at least ten messages |
| Newest first | Descending creation time |
| Oldest first | Ascending creation time |
| Title A-Z | Locale-aware title comparison |
| Most messages | Descending message count |

**Clear filters** resets the title query and the date/message filter. Sorting is
kept.

The Library does **not** perform semantic search. For embedding-based retrieval,
use [AI Chat](ai-chat.md) or call [`POST /api/v1/search`](../api-reference/search.md)
directly.

## Open a conversation

Selecting a row opens `/conversations/<conversation_id>`. The viewer shows:

- Title, message count, creation time, and source URL hostname.
- The full stored transcript with the original message order.
- Markdown rendering and code highlighting.
- A copy button per message.
- **Export PDF** and **Export DOCX** actions.
- Links to **Ask AI** and the source share page.

The viewer reads `GET /api/v1/conversations/{conversation_id}`. If the
conversation no longer exists, the API returns HTTP `404`.

## Delete a conversation

The trash action opens a confirmation dialog. Confirming calls:

```text
DELETE /api/v1/conversations/{conversation_id}
```

Deletion:

1. Attempts to delete the conversation's vectors from ChromaDB.
2. Deletes the SQLite conversation. Messages and index state are removed by
   cascade.
3. Returns counts for deleted messages and vectors.

SQLite is the source of truth. If ChromaDB is unavailable, vector cleanup is
skipped, SQLite deletion still succeeds, and `deleted_vectors` is `null`.
Orphaned vectors are ignored by retrieval because results are validated against
SQLite conversation IDs.

The operation cannot be undone. Back up `storage/chatvault.db` before bulk
cleanup. See [Backup and Restore](../guides/backup-and-restore.md).

## Empty and filtered states

- **Empty library:** no conversations exist. The page links to Import.
- **No filter matches:** conversations exist, but none match the current title
  or filter. The page offers **Clear filters**.
- **Delete error:** the confirmation dialog stays open and displays the API
  error message.

## API equivalents

```bash
# List the 20 newest conversations
curl 'http://127.0.0.1:8000/api/v1/conversations?skip=0&limit=20'

# Read one conversation
curl http://127.0.0.1:8000/api/v1/conversations/<conversation-id>

# Delete a conversation and its vectors
curl -X DELETE http://127.0.0.1:8000/api/v1/conversations/<conversation-id>
```

## Current limitations

- No pagination controls beyond the first 100 conversations.
- No folder, tag, or collection organization.
- No bulk selection or bulk delete.
- No transcript editing.
- No semantic search inside the Library.
- No sorting or filtering on the server.

## Related pages

- [Conversation viewer and export](export.md)
- [Conversations API](../api-reference/conversations.md)
- [Search and Retrieval](search-and-retrieval.md)
