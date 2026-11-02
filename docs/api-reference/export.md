# Export

ChatVault AI exports one conversation per request as a PDF or DOCX file. Both
endpoints read from SQLite and write to `storage/generated/`.

## `GET /api/v1/conversations/{conversation_id}/export/pdf`

### Response

A binary PDF download.

| Header | Value |
| --- | --- |
| `Content-Type` | `application/pdf` |
| `Content-Disposition` | Attachment with `<conversation_id>.pdf` |

The file is also written to:

```text
storage/generated/<conversation_id>.pdf
```

### Example

```bash
curl -OJ http://127.0.0.1:8000/api/v1/conversations/abc123/export/pdf
```

`-O` saves using the server-provided filename; `-J` honors
`Content-Disposition`.

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | PDF generated | Not set |
| `404` | Conversation not found | `Conversation not found.` |
| `500` | Generation failed | `Unable to generate PDF.` |

The most common `500` cause is missing DejaVu fonts at
`/usr/share/fonts/truetype/dejavu`. Install `fonts-dejavu-core` on Debian/Ubuntu.
The font path is not configurable in `v1.0.0`.

## `GET /api/v1/conversations/{conversation_id}/export/docx`

### Response

A binary DOCX download.

| Header | Value |
| --- | --- |
| `Content-Type` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `Content-Disposition` | Attachment with `<conversation_id>.docx` |

The file is also written to:

```text
storage/generated/<conversation_id>.docx
```

### Example

```bash
curl -OJ http://127.0.0.1:8000/api/v1/conversations/abc123/export/docx
```

### Status codes

| Code | Condition | `detail` |
| --- | --- | --- |
| `200` | DOCX generated | Not set |
| `404` | Conversation not found | `Conversation not found.` |
| `500` | Generation failed | `Unable to generate DOCX.` |

DOCX export does not depend on the DejaVu font files. The document references
DejaVu font names, but the viewer may substitute fonts.

## Output naming and safety

The output path is built from the conversation ID after validating:

```text
[A-Za-z0-9_-]{1,100}
```

Only `.pdf` and `.docx` are accepted. This prevents path traversal through the
ID.

Existing files with the same name are overwritten.

## Rendering support

| Markdown construct | PDF | DOCX |
| --- | --- | --- |
| Headings | Yes | Yes |
| Paragraphs | Yes | Yes |
| Bullet and numbered lists | Yes | Yes |
| Task lists | Yes | Yes |
| Block quotes | Yes | Yes |
| Fenced code blocks | Yes | Yes |
| Pipe tables | Yes | Yes |
| Horizontal rules | Yes | Yes |
| Inline code, bold, italic | Basic | Basic |

Not supported as rich content: images, raw HTML, footnotes, deeply nested
structures, and arbitrary Markdown extensions.

## Notes

- Export requests are synchronous. Large conversations take longer.
- There is no batch export, combined library export, or background job.
- There is no automatic cleanup of `storage/generated/`.
- Exports do not call Ollama or ChromaDB.
- Deleting a conversation does not delete its previously generated files.

## Related pages

- [Export guide](../user-guide/export.md)
- [Document Processing](../guides/document-processing.md)
- [Conversations](conversations.md)
- [Troubleshooting](../guides/troubleshooting.md)
