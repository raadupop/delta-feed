#!/usr/bin/env bash
# PostToolUse hook for Edit|Write on apps/classification/app/**/*.py.
# Runs targeted ruff + mypy on the changed file. On red, blocks turn
# completion and surfaces tool output to the agent.
#
# Wired by .claude/settings.json. See doc/adr/0001-agent-harness-architecture.md
# §"Concrete trigger map" and §"Sequencing to close the gap".

f=$(jq -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0

norm=$(printf '%s' "$f" | tr '\\' '/')
case "$norm" in
  */apps/classification/app/*.py) rel=${norm##*/apps/classification/} ;;
  *) exit 0 ;;
esac

cd apps/classification || exit 0

ruff_out=$(ruff check "$rel" 2>&1); ruff_rc=$?
mypy_out=$(mypy "$rel" 2>&1); mypy_rc=$?

if [ "$ruff_rc" -ne 0 ] || [ "$mypy_rc" -ne 0 ]; then
  printf 'ruff:\n%s\n\nmypy:\n%s' "$ruff_out" "$mypy_out" \
    | jq -Rs --arg rel "$rel" '{
        decision: "block",
        reason: ("Lint/type errors in " + $rel + ":\n" + .)
      }'
fi