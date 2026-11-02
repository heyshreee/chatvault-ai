# Search and Retrieval

ChatVault AI has two different search experiences:

| Experience | Where | What it searches |
| --- | --- | --- |
| Library title search | Library page | Conversation titles in the loaded list, in the browser |
| Semantic search | `POST /api/v1/search` | Embedded chunks in ChromaDB, validated against SQLite |

There is **no dedicated semantic search screen** in the current frontend. Use
AI Chat for an answer, or call the search endpoint directly for ranked chunks.

## Semantic search API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "reset the Shell-GPT API key",
    "limit": 5
  }'
```

Request fields:

| Field | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| `query` | string | Yes | 1-2000 characters after trimming, not blank | Text to embed and search |
| `limit` | integer | No | 1-20, default 5 | Maximum results after filtering |
| `conversation_id` | string or null | No | Existing conversation ID | Restrict retrieval to one conversation |

Example response:

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

## How retrieval works

1. The query is trimmed and validated.
2. The embedding model is checked against the collection provenance.
3. The query is embedded with `OLLAMA_EMBED_MODEL`.
4. ChromaDB is queried with cosine distance.
5. The backend requests `max(limit * 4, limit)` candidates.
6. Candidate conversation IDs are validated against SQLite.
7. Orphaned vectors whose SQLite conversation was deleted are discarded.
8. Results are returned up to `limit`.

Step 5 is deliberate: if ChromaDB contains stale vectors, over-fetching prevents
them from consuming the caller's result budget.

## Distance, not similarity

`distance` is the raw cosine distance returned by ChromaDB. **Lower is closer.**
It is not converted to a percentage and no similarity threshold is applied. A
result can be returned even when it is only weakly related.

There is no hybrid keyword search, BM25, reranker, or score normalization. The
ranking is the collection's cosine ranking after orphan filtering.

## Restrict to one conversation

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "Docker compose volume",
    "limit": 3,
    "conversation_id": "abc123"
  }'
```

The `where` filter is applied inside ChromaDB. Results are still validated
against SQLite.

## Requirements and errors

Semantic search requires:

- Ollama running and reachable.
- `OLLAMA_EMBED_MODEL` installed.
- A compatible ChromaDB collection.
- At least one indexed conversation for non-empty results.

| Status | Meaning |
| --- | --- |
| `200` | Search completed; `total` may be zero |
| `422` | Blank query, value out of range, or invalid request |
| `503` | Ollama or ChromaDB unavailable, or the embedding model is missing |
| `502` | Ollama returned an invalid embedding response |
| `409` | Collection provenance or distance configuration is incompatible |
| `500` | ChromaDB query failed |

An empty collection returns `200` with `"total": 0`, not an error.

## Library title search

The Library search box filters the loaded set of up to 100 conversations by
title. It does not query the backend and does not use embeddings. See
[Library Management](library-management.md).

## Practical tips

- Use natural-language phrases that resemble the stored text.
- Restrict to one conversation when you know where the answer lives.
- If results are poor, verify the conversation is indexed and the index is not
  stale.
- If the embedding model changed, rebuild the index before searching.
- Inspect `distance` values to judge how close the matches are, but do not treat
  them as calibrated confidence.

## Related pages

- [AI Chat](ai-chat.md)
- [Vector Search](../concepts/vector-search.md)
- [Search API](../api-reference/search.md)
