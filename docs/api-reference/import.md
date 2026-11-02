# Import

## `POST /api/v1/import/url`

Imports a public ChatGPT share conversation. The route validates the URL, fetches
the page, extracts user and assistant text, and stores the conversation in
SQLite. It does not index the conversation; call
[`POST /api/v1/index/{conversation_id}`](indexing.md) after a successful import.

### Request body

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `url` | string (URL) | Yes | Public `https://chatgpt.com/share/<id>` URL |

Pydantic validates the field as an HTTP URL. The application validator then
enforces the host, scheme, path, credentials, and port rules.

### Example request

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/import/url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://chatgpt.com/share/abc123"}'
```

### Response

| Field | Type | Description |
| --- | --- | --- |
| `status` | `success` or `already_exists` | Whether a new row was created |
| `conversation_id` | string | Share ID |
| `title` | string | Extracted conversation title |
| `message_count` | integer | Number of stored messages |
| `messages` | array | Stored messages, in order |

Each message:

| Field | Type | Description |
| --- | --- | --- |
| `role` | string | `user` or `assistant` |
| `content` | string | Cleaned message text |
| `position` | integer | Zero-based order |

### Example response

```json
{
  "status": "success",
  "conversation_id": "abc123",
  "title": "Shell-GPT setup notes",
  "message_count": 4,
  "messages": [
    {
      "role": "user",
      "content": "How do I install Shell-GPT?",
      "position": 0
    },
    {
      "role": "assistant",
      "content": "Install it with pipx:\n\n```bash\npipx install shell-gpt\n```",
      "position": 1
    }
  ]
}
```

A duplicate share ID returns HTTP `200` with `"status": "already_exists"` and the
existing stored record. It does not refresh the title or messages.

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | Imported or already present | Not set |
| `400` | Application URL validation failed | Validator message, for example `Only chatgpt.com URLs are allowed.` |
| `422` | Missing/invalid body or malformed URL field | FastAPI validation array |
| `500` | SQLite persistence failed | `Unable to save conversation to database.` |
| `502` | Fetch or extraction failed | `Unable to fetch shared conversation: ...` or `Unable to extract conversation: ...` |

### URL rules

Accepted:

```text
https://chatgpt.com/share/<share-id>
https://chatgpt.com/share/<share-id>/
```

Rejected:

| Input | Reason |
| --- | --- |
| `http://chatgpt.com/share/abc` | HTTPS required |
| `https://chat.openai.com/share/abc` | Host must be `chatgpt.com` |
| `https://chatgpt.com/c/abc` | Path must be `/share/<id>` |
| `https://chatgpt.com/share/abc/extra` | Extra path segments |
| `https://user:pass@chatgpt.com/share/abc` | Credentials |
| `https://chatgpt.com:8443/share/abc` | Custom port |

Query strings and fragments are normalized away in the stored source URL.

### Fetch behavior

| Limit | Value |
| --- | --- |
| Timeout | 20 seconds |
| Response size | 5 MB |
| Redirects | 3, revalidated |
| Content types | `text/html`, `application/xhtml+xml` |

### Notes

- Private or unshared conversations fail with a fetch error.
- The importer does not accept ChatGPT export ZIP files.
- The importer does not update an existing conversation.
- Indexing is a separate request and can fail without rolling back the import.
- The response contains the full message list; large conversations produce a
  large response body.

## Related pages

- [Importing Conversations](../user-guide/importing-conversations.md)
- [Importing ChatGPT URLs](../guides/importing-chatgpt-urls.md)
- [Indexing](indexing.md)
- [Errors](errors.md)
