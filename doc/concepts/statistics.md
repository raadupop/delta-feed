# Math Concepts Reference

Concepts used in INVEX classification service, explained from first principles.

**Update log.**
- 2026-04-14 — initial file (§1–§7: exponential decay, normalization, clamping, multiplicative vs additive, discounting, z-score, tanh).
- 2026-04-19 — ECDF-era additions (§8–§16). z-score (§6) and tanh (§7) marked DEPRECATED per [ADR-0002](../../apps/classification/doc/adr/0002-ecdf-severity-and-backtest-harness.md) and SRS v2.3.2 CLS-001.
- 2026-04-23 — §9 Deviation added (after §8 ECDF). Canonical definition per SRS v2.3.2 §3. §9–§16 renumbered to §10–§17.

---

## 1. Linear vs Exponential Decay

Two ways something can decrease over time.

**Linear decay** — drops by the same AMOUNT each period:
```
100 → 80 → 60 → 40 → 20 → 0
    -20   -20   -20   -20   -20
```
Like a candle burning: loses the same amount of wax per hour. Hits zero and stops.

**Exponential decay** — drops by the same PROPORTION each period:
```
100 → 37 → 14 → 5 → 2 → 0.7
    ×0.37  ×0.37  ×0.37  ×0.37  ×0.37
```
Like hot coffee cooling: loses heat fast at first, then slows down. Never quite reaches room temperature.

**When to use which:**
- Linear: when decrease is constant (paying off a loan at fixed rate, countdown timer)
- Exponential: when the decrease is proportional to what's left (information decay, radioactive decay, interest rates, options theta, volatility mean reversion)

**Formula:** `e^(-x)` where e ≈ 2.71828

| x | e^(-x) | Meaning |
|---|---|---|
| 0 | 1.0 | No decay |
| 0.5 | 0.61 | Moderate decay |
| 1.0 | 0.37 | ~63% lost |
| 2.0 | 0.14 | ~86% lost |
| 3.0 | 0.05 | ~95% lost |

**Used in finance:**
- Black-Scholes: `e^(-rT)` discounts strike price over time
- Theta decay: options lose value exponentially as expiration approaches
- VIX mean reversion: spikes decay fast at first, then slow down
- Bond pricing: `PV = FV × e^(-rt)` — continuous discounting
- EWMA: exponentially weighted moving averages for vol estimation

---

## 2. Normalization

Converting raw values into comparable units by dividing by a reference value.

**Problem without normalization:**
- MARKET_DATA is 3 days overdue = 259,200 seconds
- MACROECONOMIC is 1 month overdue = 2,592,000 seconds
- Both are "1 period late" but raw seconds are wildly different
- `exp(-259200)` = effectively zero. Raw seconds are too large.

**Solution:** Divide by the expected frequency:
```
normalized = staleness / expected_frequency
```
- 259,200 / 259,200 = 1.0 (1 period late)
- 2,592,000 / 2,592,000 = 1.0 (1 period late)

Now both produce `exp(-1) = 0.37`. Same "lateness", same decay.

**General principle:** When comparing values on different scales, divide each by its own baseline to get a ratio. The ratio is unit-free and comparable.

**Other examples:**
- Z-score: `(value - mean) / std` — normalizes by how spread out the data is
- Percentage change: `(new - old) / old` — normalizes by starting value
- BMI: `weight / height^2` — normalizes weight by body size

---

## 3. Clamping (max / min)

Forcing a value to stay within a range.

**`max(0.0, x)`** — if x goes below 0, force it to 0:
```
max(0.0, 5)   = 5    (no change, already positive)
max(0.0, -3)  = 0    (clamped, was negative)
```

**`min(1.0, x)`** — if x goes above 1, force it to 1:
```
min(1.0, 0.7) = 0.7  (no change, already below 1)
min(1.0, 1.5) = 1.0  (clamped, was too high)
```

**Combined — clamp to [0, 1]:**
```
max(0.0, min(1.0, x))
```

