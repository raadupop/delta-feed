# ADR-0003: Harness architecture for the classification service

- **Status:** Accepted
- **Date:** 2026-05-01
- **Deciders:** Radu Pop
- **Supersedes:** —
- **Relates to:** [ADR-0001](0001-per-indicator-tuning-parameters.md) (wrong-level tuning postmortem), [ADR-0002](0002-ecdf-severity-and-backtest-harness.md) (ECDF severity + registry)

This ADR locks the **harness architecture** for the Python classification
service — the concrete files, tools, and oracles that catch bugs before they
ship. The per-task inferable inventory (file paths, dispositions, current
gaps) lives in [`HARNESS.md`](../../HARNESS.md). This ADR is the durable
decision: what each oracle is, where it lives, what tool runs it, and what
the operator does when it fires.

The classification service is constant infrastructure across all six INVEX
.NET architecture iterations. It is not under measurement. The harness exists
so the service stays a stable dependency under a single-operator regime
where most edits are proposed by AI agents.

## Context

Two failure modes are demonstrated, not hypothetical:

- **Wrong-level abstraction (ADR-0001).** Per-strategy module-level constants
  were structurally invisible to the suite because every strategy had one
  indicator under test. Homogeneous inputs hid per-indicator vs per-strategy
  collapse.
- **Self-validating loop (ADR-0002).** During the four-fixture axis-coverage
  exercise, an agent writing both implementation and expected bands in one
  pass encoded the same wrong assumption in both, and the SRS-anchored
  oracle accepted it.

Common diagnosis: a single oracle is not enough. Bugs that live on an axis
the oracle does not see require a *different* oracle, not more tests of the
same kind.

Forward-deployed constraints shape the response:

- **Single operator.** Any control that depends on social process (review
  board, separate QA team) is already failed. Controls must be executable.
- **AI-mediated edits.** The harness is what stops correlated agent errors.
  It cannot rely on the operator catching what the agent missed.
- **Iteration-stable contract.** The classifier must not change shape every
  time a .NET iteration begins; the contract layer makes iteration churn
  safe.

## Decision

The harness is **five oracle classes** plus **one operational gate**, all
runnable today by typing `pytest` from `apps/classification/` (gate excepted
— it runs in production). Each oracle has a distinct file location, a
distinct tool, and a distinct oracle source. None is redundant.

### Oracle 1 — Contract shape

- **What it is.** Schema validation of every `/classify` and `/health`
  response against the OpenAPI 3.1 contract.
- **Where it lives.** [`tests/acceptance/test_contract_shapes.py`](../../tests/acceptance/test_contract_shapes.py)
  (7 tests).
- **Tool.** `jsonschema` (Draft 2020-12), wrapped as plain pytest.
- **Oracle source.** [`doc/openapi.yaml`](../openapi.yaml) — normative.
  Prose elsewhere is informative.
- **What the operator sees on failure.** A `jsonschema.ValidationError` in
  pytest output naming the offending JSON path and the violated schema
  rule.
- **Operator action.** Either fix the response shape or update
  `openapi.yaml` *and* the .NET caller's contract in lockstep. A
  contract-shape failure is never fixed by changing only the test.
- **Bug class caught.** Contract drift between .NET caller and classifier.

### Oracle 2 — Anchor scenarios

- **What it is.** Black-box replay of trader-curated historical events with
  expected severity bands derived from the SRS formula.
- **Where it lives.** [`tests/acceptance/test_anchor_events.py`](../../tests/acceptance/test_anchor_events.py)
  (11 parametrised tests over JSON fixtures in
  [`tests/acceptance/fixtures/`](../../tests/acceptance/fixtures/)).
- **Tool.** Plain pytest parametrize over JSON files; `app.state.windows`
  seeded via `tests/acceptance/conftest.py` fixtures.
