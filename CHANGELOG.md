# Changelog

All notable changes to ChatVault AI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-01

### Added

- FastAPI backend for importing public ChatGPT share conversations, storing them
  in SQLite, and exporting them as PDF or DOCX.
- Message-aware chunking, Ollama embeddings, ChromaDB persistence, per-conversation
  indexing, bulk indexing, index deletion, and index rebuild.
- Retrieval-augmented chat at `POST /api/v1/chat` with conversation history,
  numbered source citations, and a no-source response that does not call the
  chat model.
- Semantic search at `POST /api/v1/search`, dashboard statistics at
  `GET /api/v1/stats`, and model/system status at `GET /api/v1/models/status`.
- Six-page React frontend: Dashboard, AI Chat, Library, Import, Conversation,
  and Settings.
- PDF and DOCX formatting for headings, lists, task lists, block quotes, pipe
  tables, fenced code blocks, and horizontal rules.
- Shared Markdown block parser and a ChatGPT private-use annotation cleaner used
  by ingestion, API responses, chunking, retrieval, and exports.
- Route-level frontend lazy loading and a separate Markdown/Prism chunk.
- Packaging metadata in `pyproject.toml`, a `setup.py` compatibility shim, and a
  `run.py` launcher.
- GitHub Actions CI for backend tests and frontend lint/build.
- GitHub Actions release workflow for `v*.*.*` tags.
- Contributor, security, support, release, and code-of-conduct documentation.

### Changed

- The default local chat model is now `llama3.2:3b` (previously
  `qwen2.5:3b`).
- PDF exports normalize emoji and terminal symbols to supported glyphs and
  preserve code indentation.
- DOCX exports use real Word tables, list/quote styles, shaded code blocks, and
  inline formatting runs.
- Frontend routes are loaded on demand, removing the previous large single-bundle
  warning.
- Unused Vite scaffold assets and styles were removed.

### Fixed

- ChatGPT private-use annotations no longer leak into conversation responses,
  retrieval context, or exported documents.
- Markdown tables no longer appear as raw pipe text in PDF or DOCX exports.
- Block quotes, horizontal rules, and task lists render correctly in exports.
- Headings are kept with the following content instead of being orphaned at the
  bottom of a PDF page.
- PDF code blocks preserve indentation and blank lines.

### Security

- Imported conversation text continues to be treated as untrusted data in RAG
  prompts.
- Conversation text and secrets are excluded from logs and version control.
- SSRF validation and public-share URL checks remain enforced at import time.

### Verification

- Backend test suite: 120 passed, 1 skipped. The skipped test is the opt-in real
  Ollama integration test.
- Frontend production build and lint pass.
- Live AI Chat UI verification passed against the real backend, SQLite data,
  ChromaDB retrieval, and built frontend. The final verification environment did
  not have Ollama installed, so a local fake Ollama endpoint supplied the model
  response; this is documented in `HANDOFF.md`.

[1.0.0]: https://github.com/heyshreee/chatvault-ai/releases/tag/v1.0.0
