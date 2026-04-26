# ADR-0003: Window-degeneracy guard supersedes per-class dispersion floor

**Status:** Accepted
**Date:** 2026-04-27
**Supersedes:** ADR-0002 §2 (the `D` per-class registry parameter only — `N`,
`deviation_kind`, and `expected_frequency_seconds` are unaffected).

## Context

ADR-0002 introduced a per-indicator-class `D` (minimum-informative
dispersion floor): a non-negative real-valued threshold on the rolling IQR
of the history window. When `IQR(history) < D`, CLS-009 fired a
degraded-confidence response in place of a normal-path ECDF severity. The
intent was to guard the OVX-quiet-regime pathology — a modest move ranking
at p95 against a flat history — without overfitting per-event scales.

Two specialists rejected `D` as specified:

- **/statistician.** Per-class absolute `D` is undefendable at the sample
  sizes available. A defensible empirical p5 of the rolling-IQR
  distribution requires ≥ 200 non-overlapping IQR observations, i.e.
  `200 × N` raw points. For `us_inflation_yoy` at `N = 60` that is 1,000
  years of monthly data — unreachable. Overlapping windows have lag-1
  autocorrelation > 0.95; the effective sample size is `total_obs / N`,
  not `total_obs − N + 1`. The "200 observations" target does not survive
  the autocorrelation correction. `D` was a parameter without a defensible
  estimator at any sample size we will ever have for monthly or weekly
  series.

- **/trader.** "Minimum dispersion floor" is not a parameter anyone on a
  vol desk quotes, defends, or uses to size a trade. It is an
  implementation condition ("rank is meaningless when the window is
  degenerate"), not a calibration target.

A scale-invariant ratio replacement (e.g. `IQR < α × median(|deviation|)`)
was considered and rejected on statistical grounds: numerator and
denominator are both computed from the same window of a positive series;
the ratio approximates the interquartile coefficient of dispersion (IQCD),
which is bounded in roughly `[0.5, 2.0]` for typical financial returns
regardless of regime. A ratio cannot detect a *scale-collapsed* window —
exactly the failure mode the floor exists to detect.

## Decision

CLS-009's first guard condition is replaced with a **window-degeneracy
check**, not a dispersion threshold:

```
is_window_degenerate(H) ≡ |{ round(v, 4) : v ∈ H }| < k_min
```

where `H` is the history window and `k_min = 10` is a single global
constant.

Properties:

- **Distribution-free.** No assumption about the shape of `|deviation|`.
- **Sample-size independent.** No empirical p5 to estimate; no
  autocorrelation correction needed.
- **First-principles constant.** A percentile rank over fewer than ten
  distinct values has resolution coarser than `1/10 = 10pp`; below that the
  rank is not informative regardless of distribution.
- **Detects scale collapse.** A flat or near-flat window has few distinct
  values after rounding, regardless of absolute scale.
- **One global parameter, not per-class.** No calibration ever needed.

The rounding precision (4 decimal places of `|deviation|`) is set at the
significance of the inputs (FRED daily closes are 2 decimal places; pct-
change `|deviation|` carries at most 4–5 significant decimals after
division). Rounding prevents floating-point spurious distinctness.

The `D` field is removed from `infra/registry.yaml` and from
`IndicatorClass`. The `dispersion_below_floor` field in `computed_metrics`
is renamed to `window_degenerate`. CLS-009's normative text is revised
(SRS v2.3.2 in-place revision; not a new SRS version because the change is
within the still-PLANNED #5 remediation surface).

## Consequences

**What this change buys:**

- Removes a registry parameter that could not be honestly calibrated.
- Removes the LIMITATIONS.md #6 D-calibration protocol (steps 1–4 of the
  former protocol dissolve; the trader sanity gate and regime-bucketed
  validation remain for `N`).
- Removes a class of bug where stale, wrong, or unreviewed `D` values
  produce confident-looking but degraded outputs.

**What this change costs:**

- ADR-0002 §2 and §3 prose still mention `D`. ADR-0003 supersedes those
  paragraphs only; the rest of ADR-0002 stands.
- The acceptance fixture rationale strings that mention `D` are
  obsolete-phrasing; black-box assertions are unaffected (no fixture
  asserts on `dispersion_below_floor`).
- Operators must distinguish a *registry-driven* guard (gone) from an
  *implementation-driven* guard (current). The current guard cannot be
  tuned without changing source code, by design.

**What this change does not change:**

- `N` stays in the registry. It is a structural choice that defines what
  "rank" means to the trader. Static, calibrated once per class via the
  trader sanity gate documented in LIMITATIONS.md #6.
- `deviation_kind` stays in the registry. Per-class data-shape parameter.
- `expected_frequency_seconds` stays in the registry.
- CLS-001's severity formula is unchanged. CLS-009's second guard
  (unknown indicator) is unchanged.

## Compatibility

The OpenAPI contract `INVEX-API-v1.yaml` is unaffected: severity is a
number in `[0, 1]`, certainty is a number in `[0, 1]`, both before and
after this change. The `computed_metrics` map is loosely typed at the
contract level (free-form additional properties); the field rename from
`dispersion_below_floor` to `window_degenerate` is non-breaking for
schema consumers.

## Related

- Supersedes the `D` paragraphs of ADR-0002 §2 and §3.
- Updates SRS v2.3.2 §3 definitions (drops "Minimum-informative dispersion
  D"; adds "Window degeneracy") and CLS-009 first guard condition.
- Closes the D portion of LIMITATIONS.md #6; the N portion remains.