- **Oracle source.** Each fixture carries
  `expected_band: { expected_score_signed, score_tolerance,
  temporal_relevance_min, sign_convention_check, rationale_pending_trader }`
  alongside `source: { provider, series_id, retrieved_at, url }` and the
  `srs_version` it was derived under. The band-derivation rule in
  [`tests/acceptance/fixtures/ANCHORS.md`](../../tests/acceptance/fixtures/ANCHORS.md)
  is strict on two points: **bands derive from the SRS formula, not from
  current implementation output** (do not adjust a band to make a test
  green — fix the implementation), and **every value cites a public
  provider** (FRED / BLS / Twelve Data / Finnhub / Bloomberg-consensus /
  Reuters-poll, with `series_id`, `retrieved_at` ISO timestamp, and URL).
  No interpolation.
- **What the operator sees on failure.** A pytest assertion of the form
  `expected score in [a, b], got x` with the fixture filename in the test
  ID.
- **Operator action.** If the implementation drifted, fix it. If a new
  variant slipped past existing anchors, author a new fixture under
  `fixtures/` with full provenance and add it to `ANCHORS.md`.
- **Bug class caught.** Formula misimplementation against named historical
  events.

### Oracle 3 — Mathematical axioms

- **What it is.** Universally-quantified properties of CLS-001 that must
  hold for *all* inputs satisfying the precondition, not just specific
  events.
- **Where it lives.** [`tests/acceptance/test_signed_score_axioms.py`](../../tests/acceptance/test_signed_score_axioms.py)
  (7 tests).
- **Tool.** Plain pytest with synthetic windows; no fuzzing library —
  axioms are stated as concrete assertions over hand-chosen
  representatives of each precondition class.
- **Oracle source.** SRS §3 / CLS-001 sign convention, monotonicity, and
  zero-deviation behaviour; CLS-009 parametric-fallback gate.
- **What the operator sees on failure.** A pytest assertion naming the
  axiom (e.g. `test_vol_compression_returns_negative_score`,
  `test_zero_deviation_returns_near_zero_score`,
  `test_parametric_gate_failure_returns_degraded_certainty`).
- **Operator action.** Fix the implementation. An axiom failure means the
  formula is wrong for an entire class of inputs, not just one event;
  anchors alone cannot reach this.
- **Bug class caught.** Sign-convention violation, monotonicity break,
  zero-point drift, parametric-fallback regression. Demonstrated live
  during the signed-score migration — the canonical example of a bug
  that anchors miss and axioms catch.

### Oracle 4 — Structural fitness

- **What it is.** Architectural invariants asserted as pytest tests by
  subprocess-invoking five external tools.
- **Where it lives.** [`tests/architecture/`](../../tests/architecture/)
  — four files, one tool per file.
- **Tools and exact configuration** (all in `pyproject.toml`):
  - `test_typing.py` → `mypy --config-file pyproject.toml app`. `[tool.mypy]`
    sets `python_version = "3.11"`, `strict = true` on `app/models`,
    `app/routing`, `app/strategies`. Other modules tracked at default
    strictness.
  - `test_complexity.py` → `xenon --max-absolute B --max-modules B
    --max-average A app`.
  - `test_code_hygiene.py` → `ruff check --output-format=json app`.
    `[tool.ruff.lint]` enables `E, F, I, B, SIM, C90, PLR`; McCabe
    ceiling is 10; documented per-file-ignores carry ADR cross-references.
  - `test_dead_code.py` → `vulture app --min-confidence 80`, with
    `tests/fixtures` excluded and FastAPI / pytest decorators in the
    ignore list.
  - `import-linter` contracts under `[tool.importlinter]`: four
    peer-to-peer forbidden contracts (each strategy may not import any
    other strategy — MARKET_DATA, MACROECONOMIC, CROSS_ASSET,
    GEOPOLITICAL); a "models pure" contract forbidding
    strategies/routing/state/config imports from `app/models`; a layered
    contract `routing > strategies > math > state/config >
    registry/models`.
