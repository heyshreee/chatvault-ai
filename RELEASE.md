# Release Process

ChatVault AI uses [Semantic Versioning](https://semver.org/) and annotated Git
tags. The version is stored in these places and must stay in sync:

- `pyproject.toml` → `[project].version`
- `app/core/config.py` → `APP_VERSION`
- `.env.example` → `APP_VERSION`
- `frontend/package.json` → `version`
- `frontend/package-lock.json` → root `version` fields
- `CHANGELOG.md` → release section

## Checklist

1. Start from an up-to-date `main`:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

2. Update the version fields. For the frontend, use:

   ```bash
   cd frontend
   npm version 1.0.0 --no-git-tag-version
   ```

3. Add a dated section to `CHANGELOG.md` and update
   `docs/releases/v<version>.md` if the release has user-facing notes.

4. Run the full check:

   ```bash
   make check
   ```

   Optionally run the real Ollama integration test on a machine with Ollama:

   ```bash
   make test-ollama
   ```

5. Commit the release preparation:

   ```bash
   git add -A
   git commit -m "chore: release v1.0.0"
   ```

6. Create and verify the annotated tag:

   ```bash
   git tag -a v1.0.0 -m "ChatVault AI v1.0.0"
   git show --stat v1.0.0
   ```

7. Push the commit and tag:

   ```bash
   git push origin main
   git push origin v1.0.0
   ```

8. The `Release` workflow creates the GitHub release from the tag. To create it
   manually instead:

   ```bash
   gh release create v1.0.0 \
     --title "ChatVault AI v1.0.0" \
     --notes-file docs/releases/v1.0.0.md \
     --verify-tag
   ```

9. Confirm the release, CI run, and tag on GitHub.

## Hotfix releases

For a security or critical bug fix, branch from the released tag, apply the
minimal fix, add a patch version (for example `1.0.1`), and repeat the checklist.
Do not rewrite a published tag.

## Rollback

If a release is broken, publish a new patch release with the fix. Deleting or
force-pushing a published tag is not supported because it breaks downstream
clones and release links.
