# Known Limitations

Production-critical weaknesses tracked here. Each entry includes the risk and what a production-grade fix looks like.

---

## 1. ~~Fixed `_TANH_SCALE` calibration~~ — ADDRESSED

**Affects:** MARKET_DATA, MACROECONOMIC (and future CROSS_ASSET_FLOW) strategies

**Status:** Addressed by ADR-0001 Phase B + ADR-0002. Severity is now an ECDF rank against the per-symbol rolling history; there is no `_TANH_SCALE` constant. Calibration knobs (`N`, `D`) live in [`infra/registry.yaml`](../../infra/registry.yaml) per indicator class — paper-computable per indicator without a magic scale constant. Empirical calibration of `N`/`D` itself is tracked separately as #6.

---

## 2. ~~No window staleness detection~~ — ADDRESSED

**Affects:** All strategies using rolling windows (MARKET_DATA, MACROECONOMIC, CROSS_ASSET_FLOW)

**Status:** Addressed. Certainty is split into two independently computed dimensions:
- `source_reliability`: window fullness (how many values) — the original certainty formula
- `temporal_relevance`: exponential decay based on time since last update, relative to the indicator class's `expected_frequency_seconds` (sourced from [`infra/registry.yaml`](../../infra/registry.yaml) per ADR-0001 Phase B)
- `certainty = source_reliability × temporal_relevance`

The `RollingWindow` class in `app/state.py` tracks `last_update` alongside values. The `/health` endpoint exposes per-window staleness (last update timestamp + seconds since). Different indicator cadences (daily vol indices, monthly CPI, weekly claims) are now correctly distinguished by class — weekly INITIAL_CLAIMS uses 7-day expected frequency rather than the previous shared 30-day constant.

---

## 3. ~~Fixed `tanh` curve for severity mapping~~ — ADDRESSED

**Status:** Addressed by ADR-0002. Severity is now `ecdf_rank(|deviation|)` against the per-symbol rolling history, not `tanh(value / scale)`. No assumed curve shape, no tuning constant, adapts as the distribution shifts. Calibration of the per-class `N` (history length) and `D` (dispersion floor) is tracked separately as #6.

---

## 4. Test events not validated for exploitability

**Affects:** All 10 historical events in the test suite (AGENTS.md)

**Risk:** The test suite validates that the classifier produces correct severity scores from real data. It does not validate that those scores would have led to profitable trades. Exploitability depends on the full pipeline: composite scoring (CLS-002) aggregates multiple signals, IV dislocation detection (CLS-006) compares signal-implied IV to market-observed IV, and the decision engine (DEC-001) determines whether to deploy capital. A high severity score alone does not mean an event was exploitable.

**Current state:** The Phase 1 convexity analysis tags events with `exploitable: true/false` and `windowHours`, but these are manual estimates based on a rule-of-thumb ("6+ hours and 15%+ spike"), not computed from options market data.

**Production fix:**

- Validate exploitability via the .NET replay system (ANA-001), which replays historical signals through the full composite → dislocation → decision → position pipeline
- Use real intraday IV data (CBOE, OptionMetrics) to measure the actual dislocation window for each event
- Only events with confirmed positive P&L in replay should be considered exploitable

---

## 5. Self-validating-loop bug class at the per-signal severity layer

**Status:** PLANNED — two-part remediation scoped in [ADR-0002](doc/adr/0002-ecdf-severity-and-backtest-harness.md).

**Affects:** All RULE_BASED strategies (MARKET_DATA, MACROECONOMIC, CROSS_ASSET_FLOW). Root cause of #1 (scale fitting) and #3 (fixed `tanh` curve) — those are symptoms of the same underlying gap.

**Risk:** CLS-001 in the SRS is deliberately qualitative ("severity is quantified; certainty has two independent dimensions combined somehow") with no formula. An AI agent authoring both the strategy and its tests in one pass can encode the same wrong assumption in both — the acceptance suite validates the contract shape and anchor bands, but cannot validate that the formula itself is right, because there is no independent formula to compare against. The 4-fixture axis-coverage work (OVX Aramco, VIX COVID mid-crisis, VIX vol crush, VIX normal day) collapsed to regression guards: their bands reflect whatever the classifier currently outputs, not a paper-computed reference.

**Current state:** Acceptance suite + architectural fitness layer cannot catch this class. Structurally invisible to the existing harness.

**Production fix (two parts, together):**

