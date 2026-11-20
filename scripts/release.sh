#!/usr/bin/env bash
# Usage: scripts/release.sh <patch|minor|major|X.Y.Z>
# Bumps the version, runs tests, commits, tags, and pushes.
# The tag push triggers .github/workflows/publish.yml, which publishes to PyPI.
set -euo pipefail

bump="${1:?usage: scripts/release.sh <patch|minor|major|X.Y.Z>}"
cd "$(git rev-parse --show-toplevel)"

[ "$(git branch --show-current)" = "main" ] || { echo "Not on main"; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "Working tree not clean"; exit 1; }
git pull --ff-only

case "$bump" in
  patch|minor|major) uv version --bump "$bump" ;;
  *) uv version "$bump" ;;
esac
version="$(uv version --short)"

if git rev-parse -q --verify "refs/tags/v${version}" >/dev/null; then
  echo "Tag v${version} already exists"; git checkout -- pyproject.toml uv.lock; exit 1
fi

uv run pytest tests/ -q

git add pyproject.toml uv.lock
git commit -m "Release v${version}"
git tag "v${version}"
git push origin main "v${version}"

echo "Pushed v${version}. Publishing: https://github.com/patclrk/bizdurr/actions/workflows/publish.yml"
