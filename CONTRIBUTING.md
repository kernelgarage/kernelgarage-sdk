# Contributing

## Development setup

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Branch naming

`<type>/<short-kebab-case-description>`, for example `feature/add-retry-logic`
or `fix/version-import-crash`.

| Type       | Use for                                    |
| ---------- | ------------------------------------------- |
| `feature/` | New functionality                           |
| `fix/`     | Bug fixes                                   |
| `docs/`    | Documentation only                          |
| `chore/`   | Tooling, CI, dependencies, other maintenance |
| `refactor/`| Code changes with no behavior change        |

`release/vX.Y.Z` is reserved for the automated branches created by
[Prepare Release](.github/workflows/prepare-release.yml) — don't use it for
regular work.

## Pull requests

`main` is protected: all changes land via a PR, and CI (lint + tests, see
[ci.yml](.github/workflows/ci.yml)) must pass before merging.

1. Branch off `main` using the naming convention above.
2. Make your change; keep commits focused and messages in the imperative
   mood ("Add x", not "Added x" or "Adds x").
3. Open a PR against `main`. Once CI passes and the PR is approved, merge it.

## Releasing

See the [Releasing](README.md#releasing) section in the README.
