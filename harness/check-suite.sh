#!/usr/bin/env bash
# Oracle script: full pytest suite for the classification component.
# Pure function of code state. No side effects, no agent awareness.
# Contract: harness/ORACLE.md.

set -u

changed_only=0
for arg in "$@"; do
  case "$arg" in
    --changed-only) changed_only=1 ;;
    *) printf 'unknown arg: %s\n' "$arg" >&2; exit 64 ;;
  esac
done

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
  printf 'not inside a git repo\n' >&2; exit 64
}

if [ "$changed_only" -eq 1 ]; then
  if git -C "$repo_root" diff --quiet -- apps/classification \
     && git -C "$repo_root" diff --cached --quiet -- apps/classification; then
    exit 0
  fi
fi

cd "$repo_root/apps/classification" || {
  printf 'apps/classification not found\n' >&2; exit 64
}

pytest tests/ -x --tb=line 2>&1