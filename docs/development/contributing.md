# Contributing

Contributions should preserve the properties that make ChatVault AI useful:

- Conversation data stays on the user's machine.
- SQLite remains the source of truth.
- ChromaDB remains a rebuildable derived index.
- Imported conversation content is treated as untrusted data.

By participating, you agree to follow the
[Code of Conduct](https://github.com/heyshreee/chatvault-ai/blob/main/CODE_OF_CONDUCT.md).

## Before you start

- Search existing [issues](https://github.com/heyshreee/chatvault-ai/issues)
  before opening a new one.
- For security problems, do not open a public issue. Follow
  [Privacy and Security](../concepts/privacy-and-security.md).
- For large features or behavior changes, open an issue first so the approach can
  be discussed.

## Development setup

Follow [Development Setup](development-setup.md). In short:

```bash
git clone https://github.com/<your-user>/chatvault-ai.git
cd chatvault-ai
git remote add upstream https://github.com/makitdev/chatvault-ai.git
make install
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

## Checks

Run the same checks as CI before opening a pull request:

```bash
make check
```

That covers Python compilation, frontend lint, backend tests, and the production
frontend build. For documentation changes:

```bash
. .docs-venv/bin/activate
mkdocs build --strict
```

## Coding guidelines

### Backend

- Use Python 3.13 syntax and type hints on public functions.
- Keep API response shapes stable. Update `app/api/schemas.py`, the route, and
  `frontend/src/types/api.ts` together.
- Add tests for behavior changes. Use `tests/fakes.py` instead of live Ollama
  calls.
- Preserve the local-first security model:
    - Do not send conversation text to hosted services.
    - Treat imported content as untrusted.
    - Do not log conversation text or secrets.
    - Keep SSRF protections in the URL validator and fetcher intact.
- Keep storage paths out of Git.

### Frontend

- TypeScript, functional components, and Tailwind utilities.
- Use TanStack Query for server state and cache invalidation.
- Keep controls keyboard accessible and labeled.
- Run `npm run lint` and `npm run build`.

### Documentation

- Add new pages to `nav` in `mkdocs.yml`.
- Use relative links to other docs pages.
- Do not document planned features as implemented.
- Run `mkdocs build --strict`.

## Branches and commits

Use a short, descriptive branch name:

```text
feat/streaming-chat
fix/docx-table-width
docs/release-checklist
```

Write imperative, focused commits:

```text
feat: add conversation export retry
fix: preserve code indentation in PDF exports
docs: document the Ollama model override
```

## Pull requests

A good pull request:

- Explains the problem and the chosen approach.
- Links the related issue when one exists.
- Includes tests for new behavior and regressions.
- Updates documentation for user-visible changes.
- Passes `make check`.
- Avoids unrelated formatting churn.

Open pull requests against `main` on
[heyshreee/chatvault-ai](https://github.com/heyshreee/chatvault-ai). The
`makitdev/chatvault-ai` repository is the upstream project; maintainers may
forward changes there.

## Reporting bugs

Include:

- Version and commit.
- Operating system, Python, Node.js, and Ollama versions.
- Whether the issue is in the UI, API, indexing, or export.
- HTTP status and `detail`.
- Output from `GET /api/v1/models/status` and `GET /api/v1/index/status`.

Do not include private conversation text, share links, API keys, or `.env`
contents.

## License

By contributing, you agree that your contributions are licensed under the
[GNU General Public License v3.0](https://github.com/heyshreee/chatvault-ai/blob/main/LICENSE).

## Related pages

- [Development Setup](development-setup.md)
- [Testing](testing.md)
- [Project Structure](project-structure.md)
