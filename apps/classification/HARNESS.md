# HARNESS — Classification Service

Framework, inventory, and gap map for the harness that steers the Python
classification service. Architectural decisions and postmortem-style entries
for caught bugs live as ADRs under `doc/adr/` (Michael Nygard format).

This service is constant infrastructure across all six INVEX .NET
architecture iterations. It is NOT under measurement. The harness described
here exists so the service stays a stable dependency for experiments on the
.NET side.

## 1. Framework — Three Durable Controls

Bridging an SRS to a running implementation requires three complementary
controls. Lineage:

- **Contract-first** — machine-readable spec of observable behavior.
  Sources: OpenAPI 3.1; Ian Robinson / Pact consumer-driven contracts.
- **Behavioral tests against named reference scenarios** — black-box replay
  of real historical inputs.
  Sources: quant-shop "golden runs"; xUnit replay pattern (Meszaros).
- **Fitness functions on code structure** — continuous, executable
  assertions about architectural invariants.
  Sources: Ford/Parsons/Kua, *Building Evolutionary Architectures* (2017);
  Paul/Ford, *Software Architecture Metrics* (2022); ArchUnit → import-linter
  (Seddon).

Fed SR 11-7 §V framing applies to the model dimension (severity/certainty
outputs) even though we are not a bank: independent implementation and
ongoing monitoring.

Martin Fowler's April 2026 "Agent Harness" framing (Agent = Model + Harness,
Guides × Sensors × Computational × Inferential) maps cleanly onto the three
controls above: contract = computational guide, acceptance tests =
computational sensor, fitness functions = computational guide on code
structure.

## 2. Layer Map

| Layer | Artifact |
| --- | --- |
| Contract (authoritative) | `apps/classification/doc/openapi.yaml` |
| Contract-shape tests | `tests/acceptance/test_contract_shapes.py` |
| Reference-scenario tests | `tests/acceptance/test_anchor_events.py` + `tests/acceptance/fixtures/ANCHORS.md` |
| Health acceptance | `tests/acceptance/test_health_acceptance.py` |
| Structural fitness | `tests/architecture/test_layering.py`, `test_code_smells.py`, `test_complexity.py`, `test_typing.py`, `test_dead_code.py` |
| Tooling config (fitness) | `pyproject.toml` — `[tool.ruff]`, `[tool.mypy]`, `[tool.importlinter]`, `[tool.xenon]`, `[tool.vulture]` |

All fitness tests are wired as pytest — same `pytest` run executes acceptance
and fitness. Ford/Parsons/Kua: "fitness functions are first-class tests, not
a separate pipeline."

## 3. Test Inventory & Disposition

| File | Kind | Disposition |
| --- | --- | --- |
| `tests/acceptance/` | Black-box against the contract (`test_contract_shapes.py`, `test_anchor_events.py`, `test_health_acceptance.py`) + `fixtures/` with `ANCHORS.md` | New in Phase A. Authoritative layer. |
| `tests/architecture/` | Fitness functions wrapping `import-linter`, `ruff`, `mypy`, `xenon`, `vulture` | New in Phase A. |
| `tests/integration/test_bootstrap.py` | Live-API bootstrap | Separate category; skipped when `FRED_API_KEY` is absent. |

## 4. Test Model — Three Layers with Distinct Oracles

The four-fixture axis-coverage work (OVX Aramco, VIX COVID mid-crisis, VIX
vol crush, VIX normal day) surfaced a structural gap: the acceptance
suite cannot catch a class of AI-generated bugs in which the strategy
and its tests co-evolve from the same wrong assumption. The remediation
is a **third harness layer** with a different oracle, scoped in
[ADR-0002](doc/adr/0002-ecdf-severity-and-backtest-harness.md).

| Layer | Oracle | Granularity | Cadence | Bug classes caught |
| --- | --- | --- | --- | --- |
| **Acceptance** | SRS contract + CLS-001 ECDF formula (see [annex stub](doc/adr/srs-annex-cls-001-severity-formula.md)) | Per-request, deterministic | Per-commit | Formula misimplementation; contract violations; anchor-band regressions |
| **Architecture (fitness)** | Structural invariants (layering, complexity, typing, hygiene, dead code) | Per-file / per-rule | Per-commit | Wrong-level abstraction; boundary violations; McCabe blow-ups; import drift |
| **Backtest Layer A** | Market IV outcomes — binary direction + magnitude bucket (*"IV moved > 20% post-event → severity ≥ 0.7 must hold"*) | Per-event, historical | Nightly / pre-release | Self-validating-loop at the severity layer; calibration drift across regimes; ECDF-formula-plausible-but-wrong-in-reality |

Layer A is Python-only and buildable today. A future Layer B
(.NET-side system backtest against SRS §9's 10-event validation set)
waits until the .NET iterations exist.

### Why three layers, not two

Acceptance uses the SRS contract as its oracle. If the SRS and the
implementation co-evolve from the same wrong assumption, acceptance
passes while the product is broken. Layer A's oracle is external —
what IV actually did — so it catches that exact co-evolution failure
mode. Different oracle, different bug class, no duplication.

### Remaining gaps after this harness redesign

- **ECDF implementation** — the CLS-001 annex is a stub; strategy code
  still uses `tanh`. `/chief-architect` engagement scheduled.
- **CROSS_ASSET_FLOW anchors** — deferred until the strategy is
  implemented (build-step 5), which will land directly on ECDF.
- **GEOPOLITICAL anchors** — deferred until those strategies exist;
  EVENT_ASSESSMENT via LLM, not covered by ECDF.
- **Property-based tests on `_compute_temporal_relevance`** — deferred
  to Phase C after the function is extracted to `app/math/temporal.py`.
- **Mutation testing (mutmut)** — Phase C sensor-of-sensors on
  `app/strategies/*.py` and `app/math/*.py`.

## 5. Steering Loop

Every caught bug:

1. Classify the failure: contract? behavioral? structural?
2. Open a new ADR under `doc/adr/NNNN-*.md` (Nygard format). Required
   sections: Status, Context (including how the bug slipped through),
   Decision, Consequences, References. Bug status (FIXED / NOT FIXED with
   explicit accepted-risk note) belongs in the ADR's Status block.
3. Add the control of the right type. An ADR without a new control or an
   explicit accepted-risk acknowledgment is not allowed.

## 6. Out of Scope (by design)

- **Parallel domain-spec YAML** (e.g. `signal-calibration.yaml`, model cards
  with attestations, hash-linkage sensors). The contract lives in
  `openapi.yaml`; domain scenarios live in `ANCHORS.md`. Routine parameter
  changes require only that the acceptance suite passes.
- **Metamorphic tests at the service layer** — unnecessary once anchors
  cover the axes of variation. Metamorphic relations remain useful at the
  math library layer (Phase C).
- **.NET-side harness** — separate concern, governed by EVO-001 on that side.
- **Coverage-threshold gating** — coverage is a lagging metric, not a
  fitness function. `mypy --strict` and complexity ceilings are in scope;
  they belong to the fitness suite above.
