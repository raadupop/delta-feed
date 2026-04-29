# ADR-0001: Tuning parameters live per-indicator, sourced from the request

- **Status:** Superseded — Decision 2 (parameters travel in the request payload) superseded by [ADR-0002](0002-ecdf-severity-and-backtest-harness.md) Decisions 2 and 3 (registry-governed calibration; request carries indicator identity only). Decisions 1, 3, 4, 5 remain in force.
- **Date:** 2026-04-15
- **Deciders:** Radu Pop
- **Supersedes:** —
- **Superseded by:** ADR-0002 Decision 2 (registry owns expected_frequency_seconds; request payload carries indicator identity only)

## Context

During Phase 4, `_EXPECTED_FREQUENCY_SECONDS` and `_TANH_SCALE` were declared at
module level in `app/strategies/market_data.py` and
`app/strategies/macroeconomic.py`. Both are fundamentally **per-indicator**
properties (VIX trades intraday; CPI releases monthly; INITIAL_CLAIMS weekly),
not per-strategy properties. Encoding them per-strategy is a wrong-level
abstraction.

The defect was structurally invisible to the test suite at discovery time:

- No service-local API contract existed — only prose in `CLAUDE.md`. Nothing
  for tests to agree against independent of the implementation.
- Strategy tests asserted exact `computed_metrics` (`z_score`, `baseline_mean`)
  and so were coupled to the implementation; they could not catch wrong-level
  modeling.
- No structural fitness function enforced where tuning parameters may live.
- **Homogeneous inputs.** Each strategy had exactly one indicator under test
  (`VIX`, `CPI_YOY`). Per-strategy and per-indicator constants produce
  identical outputs when every strategy has only one indicator.
- **Self-validating loop.** The agent wrote both the implementation and the
  tests in one pass, encoding the same wrong assumption in both.

Failure classification: **structural** (wrong-level modeling). Contract and
behavioral tests could not catch it — the input set did not vary along the
axis the bug lives on.

## Decision

1. **Tuning parameters are per-indicator, not per-strategy.** The classifier
   does not own the catalogue of indicators or their cadences.
2. **Parameters travel in the request payload.** The inbound
   `MacroeconomicPayload` (and analogous payloads) carries an
   `indicator_spec` block — `{ id, expected_frequency_seconds, surprise_scale }`
   — set by the .NET ingestion job that owns indicator identity and cadence.
3. **Unknown indicators are first-class at runtime.** The classifier spins up
   a fresh rolling window on first observation of a new `indicator_id` and
   reflects window-emptiness in `temporal_relevance` / `history_sufficiency`.
   No hardcoded `dict[str, IndicatorParams]` in strategy modules.
4. **Shared math is extracted.** `_compute_temporal_relevance` moves to
   `app/math/temporal.py` so both strategies consume one implementation.
5. **The OpenAPI contract** (`doc/openapi.yaml`) declares `indicator_spec` as
   a required sub-schema on the relevant payload variants.

## Harness controls

The harness controls that catch this bug class — the contract layer,
the acceptance suite, and the fitness-function suite — are documented
in [ADR-0003](0003-harness-architecture.md). The accepted-risk waiver
for the two strategy files carrying `_TANH_SCALE` /
`_EXPECTED_FREQUENCY_SECONDS` is a `per-file-ignores` entry in
`pyproject.toml` tagged `# TODO(ADR-0001)`. Phase B removes the ignore
entry and the constants in the same commit.

## Consequences

### Positive

- Adding a new indicator is an upstream schema+config change, not a classifier
  code change. The classifier scales with the .NET-side indicator registry
  without redeploys.
- The fitness suite catches the *class* of bug (wrong-level tuning constant in
  any strategy), not just the specific instance.
- The contract + acceptance layer survives implementation rewrites
  (Phase C: `tanh` → ECDF) without rewriting tests.

### Negative

- The .NET ingestion job now owns the indicator-spec catalogue. The Python
  service trusts caller-supplied params; bad params produce bad scores. This
  is the correct ownership boundary but it shifts validation responsibility
  upstream.
- An unknown indicator at runtime carries low `temporal_relevance` until its
  window fills. Callers must understand that early scores on novel indicators
  are intentionally uncertain.

### Trade-off — what was rejected

A YAML model card / signal-calibration spec with attestation hashes was
considered and rejected as governance theater for a single-operator system.
Routine parameter changes require only that the acceptance suite passes; the
contract is the OpenAPI file, the domain scenarios are `ANCHORS.md`.

## Status of the bug at time of writing

**NOT FIXED.** Accepted-risk waivers in place:

- `pyproject.toml` `[tool.ruff.lint.per-file-ignores]` — `PLR2004` exempted on
  `app/strategies/market_data.py` and `app/strategies/macroeconomic.py`, tagged
  `# TODO(ADR-0001)`.
- `tests/acceptance/fixtures/macro_initial_claims_weekly_surprise_2026_04_09.json` —
  `xfail(strict=True)` marker configured; currently skipped pending `/trader`
  data pull, flips to a live fail once sourced.

Phase B (future ADR) removes the bug at its source — deletes the
`per-file-ignores` entries and the module-level constants in the same commit,
and the INITIAL_CLAIMS anchor flips from xfail to pass.

## References

- Plan: `C:\Users\Radu\.claude\plans\fluttering-sprouting-wreath.md`
- Source lines at time of bug discovery:
  - `apps/classification/app/strategies/market_data.py:20, 24, 27-36`
  - `apps/classification/app/strategies/macroeconomic.py:19, 23, 26-33`
- Harness architecture: [ADR-0003](0003-harness-architecture.md); inferable inventory in [`HARNESS.md`](../../HARNESS.md)
- Contract: `apps/classification/doc/openapi.yaml`
- ADR format: Michael Nygard, *Documenting Architecture Decisions* (2011)
