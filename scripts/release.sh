#!/usr/bin/env bash
# Cut a release: bump the version, commit, push, and publish a GitHub release.
# The pypi-publish workflow triggers off the release being published.
set -euo pipefail

bump="${1:-patch}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "error: working tree is not clean" >&2
  exit 1
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "main" ]]; then
  echo "error: must be on main (currently on $branch)" >&2
  exit 1
fi

git fetch origin main
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
  echo "error: local main is not up to date with origin/main" >&2
  exit 1
fi

uv run ruff check .
uv run ruff format --check .
uv run pytest

uv version --bump "$bump"
version="$(uv version --short)"

git add pyproject.toml uv.lock
git commit -m "v${version}"
git push origin main

gh release create "v${version}" --generate-notes
