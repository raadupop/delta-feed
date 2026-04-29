# ADR-0003: Three-layer harness architecture for the classification service

- **Status:** Accepted
- **Date:** 2026-04-30
- **Deciders:** Radu Pop
- **Supersedes:** —
- **Relates to:** [ADR-0001](0001-per-indicator-tuning-parameters.md) (postmortem — wrong-level tuning), [ADR-0002](0002-ecdf-severity-and-backtest-harness.md) (postmortem — ECDF severity + registry)

This ADR locks the **harness architecture** for the Python
classification service. The inferable per-task framework view lives in
[`HARNESS.md`](../../HARNESS.md); this ADR is the durable architectural
decision, capturing why the harness has the shape it has and what
property of bug-class coverage it is committed to.

The classification service is constant infrastructure across all six
INVEX .NET architecture iterations. It is not under measurement. The
harness exists so the service stays a stable dependency.

## Context

Two concrete bug discoveries during Phases 4–5 (see ADR-0001, ADR-0002)
established a class of failure that the original test suite could not
catch:

- **Wrong-level tuning constants.** Per-strategy module-level constants
  (`_TANH_SCALE`, `_EXPECTED_FREQUENCY_SECONDS`) were structurally
  invisible to acceptance tests because every strategy under test had
  exactly one indicator — homogeneous inputs hide per-indicator vs
  per-strategy collapse.
- **Self-validating-loop.** The four-fixture axis-coverage exercise
  (OVX Aramco, VIX COVID mid-crisis, VIX vol crush, VIX normal day)
  showed that an agent writing both the implementation and the tests in
  one pass can encode the same wrong assumption in both, and the
  acceptance suite — whose oracle is the SRS contract — passes
  trivially.

The diagnosis common to both: **a single oracle is not enough**. Bugs
that live on an axis the oracle does not see cannot be caught by adding
more tests of the same kind. They require a different oracle.

External framings used to size and name the controls:

- *Building Evolutionary Architectures* (Ford / Parsons / Kua, 2017) and
  *Software Architecture Metrics* (Paul / Ford, 2022) — fitness functions
  as continuous, executable assertions on architectural invariants,
  first-class tests rather than a separate pipeline.
- Pact / Ian Robinson — consumer-driven contracts as the
  machine-readable spec of observable behavior.
- xUnit replay / quant-shop "golden runs" (Meszaros lineage) — black-box
  replay of named historical scenarios.
- Federal Reserve **SR 11-7 §V** — independent implementation and
  ongoing monitoring for the model dimension (severity / certainty
  outputs). Applies in spirit even though INVEX is not a bank.

## Decision

The classification service harness consists of **three durable controls**
materialised as **three test layers with distinct oracles**.

### Three durable controls

1. **Contract-first.** A machine-readable spec of observable behavior
   ([`apps/classification/doc/openapi.yaml`](../openapi.yaml), OpenAPI
   3.1). The contract is normative; prose elsewhere is informative.
2. **Behavioral tests against named reference scenarios.** Black-box
   replay of trader-curated historical events from
   [`tests/acceptance/fixtures/ANCHORS.md`](../../tests/acceptance/fixtures/ANCHORS.md).
   Source-provenance is strict: every fixture value must trace to a
   verifiable public provider.
3. **Fitness functions on code structure.** Continuous, executable
   assertions about layering, complexity, typing, hygiene, and dead
   code, configured in `pyproject.toml` and wrapped as pytest tests.

### Three test layers with distinct oracles

| Layer | Oracle | Granularity | Cadence | Bug classes caught |
|---|---|---|---|---|
| **Acceptance** | SRS contract + CLS-001 ECDF formula | Per-request, deterministic | Per-commit | Formula misimplementation; contract violations; anchor-band regressions |
| **Architecture (fitness)** | Structural invariants (layering, complexity, typing, hygiene, dead code) | Per-file / per-rule | Per-commit | Wrong-level abstraction; boundary violations; McCabe blow-ups; import drift |
| **Backtest Layer A** | Market-IV outcomes — *"IV moved > 20% in the 48 h after event X → severity must be ≥ 0.7"* | Per-event, historical | Nightly / pre-release | Self-validating-loop at the severity layer; calibration drift across regimes; ECDF-formula-plausible-but-wrong-in-reality |

All three layers run as pytest. Fitness functions are first-class
tests, not a separate pipeline.

