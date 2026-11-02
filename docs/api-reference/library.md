# Library API

The ChatVault AI backend manages the conversation library through the `/api/v1/conversations` endpoints.

For complete endpoint specifications, request/response schemas, query parameters, and curl examples, see:

- [Conversations API Reference](conversations.md) — List conversations (`GET /api/v1/conversations`), fetch conversation details (`GET /api/v1/conversations/{conversation_id}`), and delete conversations (`DELETE /api/v1/conversations/{conversation_id}`).
- [Export API Reference](export.md) — Export conversations to PDF (`GET /api/v1/conversations/{conversation_id}/export/pdf`) or DOCX (`GET /api/v1/conversations/{conversation_id}/export/docx`).
- [Library Management User Guide](../user-guide/library-management.md) — Using the frontend Library page to search, filter, view transcripts, and manage conversations.
