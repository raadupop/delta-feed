#!/usr/bin/env bash
# PostToolUse hook for Edit|Write on anchor fixtures.
# Reminds the agent of the band-derivation rule + sign-off path. Advisory
# only; never blocks.
#
# Wired by .claude/settings.json. See doc/adr/0001-agent-harness-architecture.md
# §"Concrete trigger map" and apps/classification/tests/acceptance/fixtures/ANCHORS.md.

f=$(jq -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0

norm=$(printf '%s' "$f" | tr '\\' '/')
case "$norm" in
  */apps/classification/tests/acceptance/fixtures/*.json) ;;
  *) exit 0 ;;
esac

jq -n '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: "FIXTURE CHANGED. Per ANCHORS.md, expected band MUST derive from the SRS formula (CLS-001 ECDF rank), not from current implementation output. Source values MUST cite a verifiable public provider (FRED, BLS, etc.) with a retrieved_at timestamp. Invoke /trader and /statistician for band-derivation sign-off before claiming the fixture complete."
  }
}'