**Why three layers, not two.** Acceptance and Architecture share the
SRS / structural-invariant family of oracles. If the SRS and the
implementation co-evolve from the same wrong assumption, both pass
while the product is broken. Layer A's oracle is external — what IV
actually did — so it catches that exact co-evolution failure mode.
Different oracle, different bug class, no duplication.

**Layer B (system backtest, .NET replay of the SRS validation event
set)** is noted for completeness; scaffolding waits until the .NET
iterations exist.

### Steering loop

Every caught bug:

1. Classify the failure: contract? behavioral? structural?
2. Open a new ADR under `doc/adr/NNNN-*.md` (Nygard format). Required
   sections: Status, Context (including how the bug slipped through),
   Decision, Consequences, References. Bug status (FIXED / NOT FIXED
   with explicit accepted-risk note) belongs in the Status block.
3. Add the control of the right type. An ADR without a new control or
   an explicit accepted-risk acknowledgment is not allowed.

## Consequences

### Positive

- The harness catches *classes* of bugs, not just instances. The
  acceptance + architecture + Layer A composition is committed to the
  three failure modes above; new bugs that fall in those classes have
  a designated layer to be caught at, not an ad-hoc test wedged in
  somewhere.
- The contract + acceptance layer survives implementation rewrites
  (e.g. `tanh` → ECDF, scalar → signed score) without rewriting tests
  — bands derive from the SRS formula, not from the current
  implementation output.
- Fitness functions enforce architectural invariants continuously,
  removing the "we'll review for that in PR" failure mode.
- The steering loop institutionalises the postmortem-as-control
  discipline: an unfixed bug must explicitly carry an accepted-risk
  note, not silently disappear.

### Negative / cost

- Three layers is more maintenance surface than two. The Layer A
  backtest in particular requires per-event provenance discipline
  (FRED / BLS / Twelve Data / Finnhub / Reuters / Bloomberg consensus
  archive) and a band-derivation rule strict enough to survive review.
- ADR-0003 freezes the harness shape. Adding a fourth oracle (e.g. a
  property-based mathematical-invariants layer on `app/math/`) is a
  superseding ADR, not a quiet expansion.
- The SR 11-7 framing is invoked but not fully implemented — INVEX is
  not a bank and the operator runs "independent monitoring" alone.
  Documented gap, not a hidden one.

### Out of scope (by design)

- **Parallel domain-spec YAML** (e.g. `signal-calibration.yaml`, model
  cards with attestations, hash-linkage sensors). The contract lives in
  `openapi.yaml`; domain scenarios live in `ANCHORS.md`. Routine
  parameter changes require only that the acceptance suite passes.
- **Metamorphic tests at the service layer.** Unnecessary once anchors
  cover the axes of variation. Metamorphic relations remain useful at
  the math-library layer (deferred).
- **.NET-side harness.** Separate concern, governed by EVO-001 on that
  side.
- **Coverage-threshold gating.** Coverage is a lagging metric, not a
  fitness function. `mypy --strict` and complexity ceilings are in
  scope; line-coverage thresholds are not.

### Relationship to HARNESS.md

[`HARNESS.md`](../../HARNESS.md) is the **inferable per-task inventory**:
the file inventory, the layer map, the test inventory and disposition,
the running list of remaining gaps. It is regenerable from this ADR
plus the current state of the repo.

This ADR is the **locked decision**: the three controls, the three
layers, the three oracle classes, and the steering-loop discipline.
Changing the harness shape requires a superseding ADR; updating the
inventory does not.

## References

- [`HARNESS.md`](../../HARNESS.md) — inferable inventory and gap map
- [ADR-0001](0001-per-indicator-tuning-parameters.md) — wrong-level tuning postmortem
- [ADR-0002](0002-ecdf-severity-and-backtest-harness.md) — ECDF severity + registry postmortem
- [SRS](../../../../doc/srs/INVEX-SRS.md) — requirements (CLS-001, CLS-009, §11 acceptance criteria)
- [`apps/classification/doc/openapi.yaml`](../openapi.yaml) — contract
- [`tests/acceptance/fixtures/ANCHORS.md`](../../tests/acceptance/fixtures/ANCHORS.md) — anchor catalogue and band-derivation rule
- ADR format: Michael Nygard, *Documenting Architecture Decisions* (2011)
- Ford / Parsons / Kua, *Building Evolutionary Architectures* (2017)
- Paul / Ford, *Software Architecture Metrics* (2022)
- Federal Reserve, *SR 11-7: Guidance on Model Risk Management* (2011)