- **Oracle source.** The configurations themselves — first-class tests,
  not a separate pipeline (Ford / Parsons / Kua, *Building Evolutionary
  Architectures*, 2017).
- **What the operator sees on failure.** Tool stdout captured into the
  pytest assertion (mypy error list, xenon offender list, ruff JSON,
  vulture confidence-tagged finding, import-linter contract name).
- **Operator action.** Either fix the structural drift or, if the
  violation is intentionally accepted (the ADR-0001 `_TANH_SCALE`
  per-file-ignore is the precedent), tag the waiver `# TODO(ADR-NNNN)`
  with a superseding ADR opened in the same change. Untracked waivers
  are not allowed.
- **Bug classes caught.** Wrong-level abstraction, layer-boundary
  violations, complexity blow-ups, type-erasure regressions, dead code,
  cross-strategy coupling.

### Oracle 5 — Backtest Layer A (market-IV reality)

- **What it is.** Independent reality oracle. For each historical event
  in a curated set, the realised IV path in the 24–48 h post-event
  window is checked against the severity the classifier emitted —
  e.g. *"IV moved > 20 % in the next 48 h after event E → severity must
  be in band [0.7, 1.0]"*.
- **Where it lives.** **Nowhere yet. NOT BUILT.** No
  `tests/backtest/`, no `app/backtest/`, no scaffolding. The intended
  location is `tests/backtest/` with provider-traced post-event IV
  series alongside each anchor.
- **Tool.** TBD at build time. Likely plain pytest with a separate data
  ingest path and a pytest marker (`@pytest.mark.backtest`) so it does
  not run in the per-commit loop.
- **Oracle source.** Realised IV outcome from the same providers as
  anchors (Twelve Data, Finnhub historical OHLC for `^VIX`, `^OVX`),
  *not* the SRS formula. This independence is the entire point.
- **Cadence.** Nightly / pre-release, not per-commit.
- **What the operator sees on failure** (when built). An assertion of the
  form `event E: classifier emitted severity s, realised IV moved x %
  in next 48 h → expected severity in [a, b], FAIL`.
- **Operator action.** Diagnose calibration drift versus regime change;
  the response is not always *"fix the code"* — sometimes it is *"the
  market regime moved and the registry `N_L` needs review"*.
- **Bug class caught.** Calibration plausible-on-paper-but-wrong-against-
  the-market; self-validating loop where SRS and implementation are
  coherent with each other and incoherent with reality.
- **Why named here while unbuilt.** The self-validating-loop class is the
  originating motivation for this ADR. Naming it without building it
  forecloses the *we'll add the test eventually* drift; the harness has
  a known hole, named explicitly, tracked in HARNESS.md and
  LIMITATIONS.md until built.

### Operational gate G1 — `/health`

- **What it is.** A readiness probe that prevents traffic from hitting an
  uncalibrated classifier.
- **Where it lives.** [`main.py`](../../main.py) lines 89–103.
- **Behaviour.** While the FastAPI lifespan runs `populate_windows()`,
  `/health` returns `503 {status: "not_ready"}`. Once `state.is_ready`
  flips, `/health` returns `200 {status: "ready", windows: { "<source>/<symbol>":
  { indicator_class, values_count, last_update, staleness_seconds } }}`.
- **Tested by.** [`tests/acceptance/test_health_acceptance.py`](../../tests/acceptance/test_health_acceptance.py)
  (2 tests).
- **What the .NET caller does.** Gates ingestion on the 503 → 200
  transition. No `/classify` call before ready.
- **Bug classes caught.** Pre-bootstrap traffic; silent serving against
  a degenerate (empty / shallow) window.

### Build status