**Why it matters:** Mathematical formulas can produce values outside the valid range. Clamping prevents nonsensical outputs:
- `exp(-negative)` = number > 1.0 — temporal relevance shouldn't exceed 1.0
- Certainty shouldn't be negative
- Scores must stay in [0.0, 1.0]

---

## 4. Multiplicative vs Additive Combination

Two ways to combine independent dimensions into one score.

**Additive (weighted average):**
```
certainty = 0.5 × history_sufficiency + 0.5 × temporal_relevance
```
- HS=1.0, TR=0.0 → certainty = 0.5 (one perfect dimension masks a zero)
- "At least one good dimension gives partial credit"

**Multiplicative:**
```
certainty = history_sufficiency × temporal_relevance
```
- HS=1.0, TR=0.0 → certainty = 0.0 (zero in any dimension kills the result)
- "Both dimensions must be good for the result to be good"

**When to use which:**
- Multiplicative: when dimensions are prerequisites (need BOTH fresh data AND enough history)
- Additive: when dimensions are complementary (a bit of A can compensate for less B)

**Analogy:**
- Multiplicative = AND logic: "I need a valid passport AND a visa to enter"
- Additive = partial credit: "Score is 50% exam + 50% coursework"

---

## 5. Discounting

Reducing the value of something because of a condition (time, risk, quality).

**Core idea:** Something worth X today may be worth less under certain conditions.

**Examples:**
- **Time discount:** $100 next year is worth ~$95 today (at 5% rate). The further away, the less it's worth now. Formula: `PV = FV × e^(-rt)`
- **Staleness discount:** A VIX reading from 3 hours ago is worth less than one from 3 seconds ago for trading decisions
- **Source discount (INVEX d_c):** A composite score is discounted when expected data sources are missing — you have less information, so trust the result less
- **Risk discount:** A trade with higher risk is "discounted" — you need a bigger expected return to justify it

**In INVEX:** Temporal relevance IS a discount factor. It takes the "base certainty" (history sufficiency) and discounts it for staleness:
```
certainty = history_sufficiency × temporal_relevance(discount)
```

---

## 6. Z-Score

> **DEPRECATED (2026-04-19).** INVEX no longer uses z-score as an intermediate severity measure. Replaced by ECDF rank (§8) per [ADR-0002](../../apps/classification/doc/adr/0002-ecdf-severity-and-backtest-harness.md) and SRS v2.3.2 CLS-001. Section retained as audit trail.

How many standard deviations a value is from the mean.

```
z = (value - mean) / standard_deviation
```

**What it tells you:** "How unusual is this value compared to recent history?"

| z-score | Meaning | In a normal distribution |
|---|---|---|
| 0 | Exactly average | 50% of values are below this |
| 1 | 1 std above mean | ~84% below — somewhat unusual |
| 2 | 2 std above mean | ~97.7% below — unusual |
| 3 | 3 std above mean | ~99.9% below — rare |
| 6+ | Extreme | Shouldn't happen under normal conditions |

**INVEX usage:** MARKET_DATA strategy computes z-score of current VIX value against 20-day rolling window. Volmageddon produced z=27.5 (VIX jumped from ~10 to 37 against a calm window).

