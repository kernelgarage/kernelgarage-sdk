# kernelgarage

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Releasing

```bash
./scripts/release.sh [major|minor|patch|...]  # defaults to patch
```

This bumps the version in `pyproject.toml`/`uv.lock`, runs lint and tests,
commits and pushes the bump to `main`, then creates a GitHub release for the
new version tag. Publishing the release triggers `.github/workflows/pypi-publish.yml`,
which builds and uploads the package to PyPI.

The commit must be pushed to `origin/main` *before* the release is created:
`gh release create` tags the remote's current default-branch tip, not your
local commit, so creating the release first would tag the wrong commit.

Requires a clean working tree on `main`, up to date with `origin/main`, and
the [`gh` CLI](https://cli.github.com/) authenticated.
