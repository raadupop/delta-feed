#!/usr/bin/env bash
# Stop hook. Runs the classification pytest suite before the agent
# terminates a turn. On red, blocks the Stop and surfaces output to
# the agent so the steering loop (Case A) engages.
#
# Wired by .claude/settings.json. See doc/adr/0001-agent-harness-architecture.md
# §"Steering loop" and §"Sequencing to close the gap" step 1.

cd apps/classification || exit 0

out=$(pytest tests/ -x --tb=line 2>&1); rc=$?

if [ "$rc" -ne 0 ]; then
  printf '%s' "$out" \
    | jq -Rs '{
        decision: "block",
        reason: ("Pytest red on Stop. Classify per the steering loop (Case A) and address before terminating the turn:\n" + .)
      }'
fi