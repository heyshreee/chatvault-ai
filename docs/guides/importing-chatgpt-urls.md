# Importing ChatGPT URLs

This guide explains how ChatGPT share links are validated, fetched, parsed, and
stored. For the UI walkthrough, see
[Importing Conversations](../user-guide/importing-conversations.md).

## Create a public share link

Open the conversation in ChatGPT and use its sharing action to create a public
link. Copy the link from the share dialog. The exact ChatGPT interface can change;
the link ChatVault accepts must match:

```text
https://chatgpt.com/share/<share-id>
```

Do not use a private conversation URL, a `/c/` URL, or `chat.openai.com`.

## Validation rules

The backend validator in `app/ingestion/url_validator.py` enforces:

| Rule | Rejection message |
| --- | --- |
| Non-empty string | `URL cannot be empty.` |
| HTTPS scheme | `Only HTTPS URLs are allowed.` |
| Host exactly `chatgpt.com` | `Only chatgpt.com URLs are allowed.` |
| No username or password | `URL credentials are not allowed.` |
| No custom port (default or 443 only) | `Custom ports are not allowed.` |
| Path exactly `/share/<id>` with optional slash | `Invalid ChatGPT shared conversation URL.` |

The share ID uses `[A-Za-z0-9_-]+`. The validator returns a normalized URL:

```text
https://chatgpt.com/share/<share-id>
```

Query strings and fragments do not affect the stored canonical URL.

## Fetching

`app/ingestion/fetcher.py`:

- Uses an async `httpx` client with a 20 second timeout.
- Sends a `ChatVaultAI/0.1` user agent and accepts HTML.
- Does not follow redirects automatically.
- Follows at most three redirects, validating every target with the same rules.
- Blocks redirects to other hosts.
- Rejects non-HTML content types.
- Streams the body and rejects responses over 5 MB.
- Decodes using the response encoding or UTF-8 with replacement.

This is the SSRF boundary. Only the public `chatgpt.com` share host is reachable
through the importer.

## Extraction

The extractor first looks for ChatGPT's serialized payload inside a script
containing `.enqueue(`. The payload is a serialized JSON array with indexed
references. The extractor:

1. Resolves property references.
2. Finds the object containing `mapping` and `linear_conversation`.
3. Builds a node lookup by node ID.
4. Walks the linear conversation order.
5. Keeps `user` and `assistant` authors only.
6. Keeps only content with `content_type == "text"`.
7. Joins text parts and cleans ChatGPT annotations.

If the serialized format is unavailable, it falls back to legacy HTML elements
with `data-message-author-role` attributes. This fallback exists mainly for
compatibility with older saved pages and test fixtures.

If no supported messages are found, extraction raises an error and the API
returns HTTP `502` with `Unable to extract conversation: ...`.

## Text cleaning

ChatGPT share pages contain private-use annotations such as URL, entity, image,
and generated-UI markers. The cleaner:

- Replaces URL annotations with the readable title, or the URL when no title
  exists.
- Replaces entity annotations with the first readable string value.
- Drops generated-UI, image-group, and unknown UI-only annotations.
- Removes residual private-use characters.

The cleaner runs during extraction, chunking, retrieval, conversation detail
responses, and document exports. This prevents annotation noise from appearing in
answers or exports.

## Persistence and duplicates

The conversation is stored with:

- `conversation_id` from the share path.
- `title` from the payload or HTML title.
- `source_url` as the normalized URL.
- Ordered messages with role, content, and position.

`conversation_id` is unique. A duplicate import returns the existing record with
status `already_exists` and does not update it.

## Error mapping

| Condition | HTTP status | Response detail |
| --- | --- | --- |
| Invalid URL caught by the route | `400` | Validator message |
| Invalid request body or malformed URL type | `422` | FastAPI validation array |
| Fetch timeout, HTTP error, redirect, size, or content type | `502` | `Unable to fetch shared conversation: ...` |
| Extraction failure | `502` | `Unable to extract conversation: ...` |
| SQLite persistence failure | `500` | `Unable to save conversation to database.` |

The fetch error may include a safe diagnostic such as
`ChatGPT returned HTTP 404.` It does not include conversation content.

## Verify with curl

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/import/url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://chatgpt.com/share/<share-id>"}'
```

Then confirm storage:

```bash
curl http://127.0.0.1:8000/api/v1/conversations
curl http://127.0.0.1:8000/api/v1/conversations/<share-id>
```

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `Only chatgpt.com URLs are allowed.` | Using `chat.openai.com` or another host |
| `Invalid ChatGPT shared conversation URL.` | Missing `/share/` or extra path segments |
| `Unable to fetch shared conversation: ChatGPT returned HTTP 403.` | Share page is not public or ChatGPT blocked the request |
| `Unable to fetch shared conversation: Response exceeds the 5 MB size limit.` | Page is too large for the importer |
| `Unable to extract conversation: No supported user or assistant text messages found.` | Page format changed or contains no text messages |
| `already_exists` | Share ID is already stored; delete it first to re-import |

## Related pages

- [Import API](../api-reference/import.md)
- [Document Processing](document-processing.md)
- [Privacy and Security](../concepts/privacy-and-security.md)
