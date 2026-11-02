# Importing Conversations

ChatVault AI imports **public ChatGPT share pages**. It does not log in to
ChatGPT, accept private conversation URLs, or import ChatGPT data-export ZIP
files.

## Accepted URL format

```text
https://chatgpt.com/share/<share-id>
```

`<share-id>` may contain letters, digits, underscores, and hyphens. The trailing
slash is optional.

| URL | Result |
| --- | --- |
| `https://chatgpt.com/share/abc123` | Accepted |
| `https://chatgpt.com/share/abc123/` | Accepted and normalized |
| `http://chatgpt.com/share/abc123` | Rejected: HTTPS only |
| `https://chat.openai.com/share/abc123` | Rejected: host must be `chatgpt.com` |
| `https://chatgpt.com/c/abc123` | Rejected: path must be `/share/<id>` |
| `https://chatgpt.com/share/abc123?x=1` | Normalized to the canonical share URL |
| `https://user:pass@chatgpt.com/share/abc123` | Rejected: credentials not allowed |
| `https://chatgpt.com:8443/share/abc123` | Rejected: custom port |

The same validation runs in the browser form and again in the backend.

## Import workflow

```mermaid
flowchart TD
    A["Paste public share URL"] --> B{"Browser URL check"}
    B -->|"invalid"| C["Show inline validation message"]
    B -->|"valid"| D["POST /api/v1/import/url"]
    D --> E{"Backend validation"}
    E -->|"invalid"| F["HTTP 400"]
    E -->|"valid"| G["Fetch public page<br/>20 s timeout, 5 MB limit, max 3 redirects"]
    G -->|"failure"| H["HTTP 502"]
    G --> I["Extract user and assistant text"]
    I -->|"failure"| H
    I --> J["Save conversation and messages in SQLite"]
    J -->|"failure"| K["HTTP 500"]
    J --> L["Return status success or already_exists"]
    L --> M["Frontend calls POST /api/v1/index/{id}"]
    M -->|"success"| N["Show chunk count and model"]
    M -->|"failure"| O["Conversation saved; show Retry index"]
```

The import request is synchronous. The API returns after the page has been
fetched, parsed, and written to SQLite. Indexing is a separate synchronous
request made by the frontend.

## What is extracted

The extractor supports two formats:

1. **Serialized ChatGPT payload.** It looks for a script containing
   `.enqueue(...)`, decodes the embedded JSON, follows the conversation mapping
   and linear conversation order, and keeps only `user` and `assistant` messages
   whose content type is `text`.
2. **Legacy HTML fallback.** It reads elements with
   `data-message-author-role="user"` or `data-message-author-role="assistant"`.

In both paths, ChatGPT private-use annotations are removed. System messages,
tool output, thoughts, reasoning recaps, and non-text content are not stored.

The conversation ID is derived from the `/share/<id>` path. The title comes from
the serialized payload when available, otherwise from the HTML `<title>`.

## Duplicate behavior

A conversation is identified by its share ID. If it already exists:

- The API returns HTTP `200`.
- `status` is `"already_exists"`.
- The existing title, messages, and timestamps are returned.
- Nothing is overwritten or refreshed.

To replace a stored transcript, delete the conversation and import it again.

## Limits and failure behavior

| Limit | Value |
| --- | --- |
| Request timeout | 20 seconds |
| Maximum response size | 5 MB |
| Maximum redirects | 3 |
| Accepted content types | `text/html`, `application/xhtml+xml` |
| Allowed host | `chatgpt.com` |
| Allowed scheme | HTTPS |
| Allowed ports | default or 443 |

Redirects are followed manually and revalidated. A redirect to a non-ChatGPT
host is blocked. HTTP errors, non-HTML responses, timeouts, and oversized pages
return HTTP `502` with a message prefixed by `Unable to fetch shared
conversation:`.

If extraction fails, the response is HTTP `502` with `Unable to extract
conversation:`. If SQLite persistence fails, the response is HTTP `500`.

If indexing fails after a successful import, the conversation remains in
SQLite. The Import page shows a warning and a **Retry index** action. See
[Troubleshooting](../guides/troubleshooting.md).

## Import from the API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/import/url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://chatgpt.com/share/<share-id>"}'
```

Example success response, truncated:

```json
{
  "status": "success",
  "conversation_id": "abc123",
  "title": "Example conversation",
  "message_count": 12,
  "messages": [
    {
      "role": "user",
      "content": "How do I install Shell-GPT?",
      "position": 0
    }
  ]
}
```

The response includes the full stored message list. See
[Import API](../api-reference/import.md) for the complete contract.

## What is not supported

- Private or unshared conversations.
- `chat.openai.com` URLs.
- ChatGPT account login or cookie-based import.
- ChatGPT export ZIP upload.
- Bulk URL import.
- Updating an already imported conversation.
- Importing attachments, images, or non-text content.

## Related pages

- [Importing ChatGPT URLs](../guides/importing-chatgpt-urls.md)
- [Library Management](library-management.md)
- [Import API](../api-reference/import.md)
