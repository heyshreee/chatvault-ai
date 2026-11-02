# Release Process

ChatVault AI uses [Semantic Versioning](https://semver.org/) and annotated Git
tags. This guide outlines how releases are prepared, tested, tagged, and published.

## Version locations

The version string must stay synchronized across these files:

| File | Field |
| --- | --- |
| `pyproject.toml` | `[project].version` |
| `app/core/config.py` | `APP_VERSION` |
| `.env.example` | `APP_VERSION` |
| `frontend/package.json` | `version` |
| `frontend/package-lock.json` | root `version` and package entries |
| `CHANGELOG.md` | New version heading |
| `docs/releases/v<version>.md` | Release notes for the tag |

## Release checklist

Follow these steps for every release:

### 1. Ensure a clean working tree

Start on `main` with latest changes:

```bash
git switch main
git pull --ff-only origin main
```

### 2. Update version strings

Update `pyproject.toml`, `app/core/config.py`, and `.env.example`.

For the frontend:

```bash
cd frontend
npm version 1.0.0 --no-git-tag-version
cd ..
```

### 3. Update release notes

1. Add a dated release section to `CHANGELOG.md` and `docs/changelog.md`.
2. Create or update `docs/releases/v<version>.md` with highlights, breaking changes, and verification steps.

### 4. Run the full verification suite

```bash
make check
```

This verifies:

- Python syntax and compilation
- Backend unit and contract tests (120 passed)
- Frontend lint (`oxlint`)
- Frontend production build (`tsc -b && vite build`)

If an Ollama instance is running locally:

```bash
make test-ollama
```

Verify documentation builds cleanly with strict checks:

```bash
python -m mkdocs build --strict
```

### 5. Commit release preparation

```bash
git add -A
git commit -m "chore: release v1.0.0"
```

### 6. Create annotated tag

```bash
git tag -a v1.0.0 -m "ChatVault AI v1.0.0"
git show --stat v1.0.0
```

### 7. Push commit and tag

```bash
git push origin main
git push origin v1.0.0
```

### 8. GitHub Release automation

Pushing the `v*.*.*` tag triggers the `Release` GitHub Actions workflow (`.github/workflows/release.yml`), which builds and creates the GitHub release using the release notes from `docs/releases/v<version>.md`.

To create the release manually using the GitHub CLI:

```bash
gh release create v1.0.0 \
  --title "ChatVault AI v1.0.0" \
  --notes-file docs/releases/v1.0.0.md \
  --verify-tag
```

### 9. Verify deployment

Confirm:

- CI passes on `main`
- Documentation builds and publishes to `gh-pages`
- The GitHub release appears with release notes and tags

## Hotfix releases

For critical bug fixes or security patches:

1. Branch from the released tag: `git checkout -b hotfix/1.0.1 v1.0.0`
2. Apply the minimal necessary patch.
3. Increment the patch version (e.g. `1.0.1`).
4. Repeat the verification and release checklist.
5. Merge the hotfix back to `main`.
6. Never rewrite or delete a published tag.

## Rollback policy

If a release contains critical regressions, publish a new patch release with the fix. Deleting or force-pushing published Git tags is not permitted as it breaks downstream clones, build caches, and release dependencies.
