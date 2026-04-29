# HARNESS — Classification Service

**Inferable inventory** of the harness that steers the Python
classification service: file paths, current dispositions, current gaps.
The locked architectural decision (the three durable controls, the
three test layers with distinct oracles, the steering-loop discipline,
the out-of-scope list) lives in
[ADR-0003](doc/adr/0003-harness-architecture.md). This file is
regenerable from that ADR plus the current state of the repo.

This service is constant infrastructure across all six INVEX .NET
architecture iterations. It is not under measurement.

## Layer map

| Layer | Artifact |
| --- | --- |
| Contract (authoritative) | [`doc/openapi.yaml`](doc/openapi.yaml) |
| Contract-shape tests | `tests/acceptance/test_contract_shapes.py` |
| Reference-scenario tests | `tests/acceptance/test_anchor_events.py` + [`tests/acceptance/fixtures/ANCHORS.md`](tests/acceptance/fixtures/ANCHORS.md) |
| Health acceptance | `tests/acceptance/test_health_acceptance.py` |
| Signed-score axioms | `tests/acceptance/test_signed_score_axioms.py` |
| Structural fitness | `tests/architecture/test_layering.py`, `test_code_smells.py`, `test_complexity.py`, `test_typing.py`, `test_dead_code.py` |
| Tooling config (fitness) | `pyproject.toml` — `[tool.ruff]`, `[tool.mypy]`, `[tool.importlinter]`, `[tool.xenon]`, `[tool.vulture]` |
| Indicator registry | [`app/registry.py`](app/registry.py) + `data/registry/` |
| Backtest Layer A | *not yet implemented — see Gaps* |

All fitness tests run as pytest; one `pytest` invocation executes
acceptance and fitness together.

## Test inventory

| Path | Kind | Disposition |
| --- | --- | --- |
| `tests/acceptance/` | Black-box against the contract + anchor replay + signed-score axioms | Authoritative layer |
| `tests/architecture/` | Fitness functions wrapping `import-linter`, `ruff`, `mypy`, `xenon`, `vulture` | Authoritative layer |
| `tests/integration/test_bootstrap.py` | Live-API bootstrap | Separate category; skipped when `FRED_API_KEY` is absent |

## Current gaps

Tracked here so the next task can pick them up. Closing a gap requires
an ADR (postmortem-style) per the steering-loop discipline in
[ADR-0003](doc/adr/0003-harness-architecture.md).

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
