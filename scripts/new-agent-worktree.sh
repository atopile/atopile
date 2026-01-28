#!/usr/bin/env bash
set -euo pipefail

FEATURE_NAME=${1:-}
if [[ -z "$FEATURE_NAME" ]]; then
  echo "Usage: $0 <feature-name>" >&2
  exit 1
fi

BASE_REF="origin/stage/0.14.x"
BRANCH="feature/${FEATURE_NAME}"
WT_DIR="../atopile-wt/${FEATURE_NAME}"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree is dirty. Commit or stash first." >&2
  exit 1
fi

git fetch origin
git rev-parse --verify "$BASE_REF" >/dev/null

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "Branch $BRANCH already exists" >&2
  exit 1
fi

if [[ -e "$WT_DIR" ]]; then
  echo "Worktree path $WT_DIR already exists" >&2
  exit 1
fi

mkdir -p "$(dirname "$WT_DIR")"
git worktree add -b "$BRANCH" "$WT_DIR" "$BASE_REF"

cd "$WT_DIR"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"

if command -v corepack >/dev/null 2>&1; then
  corepack enable
fi

if [[ -f pnpm-lock.yaml ]]; then
  pnpm install
elif [[ -f package-lock.json ]]; then
  npm ci
elif [[ -f yarn.lock ]]; then
  yarn install --frozen-lockfile
fi

echo "✅ Agent worktree ready at $WT_DIR on $BRANCH"