| # | Oracle / gate | Status | Live red-test gaps |
| --- | --- | --- | --- |
| 1 | Contract shape | BUILT | — |
| 2 | Anchor scenarios | BUILT | `market_data_vix_low_vol_regime_2017_10_05`, `market_data_vix_normal_day_2019_07_15` (long-horizon ECDF migration) |
| 3 | Mathematical axioms | BUILT | `test_vol_compression_returns_negative_score`, `test_zero_deviation_returns_near_zero_score`, `test_parametric_gate_failure_returns_degraded_certainty` (signed-score migration) |
| 4 | Structural fitness | BUILT | — (with documented `# TODO(ADR-0001)` waiver) |
| 5 | Backtest Layer A | **NOT BUILT** | All — no scaffolding exists |
| G1 | `/health` gate | BUILT | — |

The signed-score and long-horizon-ECDF reds in oracles 2 and 3 are
expected during the in-flight migration; they are the harness working as
designed, not harness defects.

## How to run the harness

From `apps/classification/`:

```text
pytest                       # oracles 1–4 + G1 gate test (31 tests: 7 + 11 + 7 + 4 + 2)
FRED_API_KEY=… pytest tests/integration/test_bootstrap.py
                             # live-API bootstrap, skipped by default
# Layer A — NOT BUILT
```

There is no `.pre-commit-config.yaml`, no `.github/workflows/`, no
`Makefile` in this app today. Invocation is manual `pytest`. **This is a
named gap**: a regression can reach `master` if the operator forgets to
run `pytest` between edit and commit. Closing this gap (pre-commit hook
or CI workflow) is a future ADR — adding CI is a control change, not an
inventory update.

## Steering loop — concrete

Three cases. Every escaped bug must terminate in exactly one of them:

1. **Caught by the responsible oracle (the common case).** Fix the bug
   and add a regression case in the same commit *if and only if* the
   existing oracle did not cover the variant. No ADR. Example: a new
   anchor variant that the existing 11-fixture set didn't reach lands as
   a new JSON file under `fixtures/` plus an `ANCHORS.md` entry, in the
   same PR as the implementation fix.

2. **Escaped all five oracles, new control needed.** Open
   `doc/adr/NNNN-*.md` (Nygard format). Required sections: Status,
   Context (including how the bug slipped through), Decision (which
   oracle catches the failure mode going forward), Consequences,
   References. The new control lands in the same PR. Precedent:
   ADR-0001 → fitness layer; ADR-0002 → ECDF formula plus the
   commitment to Layer A.

3. **Escaped all five oracles, accepted gap.** Add an entry to
   [`LIMITATIONS.md`](../../LIMITATIONS.md) with failure mode,
   rationale, and the conditions that would re-open the question.
   Precedent: LIMITATIONS §5 records the self-validating-loop class as
   accepted-pending Layer A.

**ADR ⇔ architectural decision.** Bug ⇏ ADR. Bug + new control = ADR.
Bug + accepted gap = LIMITATIONS entry. A silent gap is not a permitted
state.

## Trade-offs

- **Five oracles, not three.** Sacrificed: a single uniform "acceptance
  suite". Gained: each oracle catches a distinct bug class with a
  distinct oracle source, and a failing test points at the failure mode
  without diagnostic effort. The marginal cost of a fifth pytest file is
  negligible against the cost of a miscategorised failure.
- **Contract = OpenAPI, not a parallel calibration spec.** Sacrificed:
  attestation hashes / model-card YAML. Gained: one shared artefact
  between .NET and Python; calibration drift is caught by Layer A, not
  by spec attestation. Governance theatre rejected for a single-operator
  system (ADR-0001 precedent).
- **Layer A nightly, not per-commit.** Sacrificed: catching calibration
  regressions within seconds. Gained: per-commit feedback under 30
  seconds, which is the realistic ceiling for an operator iterating
  with an agent.
- **Axioms hand-rolled, not Hypothesis.** Sacrificed: random fuzzing
  coverage. Gained: deterministic CI, no flake budget, no shrinker
  diagnostics to read. Reconsider when a hand-rolled axiom misses a
  variant a fuzzer would have found.
- **No coverage threshold.** Sacrificed: a familiar lagging metric.
  Gained: avoids the failure mode where coverage gaming substitutes for
  assertion quality. `mypy --strict`, `xenon B/B/A`, and import-linter
  contracts are the structural floor.

