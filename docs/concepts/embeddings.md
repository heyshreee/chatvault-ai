# Embeddings

An embedding is a numeric vector that represents the meaning of a piece of text.
Texts with similar meaning have vectors that are close together under a distance
metric. ChatVault AI uses embeddings to find conversation chunks related to a
question.

## Default model

| Setting | Default |
| --- | --- |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` |
| `OLLAMA_EMBED_TIMEOUT` | `120` seconds |
| `OLLAMA_EMBED_BATCH_SIZE` | `16` texts per request |
| Endpoint | `POST {OLLAMA_BASE_URL}/api/embed` |

The model runs in Ollama. ChatVault does not bundle a model runtime or call a
hosted embedding API.

The vector dimension is determined by the model and returned by Ollama. ChatVault
records the dimension in ChromaDB metadata instead of hard-coding a value. Use
`GET /api/v1/index/status` to see the recorded `embedding_dimension`.

## What gets embedded

For indexing, each chunk is embedded with a short context header:

```text
Conversation: <conversation title>
Speaker: <user or assistant>

<chunk text>
```

The header helps the embedding model distinguish speakers and topics. The stored
ChromaDB document is the chunk text **without** the header. Search returns the
stored document.

For search, the query is embedded as-is after trimming. Chat and search do not
add the conversation header to the query.

## Batching

Texts are split into batches of `OLLAMA_EMBED_BATCH_SIZE`:

```text
texts[0:16], texts[16:32], ...
```

Each batch is an independent HTTP request. A failure in any batch fails the whole
indexing operation. Batches are sequential, not parallel.

Larger batches reduce HTTP overhead but increase memory use and the amount of work
lost on a timeout. The allowed range is 1-128.

## Validation

The embedding client rejects malformed responses rather than writing partial or
invalid vectors:

- The response must be JSON with an `embeddings` array.
- The number of vectors must match the number of inputs.
- Every vector must be a list of numeric, finite values.
- Every vector in a response must have the same dimension.
- Empty vectors are rejected.

A validation failure becomes `EmbeddingResponseError`, which the API maps to HTTP
`502` with `Ollama returned an invalid embedding response.`

## Retries and timeouts

The embedding client retries transient failures up to two times (three attempts
total) with a short linear backoff. It retries:

- Connection errors and timeouts.
- HTTP `429`, `500`, `502`, `503`, and `504`.

It does not retry a `404` or a model-not-found error. Those are returned as
`OllamaModelNotFoundError` and mapped to HTTP `503`.

The timeout applies to the whole HTTP request for one batch. The connect timeout
is capped at 5 seconds.

## Model provenance

ChromaDB collection metadata records:

- `embedding_model`
- `embedding_dimension`
- `distance_metric: cosine`

Before indexing or querying, ChatVault checks that the configured model matches
the collection. Before writing, it checks that the vector dimension matches.

If the collection has vectors with no recorded model, or a different model, the
API returns HTTP `409` with a message such as:

```text
The embedding model has changed. Rebuild the index.
```

A dimension mismatch produces:

```text
The embedding dimension does not match the collection. Rebuild the index.
```

## Changing the embedding model

1. Pull the new model in Ollama.
2. Set `OLLAMA_EMBED_MODEL` in `.env`.
3. Restart the backend.
4. Rebuild the index:

    ```bash
    curl -X POST http://127.0.0.1:8000/api/v1/index/rebuild
    ```

The rebuild deletes and recreates the collection, then re-embeds every
conversation. Old and new vectors are never mixed.

Changing chunking settings also requires a rebuild for consistent results, even
though the model is unchanged.

## Storage and privacy

Embeddings are stored locally in `storage/chroma/`. They are derived from
conversation text and may encode sensitive information. Treat the ChromaDB
directory with the same care as the SQLite database.

Embedding requests go to `OLLAMA_BASE_URL`. If that points to a remote machine,
chunk text leaves your computer. The local-first property depends on Ollama
running on the same machine.

## What embeddings are not

- They are not human-readable or reversible by the application.
- They are not a keyword index. Exact string matching is not guaranteed.
- They are not a quality score. Distance reflects the model's geometry, not truth.
- They are not portable across embedding models without a rebuild.

## Related pages

- [Vector Search](vector-search.md)
- [RAG Explained](rag-explained.md)
- [Model Configuration](../guides/model-configuration.md)
- [Ollama Setup](../guides/ollama-setup.md)
