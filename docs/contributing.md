# Contributing

See [Development](development.md) for environment setup and the
lint/test/typecheck commands.

## Branch naming

`<type>/<short-kebab-case-description>`, for example `feature/add-retry-logic`
or `fix/version-import-crash`.

| Type        | Use for                                      |
| ----------- | --------------------------------------------- |
| `feature/`  | New functionality                             |
| `fix/`      | Bug fixes                                     |
| `docs/`     | Documentation only                            |
| `chore/`    | Tooling, CI, dependencies, other maintenance  |
| `refactor/` | Code changes with no behavior change          |

`release/vX.Y.Z` is reserved for the automated branches created by
[Prepare Release](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/prepare-release.yml) — don't use it for
regular work.

## Pull requests

`main` is protected: all changes land via a PR, and CI (lint + tests, see
[ci.yml](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/ci.yml)) must pass before merging.

1. Branch off `main` using the naming convention above.
2. Make your change; keep commits focused and messages in the imperative
   mood ("Add x", not "Added x" or "Adds x").
3. Open a PR against `main`. Once CI passes and the PR is approved, merge it.

## Releasing

See [Publishing](publishing.md).
