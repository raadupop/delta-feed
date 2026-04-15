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
