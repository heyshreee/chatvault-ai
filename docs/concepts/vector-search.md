# Vector Search

ChatVault AI stores embeddings in a persistent ChromaDB collection and queries it
with cosine distance. The vector store is a derived index: it can be deleted and
rebuilt from SQLite at any time.

## Collection configuration

| Property | Value |
| --- | --- |
| Client | `chromadb.PersistentClient` |
| Path | `CHROMA_DB_PATH`, default `storage/chroma` |
| Collection | `CHROMA_COLLECTION_NAME`, default `chatvault_conversations` |
| Distance metric | `cosine` |
| Embedding function | `None`; embeddings are always supplied explicitly |
| Telemetry | `CHROMA_TELEMETRY`, default `false` |

The adapter uses a process-wide singleton (`get_chroma_store()`) so the collection
handle is reused across requests.

## Record shape

Each vector record has:

| Field | Value |
| --- | --- |
| ID | `<conversation_id>:<message_position>:<chunk_index>` |
| Document | Cleaned chunk text |
| Embedding | Vector from the configured embedding model |
| Metadata | Conversation ID, database ID, message ID, message position, role, chunk index, title, chunking version, embedding model |

The metadata is what allows retrieval to cite a source and to filter by
conversation.

## Query behavior

`SemanticRetriever.search()`:

1. Trims the query and rejects blank text.
2. Checks collection model compatibility.
3. Embeds the query.
4. Queries ChromaDB with `n_results = max(limit * 4, limit)`.
5. Optionally applies `where={"conversation_id": ...}`.
6. Validates every candidate against SQLite conversation IDs.
7. Drops missing metadata and orphaned records.
8. Returns at most `limit` results.

ChromaDB also caps `n_results` at the collection count, so a query against a small
collection is safe.

### Why over-fetch

Deleting a conversation normally removes its vectors. If ChromaDB was unavailable
during deletion, stale vectors can remain. Over-fetching by 4× gives the retriever
enough candidates to fill the caller's limit after orphans are removed.

### Orphan filtering

A vector is usable only if its `conversation_id` still exists in SQLite. The
retriever loads titles for the candidate IDs in one query and skips any ID with no
title. This also ensures the returned title reflects the current SQLite record.

## Distance

ChromaDB returns a cosine **distance**, where lower means closer. ChatVault does
not convert it to a similarity percentage and does not apply a threshold.

Two consequences:

- A result may be weakly related but still returned.
- Distance values are not comparable across embedding models.

If you need a cutoff, apply it in your own client. The API preserves the raw
distance so you can inspect it.

## Index signature and staleness

SQLite stores an index state per conversation. The signature is:

```text
<OLLAMA_EMBED_MODEL>|<CHUNKING_VERSION>|<CHUNK_SIZE_TOKENS>|<CHUNK_OVERLAP_TOKENS>|<CHUNK_MIN_TOKENS>
```

A conversation is **stale** when its status is `indexed` but its stored signature
differs from the current configuration. Stale conversations are still counted
separately and can be reindexed. The index status endpoint reports the count.

`already_indexed` is returned only when:

- `force` is false,
- the status is `indexed`,
- the signature matches, and
- the live ChromaDB vector count for that conversation equals the recorded chunk
  count.

This guards against a ChromaDB directory that was deleted independently of
SQLite.

## Rebuild semantics

`POST /api/v1/index/rebuild`:

1. Acquires the indexing lock.
2. Verifies the embedding model is available.
3. Deletes and recreates the collection.
4. Resets every index state.
5. Reindexes every conversation with `force=True`.

The collection is recreated with cosine distance and fresh provenance. A rebuild
does not touch conversations or messages.

## Deletion

`DELETE /api/v1/index/{conversation_id}` removes that conversation's vectors and
sets its state to `not_indexed`. It does not delete the conversation.

Deleting a conversation removes its vectors first, then the SQLite record. If
vector deletion fails, the SQLite delete still proceeds and the response reports
`deleted_vectors: null`.

## Scale characteristics

- ChromaDB uses its default HNSW index with cosine distance.
- Query cost grows with collection size, but the application does not implement
  sharding, replication, or multi-process coordination.
- Upserts are batched at 100 records per ChromaDB call.
- The backend is intended for a single local process.

No benchmark numbers are claimed here; performance depends on the machine, model,
collection size, and ChromaDB version.

## What vector search does not provide

- Keyword or BM25 matching.
- Hybrid scoring.
- Reranking.
- Minimum-similarity filtering.
- Multi-vector or late-interaction retrieval.
- Server-side pagination of results. The endpoint returns the top `limit` only.

## Related pages

- [Embeddings](embeddings.md)
- [Search and Retrieval](../user-guide/search-and-retrieval.md)
- [Indexing API](../api-reference/indexing.md)
- [Search API](../api-reference/search.md)
