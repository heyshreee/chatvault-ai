# Data Flow

Every ChatVault AI operation starts in the React frontend or a direct API call
and ends in SQLite, ChromaDB, generated files, or a model response. This page
traces the four main flows.

## Import flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Import page
    participant API as POST /import/url
    participant V as URL validator
    participant F as Fetcher
    participant X as Extractor
    participant DB as SQLite

    U->>UI: Paste share URL
    UI->>UI: Browser-side URL check
    UI->>API: {"url": "https://chatgpt.com/share/..."}
    API->>V: validate_chatgpt_url
    alt Invalid
        V-->>API: InvalidChatGPTURL
        API-->>UI: 400 with validator message
    else Valid
        V-->>API: Normalized URL
        API->>F: fetch_shared_page
        F->>F: HTTPS GET, 20 s timeout, 5 MB cap, max 3 redirects
        alt Fetch failure
            F-->>API: FetchError
            API-->>UI: 502 Unable to fetch...
        else Fetched HTML
            F-->>API: FetchedPage
            API->>X: extract_conversation
            X->>X: Serialized payload or HTML fallback
            X->>X: Keep user/assistant text, clean annotations
            alt No usable messages
                X-->>API: ExtractionError
                API-->>UI: 502 Unable to extract...
            else Conversation
                X-->>API: Conversation
                API->>DB: save_conversation
                alt New
                    DB-->>API: created = true
                else Existing share ID
                    DB-->>API: created = false
                end
                API-->>UI: 200 success or already_exists
            end
        end
    end
```

The frontend then issues a separate indexing request. A failed index does not
roll back the import.

## Indexing flow

```mermaid
flowchart TD
    A["POST /index/{conversation_id}"] --> B{"Conversation exists?"}
    B -->|"no"| C["404 Not found"]
    B -->|"yes"| D{"Indexing lock free?"}
    D -->|"no"| E["409 Another indexing operation is running"]
    D -->|"yes"| F{"State indexed with current signature<br/>and vectors present?"}
    F -->|"yes"| G["200 already_indexed"]
    F -->|"no"| H["Mark state indexing"]
    H --> I["Chunk messages<br/>message-aware"]
    I -->|"no chunks"| J["422 No indexable text"]
    I --> K["Embed chunks in batches<br/>Ollama /api/embed"]
    K -->|"failure"| L["Mark state failed<br/>return 502/503"]
    K --> M["Verify or record collection provenance"]
    M --> N["Delete old vectors for conversation"]
    N --> O["Upsert new vectors and metadata"]
    O -->|"failure"| P["Best-effort cleanup<br/>mark failed"]
    O --> Q["Mark state indexed<br/>record signature, chunks, model, dimension"]
    Q --> R["200 indexed"]
```

Key invariants:

- Old vectors are deleted only after all new embeddings have been generated.
- A failed write triggers a best-effort cleanup of the conversation's vectors.
- The index signature is
  `<embedding_model>|<chunking_version>|<size>|<overlap>|<min>`.
- A conversation is `already_indexed` only if the signature matches **and** the
  live ChromaDB count matches the recorded chunk count.

## Search flow

```mermaid
sequenceDiagram
    participant API as POST /search
    participant R as SemanticRetriever
    participant E as Ollama embeddings
    participant C as ChromaDB
    participant DB as SQLite

    API->>R: query, limit, optional conversation_id
    R->>R: Trim and validate query
    R->>C: check_model_compatibility
    alt Incompatible collection
        C-->>R: VectorStoreConfigurationError
        R-->>API: 409
    else Compatible
        R->>E: Embed query
        E-->>R: Query vector or 503/502
        R->>C: Query max(limit * 4, limit) closest chunks
        C-->>R: IDs, documents, metadata, distances
        R->>DB: Load titles for candidate conversation IDs
        DB-->>R: Titles for conversations that still exist
        R->>R: Drop orphans and non-matching IDs, take limit
        R-->>API: RetrievedChunk list
        API-->>API: Map to SearchResponse
    end
```

## Chat flow

```mermaid
sequenceDiagram
    participant API as POST /chat
    participant CS as ChatService
    participant R as SemanticRetriever
    participant DB as SQLite
    participant C as ChromaDB
    participant E as Ollama embeddings
    participant L as Ollama chat

    API->>CS: message, history, top_k
    CS->>CS: Clamp top_k to 1-10
    CS->>R: search(message, limit)
    R->>E: Embed question
    E-->>R: Vector
    R->>C: Cosine query
    C-->>R: Candidates
    R->>DB: Validate conversation IDs
    DB-->>R: Titles
    R-->>CS: Sources
    alt No sources
        CS-->>API: status no_sources, model null
    else Sources
        CS->>CS: Trim context to CHAT_MAX_CONTEXT_CHARS
        CS->>CS: Take last CHAT_MAX_HISTORY_MESSAGES turns
        CS->>L: POST /api/chat (system + history + context + question)
        L-->>CS: Answer text and model
        CS-->>API: status answered, answer, model, sources
    end
```

The response's `sources` are the exact chunks included in the prompt after
context trimming, not every candidate returned by ChromaDB. Source numbering
starts at 1 in the response.

## Export flow

```mermaid
flowchart LR
    A["GET /conversations/{id}/export/pdf|docx"] --> B{"Conversation exists?"}
    B -->|"no"| C["404 Conversation not found."]
    B -->|"yes"| D["Load messages from SQLite"]
    D --> E["Clean annotation text"]
    E --> F["Parse Markdown blocks"]
    F --> G["Render PDF or DOCX"]
    G --> H["Write storage/generated/{id}.pdf|docx"]
    H --> I["FileResponse download"]
    G -->|"failure"| J["500 Unable to generate PDF/DOCX."]
```

Exports do not call Ollama or ChromaDB. They read SQLite only.

## Deletion flow

```mermaid
flowchart TD
    A["DELETE /conversations/{id}"] --> B{"Conversation exists?"}
    B -->|"no"| C["404"]
    B -->|"yes"| D["Attempt ChromaDB vector deletion"]
    D -->|"VectorStoreError"| E["Log warning<br/>deleted_vectors = null"]
    D -->|"success"| F["deleted_vectors = count"]
    E --> G["Delete SQLite conversation"]
    F --> G
    G -->|"cascade"| H["Delete messages + index state"]
    G -->|"failure"| I["500 Unable to delete conversation."]
    G -->|"success"| J["200 deleted"]
```

SQLite deletion is authoritative. If vector cleanup fails, stale vectors remain
but are not returned by search because retrieval checks conversation IDs against
SQLite.

## Index rebuild flow

1. Acquire the indexing lock.
2. Verify the embedding model is installed.
3. Delete and recreate the ChromaDB collection.
4. Reset every index state to `not_indexed` and clear signatures and chunk counts.
5. Index every conversation with `force=True`.
6. Return a per-conversation result list.

If the library is empty, the rebuild returns `nothing_to_do` after resetting the
collection.

## Related pages

- [Architecture](architecture.md)
- [RAG Explained](rag-explained.md)
- [Vector Search](vector-search.md)
- [Indexing API](../api-reference/indexing.md)
