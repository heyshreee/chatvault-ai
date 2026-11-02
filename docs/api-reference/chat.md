# Chat

## `POST /api/v1/chat`

Answers a question from indexed conversations using retrieval-augmented
generation. The request is non-streaming.

### Request body

| Field | Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| `message` | string | Yes | 1-4,000 characters, not blank after trimming | Question |
| `history` | array | No | Max 20 items | Prior user/assistant turns |
| `top_k` | integer | No | 1-10, default `5` | Number of chunks to retrieve |

Each history item:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `role` | string | Yes | `user` or `assistant` |
| `content` | string | Yes | 1-8,000 characters |

The service uses only the last `CHAT_MAX_HISTORY_MESSAGES` turns (default 10) and
truncates each content field to 8,000 characters.

### Example

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "message": "How do I install Shell-GPT?",
    "history": [
      {"role": "user", "content": "I am using Kali Linux."},
      {"role": "assistant", "content": "Understood."}
    ],
    "top_k": 5
  }'
```

### Response

| Field | Type | Description |
| --- | --- | --- |
| `status` | `answered` or `no_sources` | Outcome |
| `answer` | string | Markdown answer, or the fixed no-source message |
| `model` | string or null | Model reported by Ollama; `null` when no sources |
| `sources` | array | Passages included in the prompt |

Each source:

| Field | Type | Description |
| --- | --- | --- |
| `index` | integer | Citation number, starting at 1 |
| `conversation_id` | string | Source conversation |
| `conversation_title` | string | Current title from SQLite |
| `role` | string | Speaker role |
| `message_position` | integer | Zero-based message position |
| `chunk_index` | integer | Zero-based chunk index |
| `text` | string | Cleaned chunk text |
| `distance` | number | Raw cosine distance |

### Example answered response

```json
{
  "status": "answered",
  "answer": "Install it with pipx, then run `sgpt --install-integration` [1].",
  "model": "llama3.2:3b",
  "sources": [
    {
      "index": 1,
      "conversation_id": "abc123",
      "conversation_title": "Shell-GPT setup notes",
      "role": "assistant",
      "message_position": 3,
      "chunk_index": 0,
      "text": "Install it with pipx:\n\npipx install shell-gpt",
      "distance": 0.1412
    }
  ]
}
```

### Example no-source response

```json
{
  "status": "no_sources",
  "answer": "No indexed conversations matched this question. Import a conversation, make sure it is indexed, and try again.",
  "model": null,
  "sources": []
}
```

When `status` is `no_sources`, the chat model is not called.

### Behavior

1. Clamps `top_k` to 1-10.
2. Retrieves sources across the **entire** indexed library. There is no
   conversation filter on this endpoint.
3. Returns `no_sources` if retrieval is empty.
4. Trims sources to `CHAT_MAX_CONTEXT_CHARS`.
5. Adds the last history turns.
6. Sends a system prompt, history, numbered context, and question to Ollama.
7. Returns the answer and the trimmed sources.

The response `sources` are the passages actually supplied to the model, not every
candidate from ChromaDB.

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | Answered or no sources | Not set |
| `422` | Invalid message, history, content length, role, or `top_k` | Validation array |
| `409` | Collection model, dimension, or distance is incompatible | Rebuild message |
| `502` | Ollama returned an invalid chat response | `Ollama returned an invalid chat response.` |
| `502` | Ollama rejected the chat request with a non-model error | `Ollama rejected the request (HTTP n).` |
| `502` | Ollama returned invalid embeddings | `Ollama returned an invalid embedding response.` |
| `503` | Chat model missing or Ollama chat unavailable | Public Ollama message |
| `503` | Embedding model missing, Ollama embedding unavailable, or ChromaDB unavailable | Public message |
| `500` | ChromaDB query failed | `ChromaDB operation failed.` |

### Notes

- Answers are not streamed. The client waits for the full response.
- Chat history is not persisted. Send it on every request.
- Citation markers in `answer` are model-generated and are not verified by the
  backend. Use `sources` as the authoritative reference list.
- The model can still be influenced by instructions inside imported
  conversations. See [RAG Explained](../concepts/rag-explained.md).
- The request timeout in the frontend is 300 seconds; the backend Ollama chat
  timeout defaults to 180 seconds.

## Related pages

- [AI Chat](../user-guide/ai-chat.md)
- [RAG Explained](../concepts/rag-explained.md)
- [Search](search.md)
- [Errors](errors.md)
