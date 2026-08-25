# Development

Requires Python >=3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                       # install deps
uv run pytest                 # run tests; coverage config lives in pyproject.toml
uv run ruff check .           # lint
uv run ruff format --check .  # format check (use `uv run ruff format .` to fix)
uv run ty check .             # type check
```

Run a single test:

```bash
uv run pytest tests/test_version.py::test_falls_back_when_package_not_installed
```

CI ([ci.yml](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/ci.yml)) runs lint+format, typecheck, and
test as separate jobs on every PR to `main`. All must pass before merge.

## Docs

Docs are built with [MkDocs](https://www.mkdocs.org/) +
[mkdocstrings](https://mkdocstrings.github.io/) and live in this `docs/`
folder plus `mkdocs.yml` at the repo root.

```bash
uv run mkdocs serve   # live preview at http://127.0.0.1:8000
uv run mkdocs build   # static site in site/
```

They're published to GitHub Pages automatically on every push to `main` (see
[docs.yml](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/docs.yml)).
This requires the repo's Pages source (Settings → Pages) to be set to "GitHub
Actions" — a one-time setup step.

## Conventions

- See [Contributing](contributing.md) for branch naming and the PR process.
- Ruff lint rules enabled: `E, F, I, UP, B, SIM, RUF, S` (see `pyproject.toml`).
  `S101` (assert usage) is ignored under `tests/`.
- `ty` type checking has an extensive set of rules escalated to `error` in
  `pyproject.toml` — pay attention to `ty check` output, since many checks
  that are warnings by default are hard errors here.
