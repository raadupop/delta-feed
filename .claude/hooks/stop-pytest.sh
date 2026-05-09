#!/usr/bin/env bash
# Adapter (Claude Code): Stop hook.
# Reads CC's stdin payload, honors CC's own re-entry signal as a belt-and-
# braces, delegates to harness/steer.sh, wraps a block (rc=2) as CC block
# JSON. The steering manager's convergence detection is the primary loop
# bound; this adapter just translates protocols.
#
# Wired by .claude/settings.json. See harness/STEERING.md.

set -u

payload=$(cat)

stop_active=$(printf '%s' "$payload" | jq -r '.stop_hook_active // false')
if [ "$stop_active" = "true" ]; then
  exit 0
fi

session=$(printf '%s' "$payload" | jq -r '.session_id // empty')
[ -n "$session" ] || session="unknown"

repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

out=$("$repo_root/harness/steer.sh" stop --session="$session" 2>&1); rc=$?

case "$rc" in
  0)
    # Allow stop. Forward any advisory text (e.g. escalate:stuck notice) so
    # the operator sees it.
    [ -n "$out" ] && printf '%s\n' "$out"
    exit 0
    ;;
  2)
    printf '%s' "$out" \
      | jq -Rs '{
          decision: "block",
          reason: ("Pytest red on Stop. Classify per the steering loop (Case A) and address before terminating the turn:\n" + .)
        }'
    exit 0
    ;;
  *)
    # Fail open on internal errors. Log the rc but allow stop.
    printf 'steer.sh internal error rc=%s; allowing stop\n%s\n' "$rc" "$out" >&2
    exit 0
    ;;
esac