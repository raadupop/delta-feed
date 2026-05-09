# Steering manager — contract

The steering manager (`harness/steer.sh`) is one of three components of the
in-turn agent harness, alongside the **oracle scripts** (`harness/check-*.sh`,
see [ORACLE.md](ORACLE.md)) and the per-agent **adapters**
(`.claude/hooks/*.sh` for Claude Code).

The harness as a whole is the wired implementation of
[ADR-0001](../doc/adr/0001-agent-harness-architecture.md) **Layer 4 (feedback
oracles)** for the classification service. The steering manager is the
agent-agnostic decision layer: it owns per-turn state, runs the oracle, and
emits a block / allow decision based on a bounded self-correction loop with
convergence detection.

## CLI

```
harness/steer.sh stop --session=<id>
```

- `--session=<id>` — opaque string identifying the agent turn-group. Adapters
  pass through whatever their runtime provides (Claude Code: `session_id`).

Exit codes:

- `0` — allow stop. Stdout may be empty or carry an advisory message.
- `2` — block stop. Stdout is the report the adapter must surface to the
  agent.
- `64` — usage error.
- `>2` — internal error; adapter should fail open (allow stop) and log.

## State

Per-session JSON file under `.harness-state/<session>.json`. Schema:

```json
{
  "attempts": 1,
  "prior_fingerprint": "<sha256-hex>"
}
```

- `attempts` — count of times this session has been blocked on red.
- `prior_fingerprint` — hash of the failing test set from the last block.
  Used for convergence detection.

Created on first block, updated on subsequent blocks, deleted on terminal
states (green, convergence, budget exhausted).

## Decision log

Append-only JSON Lines at `.harness-state/decisions.log`. One line per
invocation that produces a decision. Schema:

```json
{"ts": "<ISO-8601>", "session": "<id>", "decision": "<class>", "attempts": <n>}
```

Decision classes:

- `green` — suite passed. Allow stop.
- `skip:no_edits` — `--changed-only` reported nothing to do. Allow stop.
- `block:first_attempt` — first red of the turn. Block.
- `block:progress` — red, but failures changed since last block. Block.
- `escalate:stuck` — red, failures unchanged since last block. Allow stop;
  surface to operator.
- `escalate:budget_exhausted` — `attempts >= MAX_ATTEMPTS`. Allow stop;
  surface to operator.
- `error:<reason>` — internal error. Allow stop (fail open).

## Loop policy

```
on stop --session=<id>:
  state ← load(<id>) or {attempts: 0, prior_fingerprint: ""}
  report ← oracle.check-suite --changed-only
  if report empty AND exit 0:
    log "skip:no_edits"; clear_state; exit 0

  if exit 0:
    log "green"; clear_state; exit 0

  fp ← fingerprint(report)        # sha256 of sorted FAILED test ids

  if state.attempts == 0:
    save({attempts: 1, prior_fingerprint: fp})
    log "block:first_attempt"
    print(report); exit 2

  if fp == state.prior_fingerprint:
    log "escalate:stuck"; clear_state
    print("Convergence: failing tests unchanged after one retry.\n" + report)
    exit 0

  if state.attempts + 1 > MAX_ATTEMPTS:
    log "escalate:budget_exhausted"; clear_state
    print("Budget exhausted (" + state.attempts + " attempts).\n" + report)
    exit 0

  save({attempts: state.attempts + 1, prior_fingerprint: fp})
  log "block:progress"
  print(report); exit 2
```

`MAX_ATTEMPTS` defaults to `3`. Override via `HARNESS_MAX_ATTEMPTS` env var.

## Convergence fingerprint

Defined as: sha256 of the sorted, newline-joined list of `FAILED <test_id>`
lines from pytest's short-summary section. Test IDs are stable across edits
that don't rename tests; line numbers and assertion text are intentionally
excluded so that "same tests still failing" is treated as convergence even if
error messages drift.

If you fix one failure and a different test fails, the fingerprint changes →
classified as progress, not convergence. If you fix the symptom but the same
test still fails on a deeper issue, fingerprint is unchanged → classified as
convergence after the next attempt.

## Termination guarantees

The loop always terminates. Across at most `MAX_ATTEMPTS + 1` Stop events in
one session, exactly one of the following happens:

1. Suite turns green (`green`).
2. No edits made (`skip:no_edits`).
3. Failures stop changing (`escalate:stuck`).
4. Attempts cap reached (`escalate:budget_exhausted`).

There is no path that produces an unbounded retry sequence.

## What does NOT belong here

- Agent protocol parsing (CC's `stop_hook_active`, JSON shapes). Owned by
  the adapter.
- The act of running pytest, lint, etc. Owned by the oracle scripts.
- Per-app suite selection. Deferred until a second app exists.