# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This is an early-stage skeleton for the `kernelgarage` Python package (SDK). The
only code so far is `src/kernelgarage/__init__.py` (a `main()` entry point) and
`src/kernelgarage/version.py` (reads the installed package version via
`importlib.metadata`, falling back to `"0.0.0"` when not installed). Expect to
build out real functionality from this base.

## Commands

```bash
uv sync                       # install deps (requires Python >=3.14)
uv run pytest                 # run tests; coverage config lives in pyproject.toml
uv run pytest tests/test_version.py::test_falls_back_when_package_not_installed  # single test
uv run ruff check .           # lint
uv run ruff format --check .  # format check (use `uv run ruff format .` to fix)
uv run ty check .             # type check
```

CI (`.github/workflows/ci.yml`) runs these three checks (lint+format, typecheck,
test) as separate jobs on every PR to `main`. All must pass before merge.

## Conventions

- Branch naming: `<type>/<short-kebab-case-description>` (`feature/`, `fix/`,
  `docs/`, `chore/`, `refactor/`). `release/vX.Y.Z` is reserved for automated
  release branches — don't use it for regular work. See `CONTRIBUTING.md`.
- Commit/PR messages: imperative mood ("Add x", not "Added x").
- `main` is protected: no direct pushes; all changes land via PR and must pass
  CI.
- Ruff lint rules enabled: `E, F, I, UP, B, SIM, RUF, S` (see `pyproject.toml`).
  `S101` (assert usage) is ignored under `tests/`.
- `ty` type checking has an extensive set of rules escalated to `error` in
  `pyproject.toml` — pay attention to `ty check` output, since many checks
  that are warnings by default are hard errors here.

## Releasing

Releases go through two chained GitHub Actions rather than a local script,
because `main` is protected and the default `GITHUB_TOKEN` can't trigger
downstream workflows:

1. **Prepare Release** (`.github/workflows/prepare-release.yml`) — run
   manually via `workflow_dispatch` with a `bump` input (`patch`/`minor`/`major`).
   Lints and tests, bumps the version with `uv version --bump`, pushes to a
   `release/vX.Y.Z` branch, and opens a PR against `main`.
2. Merging that PR triggers **Tag Release**
   (`.github/workflows/tag-release.yml`), which reads the version via
   `uv version --short` and creates a GitHub release if one doesn't exist yet
   for that version. The release-publish event then triggers
   `.github/workflows/pypi-publish.yml`, which builds and uploads to PyPI.

This requires a `RELEASE_TOKEN` repo secret (a PAT/GitHub App token with
`contents: write` and `pull-requests: write`) and branch protection on `main`
requiring a PR plus passing CI checks.
