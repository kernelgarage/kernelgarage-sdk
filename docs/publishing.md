# Publishing

`main` is protected (no direct pushes; PRs must pass CI to merge), so releases
go through two chained Actions instead of a local script:

1. **[Prepare Release](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/prepare-release.yml)** — run
   manually from the Actions tab (`workflow_dispatch`) with a `bump` input
   (`patch`/`minor`/`major`). It lints and tests, bumps the version with
   `uv version --bump`, and pushes the result to a `release/vX.Y.Z` branch,
   opening a PR against `main`.
2. Review and merge that PR like any other. Once merged, **[Tag
   Release](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/tag-release.yml)** runs on the resulting push
   to `main`: it reads the version with `uv version --short` and, if no
   GitHub release exists for it yet, creates one with
   `gh release create --generate-notes`. That publish event triggers
   [pypi-publish.yml](https://github.com/kernelgarage/kernelgarage-sdk/blob/main/.github/workflows/pypi-publish.yml), which builds and
   uploads the package to PyPI.

## One-time setup

- Branch protection on `main`: require a pull request before merging, and
  require the CI workflow's checks to pass.
- A `RELEASE_TOKEN` repository secret — a PAT (or GitHub App token) with
  `contents: write` and `pull-requests: write` on this repo. The default
  `GITHUB_TOKEN` can't be used for the checkout/push/PR-create steps in
  *Prepare Release*: events it triggers don't fire other workflows, so CI
  would never run on the release PR and the required check would never
  appear.
