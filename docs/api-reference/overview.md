# API Reference Overview

ChatVault AI exposes a JSON API through FastAPI. This reference documents the
`v1.0.0` routes, request models, response models, and error behavior.

## Base URL

With the default configuration:

```text
http://127.0.0.1:8000/api/v1
```

Every documented route below is relative to that prefix. The prefix comes from
`API_V1_PREFIX` and can be changed in `.env`.

Two routes are outside the prefix:

| Route | Purpose |
| --- | --- |
| `GET /` | Application status document |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | OpenAPI schema |

## Interactive documentation

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

The OpenAPI schema is generated from the live application and reflects the
installed version.

## Authentication

There is none. The API is intended for a single-user local deployment bound to
`127.0.0.1`. Anyone who can reach the port can read, import, delete, index, and
export conversations. See [Privacy and Security](../concepts/privacy-and-security.md).

## Content types

- Requests with bodies use `Content-Type: application/json`.
- JSON responses use `application/json`.
- Export responses are binary file downloads.
- Imports accept a single `url` field.

## Timestamps and IDs

- Timestamps are ISO 8601 strings.
- `indexed_at` is written as a UTC timestamp.
- Conversation IDs are the ChatGPT share IDs from `/share/<id>` and match
  `[A-Za-z0-9_-]+`.
- Message `position` values start at 0.
- Search results and chat source `message_position` values are the stored
  zero-based position. Chat context labels them as 1-based for the model.
- Response source `index` values start at 1.

## Pagination

Only `GET /api/v1/conversations` is paginated:

| Parameter | Default | Range |
| --- | --- | --- |
| `skip` | `0` | `>= 0` |
| `limit` | `20` | `1`-`100` |

The response includes `total` and the requested page in `items`. There is no
cursor pagination.

## Error envelope

Application errors return:

```json
{
  "detail": "Conversation not found."
}
```

Request validation errors return a list from FastAPI:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "message"],
      "msg": "String should have at least 1 character",
      "input": ""
    }
  ]
}
```

Do not depend on the exact validation `type` or `msg` strings across versions;
use the HTTP status and the top-level field names.

## Status codes

| Code | Meaning in ChatVault |
| --- | --- |
| `200` | Success, including `already_exists`, `no_sources`, and empty search results |
| `400` | Import URL rejected by the application validator |
| `404` | Conversation not found |
| `409` | Indexing busy, or the vector index is incompatible and must be rebuilt |
| `422` | Request validation failed, or a conversation has no indexable text |
| `500` | SQLite, ChromaDB, export, or unexpected server failure |
| `502` | Upstream fetch/extraction failed, or Ollama returned an invalid payload |
| `503` | Ollama or ChromaDB is unavailable, or a required model is missing |

## Endpoint index

| Method | Path | Page |
| --- | --- | --- |
| `GET` | `/health` | [Health](health.md) |
| `POST` | `/import/url` | [Import](import.md) |
| `GET` | `/conversations` | [Conversations](conversations.md) |
| `GET` | `/conversations/{conversation_id}` | [Conversations](conversations.md) |
| `DELETE` | `/conversations/{conversation_id}` | [Conversations](conversations.md) |
| `GET` | `/conversations/{conversation_id}/export/pdf` | [Export](export.md) |
| `GET` | `/conversations/{conversation_id}/export/docx` | [Export](export.md) |
| `POST` | `/index/{conversation_id}` | [Indexing](indexing.md) |
| `POST` | `/index/all` | [Indexing](indexing.md) |
| `POST` | `/index/rebuild` | [Indexing](indexing.md) |
| `GET` | `/index/status` | [Indexing](indexing.md) |
| `DELETE` | `/index/{conversation_id}` | [Indexing](indexing.md) |
| `GET` | `/stats` | [System](system.md) |
| `POST` | `/search` | [Search](search.md) |
| `POST` | `/chat` | [Chat](chat.md) |
| `GET` | `/models/status` | [System](system.md) |

## cURL conventions

Examples use `jq` for readability but do not require it:

```bash
curl -s http://127.0.0.1:8000/api/v1/health | jq
```

For errors, include headers:

```bash
curl -i http://127.0.0.1:8000/api/v1/conversations/does-not-exist
```

## Versioning

The API prefix is versioned as `v1`, but there is no separate version negotiation
header. The application version is reported by `GET /api/v1/health` and
`GET /api/v1/models/status`. Breaking changes are expected to use a new prefix.

## Related pages

- [Errors](errors.md)
- [Health](health.md)
- [Import](import.md)
- [Chat](chat.md)
