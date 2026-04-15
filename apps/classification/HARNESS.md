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
| `tests/regression/test_market_data.py`, `test_macroeconomic_data.py` | Strategy-level (asserts exact `computed_metrics`) with fixtures under `tests/regression/fixtures/` | Kept as a regression suite for the current implementation. Will correctly fail when Phase C swaps `tanh` for ECDF. NOT promoted to acceptance. |
| `tests/integration/test_bootstrap.py` | Live-API bootstrap | Separate category; skipped when `FRED_API_KEY` is absent. |

## 4. Gaps After Phase A

- **Per-indicator axis coverage** — MACROECONOMIC anchors today cover only
  `CPI_YOY`. Phase A invokes `/trader` to add at least one non-monthly
  indicator anchor (e.g. `INITIAL_CLAIMS` weekly) so the homogeneity trap
  that hid Lesson 1 cannot reappear silently.
- **GEOPOLITICAL and CROSS_ASSET_FLOW anchors** — deferred until those
  strategies are implemented (still scaffolds today).
- **Property-based tests on `_compute_temporal_relevance`** — deferred to
  Phase C after the function is extracted to `app/math/temporal.py`.
  Hypothesis-style tests are cheap and well-justified at the math layer.
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