1. **Tighten CLS-001 with a normative formula.** Landed in [SRS v2.3.2](../../doc/srs/INVEX-SRS-v2.3.2.md): ECDF / percentile rank with two per-class parameters (`N`, `D`) makes severity paper-computable per indicator without a magic scale constant. The formula is inline in the revised CLS-001, matching the CLS-002 / CLS-006 pattern. Companion SRS changes are CLS-009 (RULE_BASED degraded-confidence fallback for dispersion-floor trips and unknown indicators; distinct from CLS-004, which is AI-response-specific) and eight new §3 Definitions entries anchoring the vocabulary including the indicator registry. SIG-001 is preserved verbatim; the registry is not a numbered sub-requirement. See [ADR-0002](doc/adr/0002-ecdf-severity-and-backtest-harness.md); the earlier [CLS-001 annex stub](doc/adr/srs-annex-cls-001-severity-formula.md) is superseded by the SRS body.
2. **Add a backtest harness layer with a market-reality oracle.** Acceptance suite asserts the SRS contract (formula-based, deterministic). Backtest Layer A asserts that the classifier's output is consistent with what IV actually did post-event (binary direction + magnitude bucket). Different oracle, different bug class, no duplication. Documented in [HARNESS.md](HARNESS.md).

---

## 6. Registry parameters (`N`, `D`) are uncalibrated placeholders

**Status:** PLANNED — calibration is `/trader` + `/statistician` work, separate from registry mechanics.

**Affects:** All RULE_BASED strategies once ECDF lands ([ADR-0002](doc/adr/0002-ecdf-severity-and-backtest-harness.md)).

**Risk:** [`infra/registry.yaml`](../../infra/registry.yaml) ships with `N` and `D` values matched to operator + `/trader` intuition, not derived from real data. Specifically:

- **`N`** values (252 / 60 / 156) are conventional choices (one trading year, five years of monthly inflation, three years of weekly claims). They are defensible defaults but have not been validated against ECDF rank stability on the actual symbols.
- **`D`** values (0.5 / 1.0 / 0.1 / 0.15) are placeholder dispersion floors. None are derived from rolling-IQR distributions on real history. Until calibrated, the CLS-009 dispersion-floor guard fires at thresholds that may be too loose (lets quiet-regime false-highs through) or too tight (degrades confidence on legitimate signals).

**Current state:** Registry exists with placeholder values. ECDF code that consumes them is unimplemented (build-step pending).

**Production fix:**

1. Pull 5+ years of history per symbol (FRED for inflation/labor, CBOE/Twelve Data for vol indices).
2. Compute rolling-IQR distribution per symbol with the proposed `N`.
3. Set `D` per class at the empirical 5th-percentile of the IQR distribution (or whatever percentile `/statistician` defends).
4. Validate `N` by re-running ECDF on historical events and checking that severity ranks correlate with `/trader` intuition for known events (e.g., COVID first spike should rank > p95).
5. Update `infra/registry.yaml` with calibrated values, document the calibration commit in this entry.

**Reversibility:** Trivial. `git revert` on the registry change. CoBW: bounded — only affects severity scores between deploy and recalibration.

---

## 7. Multi-symbol-per-class is structurally untested

**Status:** ACCEPTED — covered by ADR-0002 design; will be exercised when ECDF lands.

**Affects:** All classes in [`infra/registry.yaml`](../../infra/registry.yaml) with multiple symbols (`equity_vol_index`, `commodity_vol_index`, `us_inflation_yoy`, `us_labor_weekly`).

**Risk:** Current acceptance fixtures cover one symbol per class (`VIX`, `OVX`, `CPI_YOY`, `INITIAL_CLAIMS`). The dedup justification in ADR-0002 assumes that tuning `N` or `D` for a class behaves correctly across all member symbols. Until a fixture exercises a second member of any class, this is asserted rather than tested.

**Current state:** Registry declares 13 symbols across 4 classes. Acceptance fixtures exercise 4 of them.

**Production fix:** Add at least one fixture for a second member of each multi-symbol class:

- `equity_vol_index`: a VVIX or VXN anchor (e.g., VVIX during 2018 Volmageddon)
- `commodity_vol_index`: a GVZ anchor (e.g., gold spike on geopolitical event)
- `us_inflation_yoy`: a CORE_CPI_YOY anchor (e.g., 2022 core inflation peak)
- `us_labor_weekly`: a CONTINUED_CLAIMS anchor (e.g., 2020 COVID labor shock)

`/trader` curates dates per `ANCHORS.md`, `/statistician` reviews that the resulting severity ranks are consistent with same-class siblings under shared parameters.
