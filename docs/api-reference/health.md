# Health

## `GET /api/v1/health`

Returns a minimal liveness response. It does not check Ollama, ChromaDB, or
SQLite. Use [`GET /api/v1/models/status`](system.md) for dependency health.

### Response

| Field | Type | Description |
| --- | --- | --- |
| `status` | string | Always `healthy` when the process is serving requests |
| `application` | string | `APP_NAME`, default `ChatVault AI` |
| `version` | string | `APP_VERSION`, default `1.0.0` |

### Example

```bash
curl -s http://127.0.0.1:8000/api/v1/health
```

```json
{
  "status": "healthy",
  "application": "ChatVault AI",
  "version": "1.0.0"
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | The application is running |

A `200` here means the HTTP server is responsive. It does **not** mean indexing
or chat will work.

## `GET /`

An unprefixed status document.

### Example

```bash
curl -s http://127.0.0.1:8000/
```

```json
{
  "application": "ChatVault AI",
  "version": "1.0.0",
  "status": "running",
  "documentation": "/docs"
}
```

### Status codes

| Code | Condition |
| --- | --- |
| `200` | The application is running |

## Related pages

- [System](system.md)
- [Troubleshooting](../guides/troubleshooting.md)
- [Configuration](../getting-started/configuration.md)
