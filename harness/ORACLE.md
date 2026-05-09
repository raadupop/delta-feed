# Oracle scripts — contract

The oracle scripts (`harness/check-*.sh`) are one of three components of the
in-turn agent harness, alongside the **steering manager** (`harness/steer.sh`,
see [STEERING.md](STEERING.md)) and the per-agent **adapters**
(`.claude/hooks/*.sh` for Claude Code).

The harness as a whole is the wired implementation of
[ADR-0001](../doc/adr/0001-agent-harness-architecture.md) **Layer 4 (feedback
oracles)** for the classification service. Reusing ADR-0001's vocabulary: an
"oracle" is any mechanism that returns pass/fail on the agent's work; these
scripts are the executable subset, narrower than ADR-0001's full Layer 4 (which
also includes specialist review and reality-derived oracles).

## Invariants

The oracle scripts answer one question: *given the current code state, is the
system within its declared invariants?*

1. **Pure function of code state.** No environment variables read, no clocks,
   no network, no random. Same files in, same output out.
2. **No side effects.** Read from disk only. Never write to disk; never touch
   `.harness-state/`; never emit decisions.
3. **No agent awareness.** Output is plain text. No JSON, no `decision: block`,
   no `additionalContext`. Adapters wrap output for their agent's protocol.
4. **Stable CLI.** Each script takes positional args, returns plain text on
   stdout, sets a non-zero exit code on red.

## Scripts

### `harness/check-suite.sh [--changed-only]`

Runs the full pytest suite for the classification component.

- Args: `--changed-only` skips invocation if `git diff --quiet -- apps/classification/`
  reports a clean working tree (no edits or staged changes under classification).
- Stdout: pytest output (`-x --tb=line`), or empty when skipped.
- Exit codes: `0` = green or skipped; `1` = red.

### `harness/check-py.sh <file>`

Runs `ruff check` and `mypy` on a single Python file under
`apps/classification/`. Caller is responsible for path filtering.

- Args: `<file>` — repo-relative path (must reside under `apps/classification/`).
- Stdout: combined ruff + mypy output, formatted with section headers.
- Exit codes: `0` = clean; `1` = ruff or mypy red.

### `harness/fixture-reminder.sh <file>`

Emits the fixture-changed reminder text for an anchor fixture path. Advisory.

- Args: `<file>` — repo-relative path (must reside under
  `apps/classification/tests/acceptance/fixtures/`).
- Stdout: reminder paragraph.
- Exit code: always `0`.

## Determinism guarantee

Two consecutive invocations with no edits in between MUST produce identical
output and identical exit codes. Without this property, the oracle is a
heuristic, not a check.

## What does NOT belong here

- Per-turn state. Owned by the steering manager.
- Decisions about whether to block an agent. Owned by the steering manager.
- JSON or agent-specific protocol. Owned by the adapters.
- Multi-app suite registry. Deferred until a second app exists.
