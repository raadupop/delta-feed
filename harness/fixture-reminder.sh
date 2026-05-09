#!/usr/bin/env bash
# Oracle script: fixture-changed advisory reminder.
# Emits the band-derivation rule + sign-off path. Always exits 0.
# Contract: harness/ORACLE.md.

set -u

if [ $# -ne 1 ]; then
  printf 'usage: fixture-reminder.sh <file>\n' >&2
  exit 64
fi

file=$1
norm=$(printf '%s' "$file" | tr '\\' '/')

case "$norm" in
  */apps/classification/tests/acceptance/fixtures/*.json) ;;
  apps/classification/tests/acceptance/fixtures/*.json) ;;
  *)
    printf 'file is not an anchor fixture: %s\n' "$file" >&2
    exit 64
    ;;
esac

cat <<'EOF'
FIXTURE CHANGED. Per ANCHORS.md, expected band MUST derive from the SRS formula
(CLS-001 ECDF rank), not from current implementation output. Source values MUST
cite a verifiable public provider (FRED, BLS, etc.) with a retrieved_at
timestamp. Invoke /trader and /statistician for band-derivation sign-off before
claiming the fixture complete.
EOF