### Dissenting view

The strongest case against this design is *"five oracles plus a not-yet-
built Layer A is over-instrumented for a single operator; ship with
contract + anchor + fitness and add the rest if a bug demonstrates the
need."* Rejected on evidence: ADR-0001 and ADR-0002 already span four
oracle classes between them, the signed-score migration produced live
axiom-oracle failures, and Layer A is the only structural answer to the
self-validating-loop class. Naming Layer A while unbuilt is the
commitment that the operator does not rely on the spec-derived family
alone.

## Out of scope (by design)

- **Parallel domain-spec YAML** with attestations, hash-linkage sensors,
  model cards. The contract is `openapi.yaml`; domain scenarios are
  anchor fixtures.
- **Service-layer metamorphic tests.** Deferred to the math-library
  layer if and when one is extracted under `app/math/`.
- **Mutation testing in the per-commit loop.** A nightly
  `mutmut`-on-`app/strategies/*` sensor-of-sensors is a candidate future
  control; not part of the locked architecture today.
- **Coverage-threshold gating.** See trade-offs.
- **.NET-side harness.** Separate concern, governed by EVO-001.
- **Property-based testing at the service boundary.** Deferred until a
  hand-rolled axiom is shown to miss a variant a fuzzer would catch.

## Cost of being wrong

If this architecture is wrong:

- **Five oracles turn out to be three plus two redundant ones.** Minor
  maintenance overhead. Reversible: collapse two pytest files into one
  in a follow-up ADR. Cheap to undo.
- **A sixth oracle class is needed.** A bug class slips through until
  observed in production. Mitigation: the steering loop turns the
  observation into a superseding ADR. Reversible at the cost of one
  production incident.
- **Layer A's market-IV oracle is methodologically flawed (e.g.
  windowing produces false positives at regime transitions).** False
  alarms erode operator trust in the suite — the worst long-term
  failure mode of any harness. Mitigation: the band-derivation rule
  must be reviewed before Layer A goes live, with the same
  source-provenance discipline ANCHORS.md applies to anchor fixtures.

The architecture is **expensive to get egregiously wrong** (operator
trust) and **cheap to refine at the margin** (add or remove an oracle
via superseding ADR). This justifies committing to the five-oracle
shape now rather than deferring.

## Relationship to HARNESS.md

[`HARNESS.md`](../../HARNESS.md) is the **inferable per-task inventory**:
file paths, current dispositions, layer map, test inventory, the running
gap list. It is regenerable from this ADR plus the state of the repo.

This ADR is the **locked decision**: the five oracles, the operational
gate, the steering loop. Changing the harness shape requires a
superseding ADR; updating the inventory does not.

## References

- [`HARNESS.md`](../../HARNESS.md) — inferable inventory and gap map
- [ADR-0001](0001-per-indicator-tuning-parameters.md) — wrong-level tuning postmortem
- [ADR-0002](0002-ecdf-severity-and-backtest-harness.md) — ECDF severity + registry postmortem
- [SRS](../../../../doc/srs/INVEX-SRS.md) — requirements (CLS-001, CLS-002, CLS-006, CLS-009, EXT-004, §11 acceptance criteria)
- [`apps/classification/doc/openapi.yaml`](../openapi.yaml) — contract
- [`tests/acceptance/fixtures/ANCHORS.md`](../../tests/acceptance/fixtures/ANCHORS.md) — anchor catalogue and band-derivation rule
- [`LIMITATIONS.md`](../../LIMITATIONS.md) — accepted-gap register
- ADR format: Michael Nygard, *Documenting Architecture Decisions* (2011)
- Ford / Parsons / Kua, *Building Evolutionary Architectures* (2017)
- Paul / Ford, *Software Architecture Metrics* (2022)
- Federal Reserve, *SR 11-7: Guidance on Model Risk Management* (2011)
