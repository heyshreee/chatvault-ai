# Backup and Restore

ChatVault AI stores durable data in SQLite and derived data in ChromaDB. A good
backup protects the durable part and treats the vector index as disposable.

## What to back up

| Path | Contents | Priority |
| --- | --- | --- |
| `storage/chatvault.db` | Conversations, messages, index state | **Required** |
| `.env` | Backend configuration | Recommended, keep private |
| `frontend/.env` | Frontend API base URL | Optional |
| `storage/chroma/` | Embeddings and vector metadata | Optional; rebuildable |
| `storage/generated/` | PDF and DOCX exports | Optional; regenerate |

`storage/chatvault.db` is the source of truth. Losing `storage/chroma/` costs a
rebuild, not conversations. Losing the SQLite file loses the library.

Do not copy `.env` or `storage/` into a public repository. Both may contain
private data.

## Stop the backend first

The safest backup is taken with the backend stopped:

```bash
# Stop the process running run.py or uvicorn
cp storage/chatvault.db storage/chatvault.db.backup
```

If you must back up while the server is running, use SQLite's online backup
command instead of a plain file copy:

```bash
sqlite3 storage/chatvault.db ".backup 'storage/chatvault-backup.db'"
```

A plain `cp` during a write can produce an inconsistent database or copy an
incomplete write-ahead log. If the database uses WAL mode, copy the `-wal` and
`-shm` files together with the main file, or use `.backup`.

## Back up the whole workspace

With the backend stopped:

```bash
tar -czf chatvault-backup-$(date +%F).tar.gz \
  storage/chatvault.db \
  storage/chroma \
  storage/generated \
  .env \
  frontend/.env
```

This archive contains private conversation data and configuration. Encrypt it or
store it somewhere private.

## Back up only the durable data

If you are willing to rebuild the index and regenerate exports:

```bash
tar -czf chatvault-data-$(date +%F).tar.gz \
  storage/chatvault.db \
  .env
```

After restoring, run a full rebuild. The rebuild re-chunks and re-embeds every
conversation from SQLite. It requires Ollama and the configured embedding model.

## Restore

1. Stop the backend.
2. Move the current data aside so the restore is reversible:

    ```bash
    mv storage/chatvault.db storage/chatvault.db.before-restore
    ```

3. Restore the database:

    ```bash
    cp storage/chatvault.db.backup storage/chatvault.db
    ```

    Or extract an archive:

    ```bash
    tar -xzf chatvault-backup-2026-11-02.tar.gz
    ```

4. Restore `storage/chroma/` if it is part of the backup and matches the
   embedding model in `.env`. Otherwise remove it and rebuild.
5. Start the backend.
6. Open Settings and check:
    - Conversation and message counts.
    - Index status and vector count.
    - Whether a rebuild is required.

If the collection is missing, empty, or from another embedding model, rebuild:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/index/rebuild
```

## Restore without the vector index

This is the normal path for moving to another machine:

```bash
# Stop the backend
rm -rf storage/chroma
# Restore storage/chatvault.db and .env
# Start the backend
curl -X POST http://127.0.0.1:8000/api/v1/index/rebuild
```

The conversations remain available immediately in the Library and for export.
Semantic search and AI Chat work after the rebuild finishes.

## Move to another machine

1. Install the same Python 3.13 stack and Node.js version.
2. Copy `storage/chatvault.db` and `.env`.
3. Keep `DATABASE_URL` and `CHROMA_DB_PATH` valid for the new machine. Relative
   paths resolve from the process working directory.
4. Pull the configured Ollama models.
5. Start the backend and run a rebuild.
6. Update `CORS_ORIGINS` if the frontend origin changed.
7. Update `VITE_API_BASE_URL` and rebuild the frontend if the API address
   changed.

## Verify a restore

```bash
curl http://127.0.0.1:8000/api/v1/stats
curl http://127.0.0.1:8000/api/v1/index/status
curl http://127.0.0.1:8000/api/v1/conversations?limit=5
```

Check that:

- `conversations_total` matches the expected count.
- A sample conversation opens with messages in order.
- `indexed_conversations` plus `not_indexed_conversations` accounts for the
  library.
- `rebuild_required` is `false` after a successful rebuild.

## What cannot be restored from ChromaDB alone

ChromaDB contains chunk text and metadata, but it is not the application
database. Conversation records, message positions, titles, source URLs, and
index state live in SQLite. Restoring only `storage/chroma/` does not restore the
library.

## Retention and cleanup

- `storage/generated/` accumulates PDF and DOCX files. Remove old files with
  `make clean-generated` or delete the directory contents.
- Conversation deletion removes SQLite rows and attempts to remove vectors. If
  ChromaDB was unavailable during deletion, orphaned vectors may remain; they are
  filtered out at retrieval time and disappear on the next rebuild.
- There is no automatic backup scheduler, retention policy, or cloud sync in
  `v1.0.0`.

## Related pages

- [Configuration](../getting-started/configuration.md)
- [Local-First Design](../concepts/local-first-design.md)
- [Privacy and Security](../concepts/privacy-and-security.md)
- [Troubleshooting](troubleshooting.md)
