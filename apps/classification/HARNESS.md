# HARNESS — Classification Service

**Inferable inventory** of the harness that steers the Python
classification service: file paths, current dispositions, current
gaps, and the response protocol when an oracle fires. The locked
architectural decision (the five oracle classes, the operational
`/health` gate, the steering loop, the out-of-scope list) lives in
[ADR-0003](doc/adr/0003-harness-architecture.md). This file is
regenerable from that ADR plus the current state of the repo.

This service is constant infrastructure across all six INVEX .NET
architecture iterations. It is not under measurement.

## Layer map

The five oracles plus the operational gate, keyed to the ADR-0003 vocabulary:

| # | Oracle / gate | Artefact(s) | Oracle source |
| --- | --- | --- | --- |
| 1 | Contract shape | `tests/acceptance/test_contract_shapes.py` | [`doc/openapi.yaml`](doc/openapi.yaml) |
| 2 | Anchor scenarios | `tests/acceptance/test_anchor_events.py` + [`tests/acceptance/fixtures/`](tests/acceptance/fixtures/) + [`ANCHORS.md`](tests/acceptance/fixtures/ANCHORS.md) | Trader-curated historical events; bands derived from SRS CLS-001 |
| 3 | Mathematical axioms | `tests/acceptance/test_signed_score_axioms.py` | SRS §3 / CLS-001 sign convention, monotonicity, zero-deviation; CLS-009 parametric gate |
| 4 | Structural fitness | `tests/architecture/test_typing.py`, `test_complexity.py`, `test_code_hygiene.py`, `test_dead_code.py` + `pyproject.toml` `[tool.ruff]`, `[tool.mypy]`, `[tool.importlinter]`, `[tool.xenon]`, `[tool.vulture]` | The configurations themselves |
| 5 | Backtest Layer A | *not yet implemented — see Gaps* | Realised post-event IV path |
| G1 | `/health` gate | [`main.py`](main.py) lines 89–103 + `tests/acceptance/test_health_acceptance.py` | `state.is_ready` after `populate_windows()` completes |

Supporting artefacts:

| Artefact | Role |
| --- | --- |
| [`app/registry.py`](app/registry.py) + `data/registry/` | Indicator registry (per ADR-0002) |
| [`tests/integration/test_bootstrap.py`](tests/integration/test_bootstrap.py) | Live-API bootstrap; skipped without `FRED_API_KEY` |

Oracles 1–4 plus G1's test run as one `pytest` invocation from
`apps/classification/`. Oracle 5 (Layer A) is unbuilt.

## Test inventory

| Path | Oracle | Disposition |
| --- | --- | --- |
| `tests/acceptance/test_contract_shapes.py` (7 tests) | 1 — contract shape | BUILT |
| `tests/acceptance/test_anchor_events.py` (11 parametrized) | 2 — anchor scenarios | BUILT; reds during ECDF migration |
| `tests/acceptance/test_signed_score_axioms.py` (7 tests) | 3 — mathematical axioms | BUILT; reds during signed-score migration |
| `tests/architecture/` (4 files, one tool each) | 4 — structural fitness | BUILT |
| `tests/acceptance/test_health_acceptance.py` (2 tests) | G1 — `/health` gate | BUILT |
| `tests/integration/test_bootstrap.py` | Separate — live-API bootstrap | Skipped when `FRED_API_KEY` absent |
| *(`tests/backtest/` — does not exist)* | 5 — Backtest Layer A | NOT BUILT |

## Response protocol — when an oracle fires

When an oracle (1 contract / 2 anchor / 3 axiom / 4 fitness / 5 Layer A)
or the G1 health gate flags a failure:

1. **Classify** the failure mode and identify which oracle caught it.
2. **Caught by the responsible oracle — harness working as designed.**
   Fix the bug; add a regression case (new anchor / axiom / fitness rule
   / Layer A scenario) if the existing one didn't cover the variant.
   No ADR. Normal commit + test discipline. This is the common path.
3. **Escaped all five oracles — harness gap.** Pick one:
   - **Add a new control.** Open an ADR for the architectural
     decision (the new fitness rule / axiom / anchor class / contract
     clause / Layer A scenario type). The bug appears in Context as the
     trigger. The ADR must name which oracle class catches the failure
     mode going forward.
   - **Accept the gap.** Document in
     [`LIMITATIONS.md`](LIMITATIONS.md) with failure mode, rationale,
     and the conditions that would re-open the question.

Trigger summary: **ADR ⇔ architectural decision.** Bug ⇏ ADR.
Bug + new control = ADR. Bug + accepted gap = LIMITATIONS entry.

## Current gaps

Tracked here so the next task can pick them up. Closing a gap that
requires a new control opens an ADR per the response protocol above;
gaps closed by routine implementation work do not.

- **Signed-score migration in implementation.** SRS CLS-001 specifies
  signed severity in `[-1.0, +1.0]`; verify strategy code emits signed
  scores end-to-end and that the OpenAPI score range is migrated in
  lockstep with the .NET-side schema. *Currently failing axioms:
  `test_vol_compression_returns_negative_score`,
  `test_zero_deviation_returns_near_zero_score`.*
- **Long-horizon ECDF implementation.** SRS CLS-001 anchors severity
  to a long-horizon reference window `H_L` of length `N_L`
  (binomial-SE bounded, ≥ 278); verify per-symbol windows run at that
  depth in production bootstrap, not at the legacy short-window depth.
  *Currently failing anchors:
  `market_data_vix_low_vol_regime_2017_10_05`,
  `market_data_vix_normal_day_2019_07_15`.*
- **Parametric fallback path.** SRS CLS-001 specifies a parametric
  fit fallback for indicator classes whose `N_L` is unattainable
  (monthly macro). Verify the fallback exists and routes through
  CLS-009-style degraded confidence. *Currently failing axiom:
  `test_parametric_gate_failure_returns_degraded_certainty`.*
- **Backtest Layer A — not yet built.** ADR-0003 specifies the
  market-IV-outcome oracle layer; scaffolding does not exist in the
  repo today.
- **CROSS_ASSET_FLOW anchors** — deferred until the strategy lands on
  ECDF.
- **GEOPOLITICAL anchors** — deferred until those strategies exist;
  EVENT_ASSESSMENT via LLM, not covered by ECDF.
- **Property-based tests on `_compute_temporal_relevance`** — deferred
  until the function is extracted to `app/math/temporal.py`.
- **Mutation testing (mutmut)** — sensor-of-sensors on
  `app/strategies/*.py` and `app/math/*.py`, deferred.
