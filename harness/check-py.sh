#!/usr/bin/env bash
# Oracle script: ruff + mypy on a single Python file under
# apps/classification/. Pure function of code state.
# Contract: harness/ORACLE.md.

set -u

if [ $# -ne 1 ]; then
  printf 'usage: check-py.sh <file>\n' >&2
  exit 64
fi

file=$1
norm=$(printf '%s' "$file" | tr '\\' '/')

case "$norm" in
  */apps/classification/*.py) rel=${norm##*/apps/classification/} ;;
  apps/classification/*.py)   rel=${norm#apps/classification/} ;;
  *)
    printf 'file not under apps/classification/: %s\n' "$file" >&2
    exit 64
    ;;
esac

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
  printf 'not inside a git repo\n' >&2; exit 64
}

cd "$repo_root/apps/classification" || {
  printf 'apps/classification not found\n' >&2; exit 64
}

ruff_out=$(ruff check "$rel" 2>&1); ruff_rc=$?
mypy_out=$(mypy "$rel" 2>&1); mypy_rc=$?

if [ "$ruff_rc" -ne 0 ] || [ "$mypy_rc" -ne 0 ]; then
  printf 'ruff:\n%s\n\nmypy:\n%s\n' "$ruff_out" "$mypy_out"
  exit 1
fi

exit 0
