# ADR-0001: Agent harness architecture for DeltaFeed / INVEX

- **Status:** Accepted
- **Date:** 2026-05-03
- **Deciders:** Radu Pop
- **Supersedes:** —
- **Relates to:** [classification ADR-0001](../../apps/classification/doc/adr/0001-per-indicator-tuning-parameters.md), [classification ADR-0002](../../apps/classification/doc/adr/0002-ecdf-severity-and-backtest-harness.md), [classification ADR-0003](../../apps/classification/doc/adr/0003-test-oracle-architecture.md)

This ADR locks the **agent harness architecture** for the project as a
whole. The architecture answers the project thesis stated in
[AGENTS.md](../../AGENTS.md). DeltaFeed is the research instrument;
INVEX is the trading system being measured. Every component — the
Python classification service today, the six .NET iterations to come
— instantiates the same harness shape with component-specific
mechanics.

This ADR covers the harness as a system: what it is, what its layers
are, how they are triggered, who fires what when. Component-specific
test-oracle architectures (e.g. classification's five oracles + G1
gate) are locked in their own per-component ADRs and reference this
one.

## Glossary (plain language at first use)

A reader new to this project should be able to read this ADR without
prior context. Terms that recur are defined once, plainly:

- **Agent harness.** The practice of designing the surrounding
  environment, infrastructure, and feedback loops for AI coding
  agents — the system that turns them into reliable autonomous work
  engines. Not the test suite (that is one layer); not the prompt
  (that is one input); the whole compositional system.
- **Oracle.** Any mechanism that can look at the agent's work and
  declare a verdict (pass / fail / specific issue). Examples: pytest
  tests, type checkers, lint rules, schema validators, specialist
  reviewers, market-reality checks.
- **Oracle red.** An oracle returned a failure signal. Pytest output
  shows a failed test; mypy reports a type error; etc. The bug was
  caught.
- **Oracle escape.** A bug exists in the agent's work but every
  oracle in the harness returned green. By definition not detectable
  from the oracles' output — only catchable when a non-oracle
  observer (specialist review, a separate independent oracle,
  production reality) raises the issue.
- **Case A / Case B.** The two entry points to the steering loop
  (defined later in this ADR). Case A = oracle red. Case B = oracle
  escape.
- **Layer A** (specific to the classification component, defined in
  classification ADR-0003). A planned, currently unbuilt oracle that
  takes a historical event from a curated catalogue, runs the
  classifier on it, and compares the emitted severity against the
  market's realized implied-volatility path in the post-event window.
  Example assertion: classifier emitted severity 0.3, realized IV
  moved 28% over the next 48 h, the pairing falls outside the
  expected band → FAIL. Layer A is one specific instance of a broader
  **independent reality-derived oracle** pattern.
- **Independent reality-derived oracle.** Any oracle whose ground
  truth is *what actually happened in the world* rather than what the
  spec or the implementation predicts. The "independence" is from the
  spec-and-implementation pair — useful precisely because correlated
  errors between spec and implementation cannot fool a separately-
  sourced oracle.
- **Calibration mismatch with realized market behavior.** The bug
  class where the formula's output (e.g. severity) and the formula's
  own oracles agree, but the output disagrees with the market
  outcome. The classic *self-validating loop* — tests and
  implementation co-evolved from the same wrong assumption; both
  pass; the product is wrong. ADR-0002 at the classification service
  identifies this as a demonstrated failure mode.
- **Steering loop.** The discipline applied when a bug is observed:
  classify it (Case A or Case B), respond per a fixed protocol (fix
  in place, open ADR + new control, or accept gap in
  `LIMITATIONS.md`). Detailed below.

## Context

DeltaFeed measures how AI agents handle six distinct architecture
patterns ([AGENTS.md](../../AGENTS.md)). INVEX, the carrier system,
is reimplemented under each pattern; the Python classification
service is constant infrastructure across all six .NET iterations.
Most code changes — implementation and tests — are proposed by AI
agents in one pass.

Two failure modes are demonstrated, not hypothetical, both at the
classification service:

- **Wrong-level abstraction** (classification ADR-0001). Per-strategy
  module-level constants were invisible to the test suite because
  every strategy under test had only one indicator. Homogeneous
  inputs hid the per-indicator-vs-per-strategy collapse.
