# Dashboard

The Dashboard is the landing page at `/`. It summarizes the local workspace and
the health of the derived vector index.

![ChatVault AI demo](https://heyshreee.github.io/chatvault-ai/assets/demo.gif)

## Metrics

| Card | Meaning | Source |
| --- | --- | --- |
| Conversations | Total stored conversations | `GET /api/v1/stats` |
| Messages | Total stored messages | `GET /api/v1/stats` |
| Indexed conversations | Conversations with a current index signature and stored vectors | `GET /api/v1/stats` |
| Indexed chunks | Sum of chunk counts recorded for indexed conversations | `GET /api/v1/stats` |

The index coverage bar is calculated in the browser as:

```text
indexed_conversations / conversations_total * 100
```

It is a coverage indicator, not a quality score.

## Recent imports

The **Recent imports** panel lists the five most recently stored conversations,
ordered by creation time. Each row shows the title, message count, and creation
date. Selecting a row opens the conversation viewer.

If the library is empty, the panel links to **Import**.

## Index health

The **Index health** panel reads `GET /api/v1/index/status` and reports:

- **Healthy**: the vector store is available and no rebuild is required.
- **Rebuild required**: the stored embedding model, dimension, or vector count no
  longer matches the current configuration or SQLite state.
- **Unavailable**: ChromaDB could not be read.

It also shows the configured collection, embedding model, live vector count,
recorded chunks, and an index coverage bar. Use **Index settings** to open the
full Settings page.

A rebuild is required when:

- The collection has vectors but no recorded embedding model.
- The configured embedding model differs from the stored model.
- The collection has no recorded embedding dimension.
- The collection is empty while conversations are marked as indexed or stale.

## Index activity notice

When conversations are currently indexing or have failed, the Dashboard shows a
notice. Failed conversations can be retried individually from the Import page or
reindexed with the full rebuild action in Settings. Rebuilds are synchronous; see
[Settings](settings.md).

## Empty state

On a fresh database the Dashboard shows onboarding steps:

1. Import a shared link.
2. Build the index.
3. Ask with citations.

The statistics cards still render with zero values. The Dashboard does not
create sample data.

## API equivalents

```bash
curl http://127.0.0.1:8000/api/v1/stats
curl http://127.0.0.1:8000/api/v1/index/status
```

`GET /api/v1/stats` returns total conversations and messages, index counts,
chunk and vector counts, vector-store availability, and the five most recent
imports. `GET /api/v1/index/status` returns the detailed chunking and collection
information.

## Related pages

- [Importing Conversations](importing-conversations.md)
- [Library Management](library-management.md)
- [Indexing API](../api-reference/indexing.md)
