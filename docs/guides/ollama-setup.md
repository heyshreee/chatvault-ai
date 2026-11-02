# Ollama Setup

Ollama provides both local embeddings and local chat generation. ChatVault AI
does not bundle Ollama and does not call a hosted model provider.

## 1. Install Ollama

Install Ollama from the official site for your platform:
<https://ollama.com/download>.

After installation, confirm the CLI is available:

```bash
ollama --version
```

## 2. Start the service

If Ollama is not already running as a background service:

```bash
ollama serve
```

By default it listens on `http://localhost:11434`. ChatVault's default
`OLLAMA_BASE_URL` matches that address.

Verify the API:

```bash
curl http://localhost:11434/api/tags
```

The response is JSON with a `models` array.

## 3. Pull the default models

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Check what is installed:

```bash
ollama list
```

Both names must appear for the default configuration to work.

| Purpose | Default model | Config variable |
| --- | --- | --- |
| Embeddings | `nomic-embed-text` | `OLLAMA_EMBED_MODEL` |
| Chat | `llama3.2:3b` | `OLLAMA_CHAT_MODEL` |

## 4. Point ChatVault at Ollama

Root `.env`:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2:3b
```

Restart the backend after editing `.env`. Open **Settings** and confirm:

- Ollama connection: **Connected**.
- Chat generation: **Available**.
- Embeddings: **Available**.

The API equivalent:

```bash
curl http://127.0.0.1:8000/api/v1/models/status
```

## 5. Test embeddings and chat directly

Embedding request:

```bash
curl -X POST http://localhost:11434/api/embed \
  -H 'Content-Type: application/json' \
  -d '{"model":"nomic-embed-text","input":["hello world"]}'
```

Chat request:

```bash
curl -X POST http://localhost:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role":"user","content":"Say hello."}],
    "stream": false
  }'
```

If these fail, ChatVault will also fail. Fix the Ollama service before debugging
the application.

## Timeouts and batching

| Setting | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_EMBED_TIMEOUT` | `120` seconds | Per-request embedding timeout |
| `OLLAMA_CHAT_TIMEOUT` | `180` seconds | Chat generation timeout |
| `OLLAMA_EMBED_BATCH_SIZE` | `16` | Number of texts per embedding request |
| `OLLAMA_CHAT_TEMPERATURE` | `0.2` | Chat sampling temperature |

Large local models or slow hardware may need a higher timeout. The embedding
client retries transient connection errors and HTTP `429`/`5xx` responses twice
with a short linear backoff.

## Remote or non-default Ollama

To use Ollama on another machine or port, set `OLLAMA_BASE_URL`:

```dotenv
OLLAMA_BASE_URL=http://192.168.1.50:11434
```

Considerations:

- The Ollama service must accept connections on that interface. Follow Ollama's
  own `OLLAMA_HOST` documentation.
- ChatVault's Ollama HTTP clients use `trust_env=False`, so proxy environment
  variables are ignored for these requests.
- Conversation chunks are sent to that Ollama instance. If it is not under your
  control, the local-first privacy property no longer holds.
- Network latency and timeouts matter for indexing and chat.

## Common Ollama errors

| Message | Cause | Fix |
| --- | --- | --- |
| `Ollama is unavailable. Start Ollama and try again.` | Connection refused or timeout | Start Ollama; check `OLLAMA_BASE_URL` |
| `Embedding model 'nomic-embed-text' is not available.` | Model not pulled | `ollama pull nomic-embed-text` |
| `Chat model 'llama3.2:3b' is not available.` | Model not pulled | `ollama pull llama3.2:3b` |
| `Ollama returned an invalid embedding response.` | Unexpected payload | Check Ollama version and model |
| `Ollama returned an invalid chat response.` | Missing message content | Check Ollama logs and model |

See [Troubleshooting](troubleshooting.md) for application-level errors.

## Related pages

- [Model Configuration](model-configuration.md)
- [Requirements](../getting-started/requirements.md)
- [Embeddings](../concepts/embeddings.md)