- **Self-validating loop** (classification ADR-0002). During a
  four-fixture axis-coverage exercise, an agent writing both the
  implementation and the expected bands in one pass encoded the same
  wrong assumption in both, and the SRS-anchored oracle accepted it.

Common diagnosis: a single oracle is not enough. Bugs that live on
an axis the oracle does not see require a different oracle, not more
tests of the same kind. The harness is the architectural answer.

Operating constraints shape the response:

- **Single operator.** Any control that depends on social process
  (review board, separate QA team) is already failed. Controls must
  be executable by one person plus their AI agents.
- **AI-mediated edits.** The harness is what stops correlated agent
  errors. It cannot rely on the operator catching what the agent
  missed.
- **Iteration-stable contract.** The classifier must not change shape
  every time a .NET iteration begins; the contract layer makes
  iteration churn safe.
- **Controlled-variable framing** ([SRS](../srs/INVEX-SRS.md) ACX-001,
  ACX-002, EVO-001). Agent context is itself a measurement variable
  in the research design; changes to AGENTS.md, skills, or permissions
  require justification because they affect the variable being
  measured.

## Decision

The INVEX agent harness is **five layers** plus a defined **execution
model** (who fires what, when). Each layer has a concrete INVEX
implementation today; gaps are named explicitly.

### Layer 1 — Context architecture (what the agent knows)

- `AGENTS.md` at project root + per-component (Python classification
  today; per-iteration .NET AGENTS.md to come).
- `CLAUDE.md` auto-discovery pointer stubs at every level (so Claude
  Code's context loader resolves regardless of which directory the
  session opens in).
- [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md)
  → root AGENTS.md (single source across Claude Code, Codex, Cursor,
  Copilot).
- Document hierarchy: [SRS](../srs/INVEX-SRS.md) → OpenAPI (root
  [`doc/INVEX-API-v1.yaml`](../INVEX-API-v1.yaml) + per-component
  [`apps/classification/doc/openapi.yaml`](../../apps/classification/doc/openapi.yaml))
  → ADRs (project root + per-component) → conventions
  ([`doc/conventions/python-naming.md`](../conventions/python-naming.md)).
- Shared technical context: [`infra/registry.yaml`](../../infra/registry.yaml)
  (indicator registry, per classification ADR-0002).

### Layer 2 — Cognitive tools (specialised expertise on demand)

The seven skills under [`.claude/skills/`](../../.claude/skills/) —
domain experts (`/trader`, `/statistician`, `/risk-officer`) and
engineering experts (`/chief-architect`, `/architect`,
`/forward-deployed-engineer`, `/adversary`).

**This layer is load-bearing, not a convenience.** Layer 4 below
names an autonomy ceiling: no system of automated oracles can fully
verify itself, so some bug classes are unreachable without external
observers. The skills layer is the architectural answer to that
ceiling, covering the bug classes no automated oracle can reach:
frame-of-reference errors, wrong-level abstractions in novel forms,
anything outside the existing oracle set's mapping.

The skills are operator-invoked via slash commands today. The
execution model below adds harness-surfaced reminders so the operator
knows when a skill review is warranted.

### Layer 3 — Tool permissions (what the agent can do without asking)

- [`.claude/settings.json`](../../.claude/settings.json) — global
  allowlist (pytest, dotnet, git, ruff/mypy invocations, specific
  WebFetch domains).
- [`.claude/settings.local.json`](../../.claude/settings.local.json)
  — local override (~42 specific permissions for active development).
- **Hooks: NOT YET CONFIGURED.** Without these, Layer 4 cannot fire
  automatically. See Execution model below.
- Per ACX-002: the permission set is itself a controlled variable;
  changes require justification.

### Layer 4 — Feedback oracles (how the agent learns it broke something)

Per-component layer. Each component implements feedback oracles sized
to its tech stack and risk profile.

- **Classification service today:** five oracles + G1 health gate, locked in
  [classification ADR-0003](../../apps/classification/doc/adr/0003-test-oracle-architecture.md)
  and inventoried in
  [`apps/classification/HARNESS.md`](../../apps/classification/HARNESS.md).
  The five oracles are: contract shape, anchor scenarios,
  mathematical axioms, structural fitness, and the planned
  reality-derived backtest (Layer A — currently unbuilt).
