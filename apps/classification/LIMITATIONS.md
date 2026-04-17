# Known Limitations

Production-critical weaknesses tracked here. Each entry includes the risk and what a production-grade fix looks like.

---

## 1. Fixed `_TANH_SCALE` calibration

**Affects:** MARKET_DATA, MACROECONOMIC (and future CROSS_ASSET_FLOW) strategies

**Risk:** The `_TANH_SCALE` constant that maps raw scores to [0, 1] severity is fitted to 2 test events per strategy. This is curve-fitting, not calibration. A poorly chosen scale compresses or stretches the severity range, weakening downstream composite scoring (CLS-002).

**Current state:** MARKET_DATA uses 20.0, MACROECONOMIC uses 3.0 — both derived from back-of-envelope estimates and 2 historical anchors.

**Production fix:**
- Calibrate against 20+ historical releases per indicator with known market reactions
- Backtest end-to-end through CLS-002 composite scoring to validate that component severity produces correct composite behavior
- Consider adaptive scaling: derive scale from the data itself (e.g., 95th percentile of historical values), so it adjusts as market regimes change

---

## 2. ~~No window staleness detection~~ — ADDRESSED

**Affects:** All strategies using rolling windows (MARKET_DATA, MACROECONOMIC, CROSS_ASSET_FLOW)

**Status:** Addressed. Certainty is now split into two independently computed dimensions:
- `source_reliability`: window fullness (how many values) — the original certainty formula
- `temporal_relevance`: exponential decay based on time since last update, relative to the expected update frequency (3 calendar days for MARKET_DATA, 30 days for MACROECONOMIC)
- `certainty = source_reliability × temporal_relevance`

The `RollingWindow` class in `app/state.py` tracks `last_update` alongside values. The `/health` endpoint exposes per-window staleness (last update timestamp + seconds since).

**Remaining considerations:**
- Expected frequencies are module-level constants per strategy; future indicators with different release cadences (e.g., weekly jobless claims) will need per-indicator frequency configuration
- CROSS_ASSET_FLOW strategy (not yet implemented) will follow the same pattern when built

---

## 3. Fixed `tanh` curve for severity mapping

**Status:** PLANNED — remediation scoped in [ADR-0002](doc/adr/0002-ecdf-severity-and-backtest-harness.md). Pivot to ECDF / percentile rank with per-class `N` (history length) + `D` (minimum-informative-dispersion floor). Implementation deferred to `/chief-architect` engagement.

**Affects:** MARKET_DATA, MACROECONOMIC (and future CROSS_ASSET_FLOW) strategies

**Risk:** `tanh(value / scale)` assumes a fixed S-curve shape for mapping raw scores to severity. The curve shape never changes — it doesn't adapt to shifting market regimes, and the scale constant bakes in a static judgment about what counts as "severe." Industry-grade systems (Bloomberg, Aladdin) either pass raw values through and let downstream systems interpret, or use continuously recalibrated models.

**Current state:** All RULE_BASED strategies use `tanh` with a hardcoded scale constant.

**Production alternatives (by increasing sophistication):**
- **Empirical CDF:** Rank the current value against the full window history. "This is the 95th percentile of surprises" → severity 0.95. No assumed curve shape, no tuning constant, adapts automatically as the distribution shifts. Simplest upgrade from tanh.
- **Pass raw scores to composite:** Remove severity mapping from the classifier entirely. Let the .NET composite layer (CLS-002) decide how to weight raw surprise magnitudes alongside other signals — it has more context.
- **Learned mapping:** Fit severity from historical data (surprise magnitude vs observed market reaction). Requires labeled data: "this surprise produced this market impact." Most accurate, highest data requirement.

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

1. **Tighten CLS-001 with a normative formula.** ECDF / percentile rank with two per-class parameters (`N`, `D`) makes severity paper-computable per indicator without a magic scale constant. Shifts CLS-001 from Insight-7 category (b) qualitative to (a) quantitative for a principled statistical reason. See [ADR-0002](doc/adr/0002-ecdf-severity-and-backtest-harness.md) and the [CLS-001 SRS annex stub](doc/adr/srs-annex-cls-001-severity-formula.md).
2. **Add a backtest harness layer with a market-reality oracle.** Acceptance suite asserts the SRS contract (formula-based, deterministic). Backtest Layer A asserts that the classifier's output is consistent with what IV actually did post-event (binary direction + magnitude bucket). Different oracle, different bug class, no duplication. Documented in [HARNESS.md](HARNESS.md).