**Why it's useful:** It's normalized (see concept #2). A VIX move from 10 to 15 and a move from 30 to 35 are both +5 points, but the first is far more unusual relative to its recent history. Z-score captures that.

---

## 7. tanh (Hyperbolic Tangent)

> **DEPRECATED (2026-04-19).** INVEX no longer uses `tanh(|z|/scale)` for severity compression. The fitted `_TANH_SCALE` constant assumed a time-invariant distribution, which no vol indicator has across 2017–2024. Replaced by ECDF rank (§8) per [ADR-0002](../../apps/classification/doc/adr/0002-ecdf-severity-and-backtest-harness.md) and SRS v2.3.2 CLS-001. Section retained as audit trail.

A function that maps any number to the range (-1, 1). INVEX uses `tanh(|x|)` to map to [0, 1].

```
tanh(0) = 0
tanh(1) = 0.76
tanh(2) = 0.96
tanh(3) = 0.995
tanh(∞) = 1.0
```

**Shape:** S-curve. Starts flat near 0, rises steeply in the middle, flattens near 1.

**Why INVEX uses it:** Raw z-scores are unbounded (can be 6, 27, 100+). Severity needs to be [0, 1]. `tanh` compresses large values toward 1.0 without hard-clipping them — a z-score of 27 maps to 0.88, not 1.0, preserving the information that "even more extreme" is possible.

**The scale parameter:** `tanh(z / scale)` controls where the curve is steep vs flat. A larger scale (20 for MARKET_DATA) means higher z-scores are needed to reach high severity. A smaller scale (3 for MACROECONOMIC) means the curve is more sensitive.

---

## 8. Empirical Cumulative Distribution Function (ECDF) / ECDF Rank 

A way to say "where does this value sit in its history?" without assuming the history follows any particular distribution shape.

**Core idea.** You have a history window of `N` past values. For a new value `x`, count how many of those past values are `≤ x`. Divide by `N`. That's the ECDF rank.

```
history = [10, 12, 11, 15, 13, 22, 14]   (N = 7)
new value x = 16
count of history ≤ 16:  [10, 12, 11, 15, 13, 14] → 6 out of 7
ECDF rank = 6/7 = 0.857
```

**What it tells you:** "86% of the last 7 values were at or below this one." Equivalent phrasing: "this is roughly at the 86th percentile of recent history."

**Left-continuous convention for ties.** When the new value equals some history values, the convention matters. INVEX uses `≤` (left-continuous): ties count toward the rank. A value exactly equal to the previous 3 values gets rank `3/N`, not `0/N`. This keeps the rank monotone-non-decreasing as `x` grows.

**Why INVEX uses it.**

- **Distribution-free.** Works whether the history is Gaussian, fat-tailed, skewed, bimodal, or weird. No assumption about shape.
- **Bounded output by construction.** Always in `[0, 1]`. No compression function (tanh) needed. No magic scale constant.
- **Regime-adaptive.** As the history window rolls forward, the ECDF updates automatically. A VIX of 25 during calm times gets a high rank; during a crisis window that already absorbed 40s, the same VIX of 25 gets a low rank.

**Contrast with z-score (§6, deprecated).** Z-score assumes standard deviation is a meaningful yardstick — true only for roughly symmetric, roughly Gaussian distributions. Vol indicators are neither. ECDF doesn't care.

**Formula (INVEX CLS-001):** `severity = ecdf_rank(|deviation|) / N`.

---

## 9. Deviation

The unsigned distance between an observed value and a strategy-specific reference value, computed without rescaling by standard deviation. This is the raw input to the ECDF severity formula (§8).

**Why not z-score.** Z-score divides by standard deviation: `z = (value − mean) / std`. That requires `std` to be stable and meaningful. Vol indicators are fat-tailed, regime-shifting, and serially correlated — `std` inflates after a spike and deflates in quiet regimes, silently distorting what "2 sigma" means. Deviation skips the division entirely. Magnitude is kept in native units; the ECDF then ranks it within its own history. The distribution shape does not matter.

**Per-category definitions (SRS v2.3.2 §3):**

| Source category | Formula | Reference value |
|---|---|---|
| MARKET_DATA | `\|current_value − rolling_median(history)\|` | Rolling median of the history window |
| MACROECONOMIC | `\|actual_value − consensus_expected_value\|` | Analyst consensus estimate |
| CROSS_ASSET_FLOW | `\|pairwise_correlation − rolling_baseline_correlation\|` | Rolling baseline correlation (§14) |

GEOPOLITICAL signals do not produce a deviation. Severity for GEOPOLITICAL is LLM-judged (CLS-003).

**`deviation_kind`.** An enumeration stored in the indicator registry (§16) that records which of the three definitions above applies to a given indicator class: `LEVEL_VS_MEDIAN`, `SURPRISE`, or `CORR_DEVIATION`. The classifier reads this from the registry at runtime — no conditional logic on source category in the formula itself.

**Worked example (MARKET_DATA).** VIX closes: history window = `[14.0, 14.5, 15.1, 13.8, 14.2, ...]` (N=60 days). Rolling median = 14.3. Today VIX = 28.6.
```
deviation = |28.6 − 14.3| = 14.3
```
ECDF then ranks 14.3 against the 60 history values of `|VIX − 14.3|`. If 57 of those are smaller, `ecdf_rank = 57`, `severity = 57 / 60 = 0.95`.

**Worked example (MACROECONOMIC).** CPI YoY: actual = 9.1%, consensus estimate = 8.8%.
```
deviation = |9.1 − 8.8| = 0.3 percentage points
```
ECDF ranks 0.3 against the N-period history of `|actual − expected|` for that indicator class.

**Relationship to §8 (ECDF), §11 (IQR), §17 (D).** Deviation is the value passed into `ecdf_rank()`. IQR is computed over the history of deviations to measure dispersion. `D` is the minimum IQR below which the history is too flat to trust. All three concepts work together in CLS-001 and CLS-009.

---

## 10. Percentile Rank

ECDF rank expressed as a human-readable percentile.

```
ECDF rank = 0.857  ⟺  "87th percentile"  ⟺  "p87"
ECDF rank = 0.95   ⟺  "95th percentile"  ⟺  "p95" (top 5%)
ECDF rank = 0.99   ⟺  "99th percentile"  ⟺  "p99" (top 1%)
```

**Why the traders talk this way.** Percentile rank is regime-relative and unit-free. "VIX deviation is at p95 against the trailing 60 days" means **95% of recent observations were at or below this one** — equivalently, it sits in the **top 5%** of the recent window. The rank communicates signal strength without requiring the listener to know raw levels, units, or the reference median that produced it.

**Careful with the phrasing.** "p95" does NOT mean "it has been this high 95% of the time." It means the opposite: it has been this high (or higher) only 5% of the time.

**INVEX ranks deviation, not the raw level — and these differ.** On a typical trading desk "VIX at p95" refers to the *level* of VIX against its trailing history. INVEX ranks `|deviation from median|` (§9), not the raw level. They diverge in important cases:

- VIX grinds from 15 → 20 over a month. The median drifts up with it. Deviation stays small → low severity, even though the absolute level is elevated.
- VIX spikes overnight from 15 → 28 while the 60-day median is still 14. Deviation = 14 points → high severity. Both approaches agree: this is extreme.

**The rank is sufficient for signal strength, not for execution.** A consumer can act on `severity = 0.95` knowing the move is statistically extreme for this regime. But execution still requires the raw level — bid-ask spreads, term structure shape, and position sizing all depend on whether VIX is at 25 or 45, even if both have the same deviation rank.

**In INVEX.** ECDF rank IS a percentile (just on a 0–1 scale). `severity = 0.95` means "this signal's `|deviation|` is in the top 5% of its own recent history."

---

## 11. Interquartile Range (IQR)

A robust measure of how spread out a set of values is.

**Recipe.**

1. Sort the values.
2. Find Q1 (25th percentile — cuts off the bottom quarter).
3. Find Q3 (75th percentile — cuts off the bottom three-quarters).
4. IQR = Q3 − Q1.

```
history = [10, 11, 12, 13, 14, 15, 22]   (sorted)
Q1 = 11 (cuts bottom 25%)
Q3 = 15 (cuts bottom 75%)
IQR = 15 − 11 = 4
```

**What it tells you:** "The middle half of the values spans 4 units."

**Why IQR, not standard deviation.** Standard deviation gets destroyed by outliers — one VIX spike from 10 to 50 makes std explode, making every other value look "normal" afterward. IQR ignores the top and bottom 25% by construction. A single spike doesn't move it.

**In INVEX.** The minimum-informative-dispersion floor `D` is measured in IQR, not std:

- `IQR(history) < D` → history is too flat to support a meaningful ECDF rank → CLS-009 degraded confidence.

Uses IQR instead of std specifically to avoid the pathology where a single recent spike inflates std, making the floor falsely "pass" even though the remaining history is flat.

---

## 12. Rolling Median

The median of the last `N` values, recomputed every period.

**Recipe.** Sort the last `N` values. Take the middle one. (For even `N`, take the average of the two middle ones.)

```
history = [10, 12, 11, 15, 13]   sorted → [10, 11, 12, 13, 15]
median = 12
```

**Why median, not mean.** For level-anomaly deviation (`|current − reference|`):

- **Mean** gets pulled toward outliers. A recent spike from 10 to 40 inflates the mean, making the spike "look less anomalous" in future readings because the reference moves toward it. **Spike-absorbing-into-mean pathology.**
- **Median** doesn't move much from an outlier. A single 40 in `[10, 12, 11, 15, 13, 40]` gives median = 12.5, barely budged. The reference stays anchored to "normal."

**In INVEX.** MARKET_DATA deviation is `|current_value − rolling_median(history)|`. The rolling median is the "normal level" against which deviation is measured.

---

## 13. Pairwise Correlation (Pearson ρ)

How two return streams move together. Ranges from −1 (perfectly opposite) through 0 (unrelated) to +1 (perfectly together).

**Formula.**

```
ρ(X, Y) = covariance(X, Y) / (std(X) × std(Y))
```

- Covariance: average of `(xᵢ − x̄) × (yᵢ − ȳ)` — positive when X and Y deviate in the same direction, negative when they deviate oppositely.
- Dividing by the two standard deviations normalizes to `[−1, +1]`.

**Intuition.**

- `ρ = +0.9`: SPY and QQQ. They go up and down together.
- `ρ = 0`: SPY and gold-miner stocks (some periods). Roughly independent.
- `ρ = −0.6`: SPY and VIX. Inverse relationship — when stocks fall, vol rises.

**In INVEX.** CROSS_ASSET_FLOW strategy doesn't care about the *level* of correlation. It cares about *changes* in correlation (see §13).

---

## 14. Rolling Baseline Correlation

The correlation of two return streams measured over a trailing window, recomputed each period.

**Recipe.**

```
baseline_ρ(t) = Pearson correlation of (X, Y) over the last N periods ending at t
current_ρ(t)  = Pearson correlation of (X, Y) over a shorter recent window ending at t
deviation      = |current_ρ(t) − baseline_ρ(t)|
```

**What trips the signal.** SPY and VIX normally have `ρ ≈ −0.7`. If that relationship breaks (suddenly drops to `ρ ≈ −0.2` or flips positive), something unusual is happening in the market — often a liquidity event or a regime change. The `deviation` is how much the current correlation has departed from its rolling baseline.

**In INVEX.** CROSS_ASSET_FLOW deviation (CORR_DEVIATION kind) is `|current_ρ − rolling_baseline_ρ|`. The ECDF of that deviation over history produces severity.

---

## 15. Distribution-Free / Regime-Adaptive

Two properties of ECDF that together explain why it replaced tanh.

**Distribution-free.** Does not assume the underlying data follows any particular distribution shape (Gaussian, exponential, power-law, etc.). The ECDF rank is just a count — it works on any data.

- Z-score assumes symmetric, roughly Gaussian. VIX is not.
- tanh with a fitted scale assumes the scale is stable across time. It isn't — VIX regime of 2017 and VIX regime of 2020 have wildly different dispersions.
- ECDF makes no such assumption.

**Regime-adaptive.** As market conditions change, the trailing history window changes with them, so the ECDF rank recalibrates automatically.

- In a calm regime (VIX 10–15), a VIX of 25 is rank ≈ 1.0 (off the top).
- In a crisis regime (VIX 30–50), a VIX of 25 is rank ≈ 0.0 (below the window).
- Same raw value, opposite signal strength — because the signal is *relative to the prevailing regime*, not absolute.

**Trade-off.** ECDF loses the ability to say "this is a 5-sigma event in absolute terms." It only tells you "this is extreme for the recent window." For vol-exploitation trading, the relative view is what matters — you're looking for *dislocations from current normal*, not deviations from a long-dead baseline. This is intentional.

---

## 16. Indicator-Class Pooling

Why INVEX calibrates per *class* (group of symbols), not per symbol.

**Motivation.** Every symbol needs calibration parameters (`N`, `D`, `deviation_kind`). With 50+ symbols, per-symbol calibration means 50+ parameter rows to maintain and validate. Pooling symbols that behave the same statistically collapses those to a handful of classes.

**The pooling criterion is empirical, not taxonomic.** This is the subtle part. It is tempting to say:

- "VIX and VVIX are both equity-vol indices → same class."
- "WTI and Brent are both crude spot → same class."
- "CPI and PCE are both US inflation prints → same class."

**/trader caveat: this is often wrong.** Class membership is a statistical question, answered by testing whether the two symbols' `|deviation|` distributions pool without shifting the p95 rank by more than some tolerance. Test with Kolmogorov–Smirnov or Anderson–Darling; reject pooling on failure.

- **VIX vs VVIX.** VIX measures 30-day S&P 500 implied vol. VVIX measures the implied vol *of VIX itself* — vol of vol. The distributions have different tails, different regime structure, different jump behavior. VVIX routinely spikes on days VIX barely moves. **Likely fails the pooling test.**
- **WTI vs Brent.** 95% of the time they move together and pool fine. But during pipeline events (Aramco attack, Druzhba contamination), one can gap 10% while the other moves 2%. **Pooling works most days, fails exactly when it matters most.**
- **CPI vs PCE.** Different reference bases, different surprise distributions. Pool-validation is non-obvious.

**Realistic INVEX universe size.** A naive asset-taxonomy pooling gives 15–30 classes. An empirically validated pooling (with KS rejection) probably gives **30–50 classes** across equity IV, rate vol, crude spot, gold, FX pairs, inflation prints, growth prints, employment prints, correlation pairs. The registry needs to absorb that, not be fixed-size.

**Bottom line.** Classes are defined by distributional equivalence under deviation, proven by test — not by "they look similar to a human."

---

## 17. Window-Degeneracy Guard (replaces per-class `D`)

A global check that the history window has enough distinct values for the ECDF rank to be meaningful, regardless of dispersion shape.

**The pathology.** Suppose OVX has been trading in a range of 22.0 to 22.3 for 60 days — flat regime. A modest move to 22.5 ranks above every one of the 60 history points → **ECDF rank = 1.0, severity = 1.0**. The classifier screams. The market yawns.

**The guard (ADR-0002, 2026-04-27 amendment).** Compute the count of distinct values in the history window after rounding to 4 decimals. If that count is below a global threshold `k_min` (= 10), the history is declared degenerate:

- The classifier returns a **CLS-009 degraded-confidence response** instead of the raw ECDF severity.
- `computed_metrics.window_degenerate = true` so the composite (CLS-002) can exclude it deterministically.

**Why `k_min` and not a per-class IQR floor (`D`).** A defensible empirical-p5 estimate of an IQR distribution requires ≥ 200 non-overlapping IQR observations, i.e. `200 × N` raw points. For monthly inflation at `N = 60`, that is 1,000 years of data — unreachable. Any per-class `D` set without that data is a placeholder, not a calibrated parameter. The `k_min` threshold instead is sample-size independent and distribution-free: 10 distinct values is the resolution floor below which a percentile rank cannot resolve finer than 10 percentage points, period. `/statistician` rejects per-class `D` calibration at the available sample sizes; `/trader` accepts the global threshold because it lines up with desk experience for what counts as "enough variation to call a tail."

**Why rounding to 4 decimals.** Matches the significance of the inputs — FRED daily closes carry 2 decimals, pct-change `|deviation|` carries at most 4–5 significant decimals after division. Rounding to 4 squashes float noise without conflating genuinely distinct values.

**Trade-off made explicit.** The guard introduces false-negatives in genuine slow-burn regime-change events (OVX grinding upward from 22 to 25 over a month, all distinct values). It will *not* trip then, because the history has plenty of distinct values — that is the correct behaviour, those grinds should produce real ranks. The guard's only job is to catch the pathological case where the history has structurally collapsed.