- **.NET iterations (future):** EVO-001 mandates black-box acceptance
  tests against `INVEX-API-v1.yaml`; iteration-specific structural
  tests (the architecture being measured varies). Each iteration
  adds its own ADR + per-component HARNESS.md.
- **Universal floor for every component:** at minimum a contract
  oracle + an acceptance oracle + a structural-fitness oracle + an
  operational gate. An independent reality-derived oracle is
  *encouraged* — see ceiling below — but not floor-mandated.

#### The autonomy ceiling

--- Clarify ---
No system of automated oracles can fully verify itself. Each oracle
catches a class of bugs based on an assumptions that needs
external validation (window choice, ground-truth source
integrity, normalization, regime-conditioning). This limit is
structural, not a defect to be fixed.

A reality-derived oracle (for classification: Layer A) catches **one
specific Case B sub-class**: calibration mismatch with realized
market behavior. It does not catch:

- Wrong-level abstraction bugs (output is fine; structure is wrong).
  These are caught by Layer 4 fitness functions (import-linter,
  xenon, mypy strict) and `/architect` review.
- Frame-of-reference errors where shared assumptions propagate
  through every oracle, including the reality-derived one.
- Bugs in the reality-derived oracle's own ground truth (wrong
  post-event window, corrupted IV source, regime-misaware bands).
- Novel bug classes outside the reality-derived oracle's mapping.

**Statistical limits of independent reality-derived oracles.** Even
within their target sub-class, these oracles have known limits: small
sample sizes (vol shocks are rare; classification's anchor catalogue
is ~50 events maximum from 2010–2025); confounding events in any
post-event window; regime non-stationarity (a 28% IV move means
different things in different vol regimes); single-event isolation
is hard. Layer A is defensible as a coarse-grained rank-correlation
check across the catalogue ("do high-severity flagged events
systematically have larger post-event IV moves than low-severity
ones?") and as a per-event band-violation check ("is this
severity-IV pairing incompatible with anything we have seen?"). It
is not defensible as a fine-grained continuous-calibration tool. The
band-derivation rule and any regime-conditioning are
quantitative-methods decisions, not architecture decisions; they
require `/trader` + `/statistician` review when the oracle is built.

The architectural commitment is to the **pattern** — an independent
reality-derived oracle as a valid oracle class, when achievable —
not to any specific oracle being sufficient. The skills layer above
remains the answer for everything reality-derived oracles cannot
reach.

### Layer 5 — Decision durability (what persists)

- **ADR discipline** (Nygard format). Architectural decisions live in
  `doc/adr/` at the project root and per-component (e.g.
  `apps/classification/doc/adr/`).
- **`LIMITATIONS.md` per component.** Accepted gaps with rationale
  and the conditions that would re-open the question.
- **`HARNESS.md` per component.** Regenerable runbook inventory of
  every harness layer as it instantiates at that component.
- Git history is the immutable substrate. The harness presumes
  Nygard-format ADRs and meaningful commit messages, but those are
  properties of using git well, not separate mechanisms.

## Execution model — who triggers what, when

The five layers describe what exists. This section describes who
fires what, and when. A harness that requires the operator to
manually run feedback after every agent change is not a harness; it
is a testing technique applied at the agent. The discipline calls
for **agent-triggered or harness-triggered** feedback as the default,
with the operator as the human-in-loop reviewer.

### Three actors

1. **Harness (automated).**
   [`.claude/settings.json`](../../.claude/settings.json) hooks fire
   on well-defined events (PostToolUse, Stop). No human or agent
   action required. Today: zero hooks configured. Target: see
   sequencing below.
2. **Agent (self-disciplined).** Convention encoded in AGENTS.md
   instructs the agent to surface skill recommendations, run
   commands, or open artefacts when specific concrete events occur.
   Agent reads convention; agent applies it; output flags
   recommendations for the operator.
3. **Operator (manual).** Reads agent output before `git commit`. The
   final human-in-loop. Not a designed mechanism — an unavoidable
   property of running a single-operator system.

### Concrete trigger map

Specific file-path and action triggers:

| Trigger (concrete) | What fires | Actor |
| --- | --- | --- |
| Session start | Auto-load AGENTS.md (root) → AGENTS.md (component) → relevant ADRs | Harness (Claude Code auto-discovery — already wired) |
| Tool call | Permission check against `.claude/settings.json` allowlist | Harness (already wired) |
| `Edit/Write` on `apps/*/app/**/*.py` | Targeted `ruff check` + `mypy` on the file | Harness (PostToolUse hook — NOT YET CONFIGURED) |
| `Edit/Write` on `apps/*/tests/acceptance/fixtures/*.json` | Stdout reminder to invoke `/trader` + `/statistician` for band-derivation review | Harness (PostToolUse hook — NOT YET CONFIGURED) |
| `Edit/Write` on a strategy / severity-formula file | Stdout reminder to invoke `/statistician` for formula correctness | Harness (PostToolUse hook — NOT YET CONFIGURED) |
| `Edit/Write` on `app/registry.py` or `infra/registry.yaml` | Stdout reminder to invoke `/trader` + `/risk-officer` | Harness (PostToolUse hook — NOT YET CONFIGURED) |
| New file under any `doc/adr/` | Stdout reminder to invoke `/chief-architect` for ADR review | Harness (PostToolUse hook — NOT YET CONFIGURED) |
| New entry in any `LIMITATIONS.md` | Stdout reminder to invoke `/adversary` to challenge gap acceptance | Harness (PostToolUse hook — NOT YET CONFIGURED) |
| Agent attempts to terminate a turn | `pytest tests/ -x --tb=line` from the affected component | Harness (Stop hook — NOT YET CONFIGURED) |
| Pytest red observed | Steering-loop reasoning protocol (Case A) | Agent reads output; agent classifies per AGENTS.md convention |
| Bug observed despite green pytest (Case B) | Operator or specialist raises issue; ADR or LIMITATIONS entry | External — see ceiling above |
| Pre-commit | Operator reads agent output and final diff | Operator |

### Steering loop — two entry points, not one

**Case A — oracle red.** Pytest output shows a failure. The bug
class is being caught; the failing test is the catch. The agent
reads the failure and classifies:

- Common. The failing test correctly states the requirement and the
  implementation is wrong → fix the implementation. No ADR.
- Rare. The failing test itself encodes a wrong assumption (a
  fixture band copied from broken implementation output rather than
  derived from the SRS) → fix the test as a *harness bug*, not a
  service bug. No ADR if the existing oracle class still applies.

**Case B — oracle escape.** Pytest is green; the bug exists anyway.
Not visible in pytest output, so it can only be entered when a
non-oracle observer raises the issue:

- A specialist skill review (`/trader`, `/statistician`, `/architect`,
  `/adversary`) spots a wrong fixture band, a wrong-level abstraction,
  an axis the oracles don't probe.
- A reality-derived oracle, when built and within its target
  sub-class, flags a calibration drift.
- Code review by the operator notices something the agent missed
  (this is how classification ADR-0001 was discovered).
- Production observation (someone sees a wrong score in the field).

The Case B response is operator-and-agent together, after the issue
is raised:

- Open an ADR and add a new control (test, fitness rule, fixture,
  new oracle layer) in the same PR. The ADR names which oracle class
  catches the failure mode going forward.
- Or, if no control is feasible, add a `LIMITATIONS.md` entry with
  failure mode, rationale, and the conditions that would re-open the
  question.

A bug alone does not warrant an ADR. A bug plus a new control does.
A bug plus an accepted gap is a `LIMITATIONS.md` entry. **Silent
gaps are not a permitted state.**

The agent looking only at green pytest output cannot autonomously
detect Case B. This is the ceiling named in Layer 4.

### Concrete hooks the harness needs (NOT YET BUILT)

These are the hooks the architecture commits to. To be added in
`.claude/settings.json`:

```jsonc
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": {"tool": "Edit|Write", "filePathPattern": "apps/classification/app/.*\\.py"},
        "hooks": [{"type": "command",
                   "command": "cd apps/classification && ruff check ${CLAUDE_FILE_PATH} && mypy ${CLAUDE_FILE_PATH}"}]
      },
      {
        "matcher": {"tool": "Edit|Write",
                    "filePathPattern": "apps/classification/tests/acceptance/fixtures/.*\\.json"},
        "hooks": [{"type": "command",
                   "command": "echo 'FIXTURE CHANGED. Per ANCHORS.md, band must derive from SRS CLS-001 and source values must cite a public provider. Invoke /trader and /statistician for sign-off before claiming complete.'"}]
      }
    ],
    "Stop": [
      {
        "hooks": [{"type": "command",
                   "command": "cd apps/classification && pytest tests/ -x --tb=line"}]
      }
    ]
  }
}
```

### Concrete AGENTS.md conventions (NOT YET WRITTEN)

To be added to project-root and per-component AGENTS.md:

- *When a hook surfaces a skill-invocation reminder, flag it
  explicitly in the end-of-turn output so the operator can decide
  whether to invoke the skill before commit.*
- *Before claiming a code change complete, run the full pytest. If
  red, address it or explicitly hand off to the operator with the
  failure named.*
- *On pytest red (Case A), classify per the steering protocol: fix
  the implementation if the failing test correctly states the
  requirement; flag the test as a harness bug if it encodes a wrong
  assumption.*
- *On a Case B bug raised by an external observer, the response is
  an ADR (with control in the same PR) or a `LIMITATIONS.md` entry
  — never a silent fix.*

### Where the project stands today

- **Layer 1 (context)**: autonomous — auto-discovery loads AGENTS.md
  on session start.
- **Layer 3 (permissions)**: autonomous — settings.json blocks
  unallowlisted calls.
- **Layer 2 (cognitive tools)**: operator-invoked, no convention
  prompting recommendation. The agent does not surface "you should
  invoke /trader here" because no convention tells it to.
- **Layer 4 (feedback oracles)**: operator-manual `pytest`. This is
  the largest gap: a regression reaches `master` if the operator
  forgets to run it.
- **Layer 5 (decision durability)**: operator-prompted. ADRs and
  `LIMITATIONS.md` entries get written when explicitly asked, not
  when the steering loop dictates they should.

### Sequencing to close the gap (this ADR commits to it)

1. **First.** Add the hooks above to `.claude/settings.json`. This
   converts Layer 4 from operator-manual to harness-automated — the
   biggest single autonomy lift. PostToolUse runs targeted lints/types;
   Stop runs full pytest before turn termination.
2. **Second.** Add the AGENTS.md conventions above. This wires the
   agent into the steering loop (Case A reasoning) and into surfacing
   skill-invocation reminders to the operator.
3. **Third.** Add a CI workflow (GitHub Actions) so the harness runs
   even when local hooks are bypassed. Defence in depth, not a
   replacement for hooks.

These three steps are the work this ADR commits to. Subsequent ADRs
may refine hook contents or CI shape; the commitment to autonomous
execution is locked here.

**Acknowledged limit.** Even after all three steps, Case B detection
beyond a reality-derived oracle's reach remains operator-mediated.
That is a property of the discipline, not a gap to close.

## Per-component instantiation rule

For each INVEX component (Python classification today; six .NET
iterations to come), the harness MUST manifest as:

- `AGENTS.md` (Layer 1)
- `LIMITATIONS.md` (Layer 5)
- `HARNESS.md` (Layer 5 — the runbook inventory across all five
  layers as instantiated at that component)
- `doc/adr/` (Layer 5)
- Component-specific feedback infrastructure satisfying the universal
  floor in Layer 4 (contract + acceptance + structural-fitness +
  operational gate).

Skills (Layer 2) and permissions (Layer 3) are project-wide; they
extend per-component via `.claude/settings.local.json` and convention.

## Trade-offs

- **Five layers vs simpler three.** Sacrificed: simplicity. Gained:
  each layer has a named owner-failure-mode pair, and "the harness"
  stops being an ambiguous word.
- **Per-component ADRs vs one big harness ADR.** Sacrificed: single
  source for component-level harness decisions. Gained: component
  ADRs evolve without superseding the project-wide one. Iteration
  churn is contained.
- **Skills as operator-invoked-with-reminders, not agent-autonomous.**
  Sacrificed: forced rigor (the skill always runs). Gained: realism;
  skills are judgment calls, not mechanical checks. Convention
  surfaces the recommendation, the operator chooses. Forcing every
  fixture edit through `/trader` would create alarm fatigue and erode
  the signal.
- **No CI today.** Sacrificed: regression safety net at the network
  boundary. Gained: faster iteration without infrastructure overhead.
  Sequencing step 3 closes this in a follow-up ADR.
- **Architectural commitment to the pattern, not to a specific
  oracle.** Sacrificed: a single concrete promise ("Layer A will
  catch X"). Gained: independent reality-derived oracles catch some
  Case B sub-classes, not all; band-derivation is a
  quantitative-methods decision (`/trader` + `/statistician`), not
  architecture; novel bug classes will require new oracles (future
  ADRs) or specialist review.

## Cost of being wrong

- **Five layers turns out to be four plus one redundant.**
  Reversible: collapse via superseding ADR. Cheap to undo.
- **A sixth layer is needed** (e.g. an *agent reflection* layer
  where the agent self-critiques the diff before turn termination).
  Reversible: add via superseding ADR. Cost: one missed failure
  mode until observed.
- **The trigger map over-prompts the operator.** Every fixture edit
  fires a reminder; alarm fatigue. Mitigation: hooks tunable
  per-path; superseding ADR shrinks the map.
- **The autonomy ceiling is misread as a gap and someone tries to
  close it with more oracles.** Mitigation: this ADR names the
  ceiling explicitly so a future contributor does not propose another
  oracle layer to catch what cannot be caught autonomously.
- **Skills layer is mis-configured (wrong skill list, missing
  domain expertise).** Cost: bug class slips because no skill catches
  it. Reversible: add skill via superseding ADR; the discipline of
  Case B → ADR makes the gap discoverable.

## Out of scope

- **Multi-agent orchestration** (parallel agents collaborating on
  one PR). Not used; not part of the harness today.
- **Agent self-modification of the harness** (an agent editing its
  own AGENTS.md or hooks). ACX-001 forecloses this without operator
  review.
- **Domain-specific harness components for the LLM-judged
  GEOPOLITICAL strategy** (RAG store, prompt versioning). Their
  oracle layer is fundamentally different and warrants a future
  component ADR.
- **AI-judged oracles.** Layer A and other reality-derived oracles
  in this architecture are statistical, not LLM-based. Using an LLM
  to judge correctness would just be another oracle subject to its
  own correlated-error pathology.
- **Coverage-threshold gating.** Coverage is a lagging metric, not a
  fitness function.

## Relationship to other artefacts

- **Component-specific ADRs** (e.g. classification's
  [`0003-test-oracle-architecture.md`](../../apps/classification/doc/adr/0003-test-oracle-architecture.md))
  instantiate Layer 4 for that component. They do not re-decide the
  harness shape — only how that component implements its oracles.
- **`HARNESS.md` per component** is the regenerable inventory of
  every layer at that component. It changes as the inventory
  changes; it does not require an ADR.
- **This ADR** locks the project-wide architecture. Component ADRs
  lock component instantiations. Changing the architecture →
  superseding project ADR. Changing a component's instantiation →
  component ADR. Changing current state → `HARNESS.md` edit, no ADR.

## References

- [`AGENTS.md`](../../AGENTS.md) — project root context
- [`.claude/skills/`](../../.claude/skills/) — Layer 2 cognitive tools
- [`.claude/settings.json`](../../.claude/settings.json) +
  [`settings.local.json`](../../.claude/settings.local.json) — Layer 3
  permissions
- [SRS](../srs/INVEX-SRS.md) — ACX-001, ACX-002, EVO-001 (controlled-
  variable framing)
- [Classification ADR-0001](../../apps/classification/doc/adr/0001-per-indicator-tuning-parameters.md)
  — wrong-level abstraction postmortem
- [Classification ADR-0002](../../apps/classification/doc/adr/0002-ecdf-severity-and-backtest-harness.md)
  — self-validating-loop postmortem and ECDF + Layer A commitment
- [Classification ADR-0003](../../apps/classification/doc/adr/0003-test-oracle-architecture.md)
  — Layer 4 instantiation at the classification service
- ADR format: Michael Nygard, *Documenting Architecture Decisions*
  (2011)
- Anthropic, *Building Effective Agents* (2024)
- Ford / Parsons / Kua, *Building Evolutionary Architectures* (2017)
- Federal Reserve, *SR 11-7: Guidance on Model Risk Management*
  (2011) — independent validation principle
