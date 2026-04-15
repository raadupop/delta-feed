# ANCHORS — Trader-Curated Reference Events

Reviewed catalogue of historical events used as black-box acceptance anchors.
One JSON fixture per row lives in this directory; the acceptance runner loads
them all via glob (`tests/acceptance/test_anchor_events.py`).

## Source-Provenance Rule (STRICT)

Every fixture value — seed window, `actual`, `expected`, price points,
correlations — MUST cite a verifiable public source. Each fixture carries a
`source` block with:

- `provider` — e.g. `FRED`, `BLS`, `Twelve Data`, `Finnhub`,
  `Bloomberg-consensus`, `Reuters-poll`.
- `series_id` / identifier (`VIXCLS`, `CUUR0000SA0`, `ICSA`, ...).
- `retrieved_at` — ISO timestamp of the data pull.
- `url` where applicable.

No invented, interpolated, or "synthetic but plausible" values. If a required
data point cannot be sourced, the anchor is **dropped**, not approximated.

## Status Legend

- **SOURCED** — data traces to a verifiable provider.
- **PENDING /trader** — data pulled from primary source but severity band and
  event categorization await sign-off by `/trader` skill review.
- **PENDING DATA PULL** — event identified, fixture scaffolded, awaits
  `/trader`-led extraction of real values from the cited provider.

## Catalogue

| # | Date | Strategy | Indicator / Symbol | Fixture | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2018-02-05 | MARKET_DATA | VIX | `market_data_vix_volmageddon_2018_02_05.json` | SOURCED, PENDING /trader | Volmageddon — VIX 10→37. Seed: FRED VIXCLS last 20 closes to 2018-02-02. |
| 2 | 2020-02-24 | MARKET_DATA | VIX | `market_data_vix_covid_first_spike_2020_02_24.json` | SOURCED, PENDING /trader | COVID first spike — VIX 17→25. Seed: FRED VIXCLS last 20 closes to 2020-02-21. |
| 3 | 2022-07-13 | MACROECONOMIC | CPI_YOY | `macro_cpi_yoy_peak_inflation_2022_07_13.json` | SOURCED, PENDING /trader | CPI YoY 9.1% vs 8.6% consensus. Surprise history from BLS releases 2019–2022. |
| 4 | 2021-12-10 | MACROECONOMIC | CPI_YOY | `macro_cpi_yoy_inflation_ramp_2021_12_10.json` | SOURCED, PENDING /trader | CPI YoY 6.9% vs 6.7%. Surprise history from BLS releases 2019–2021. |
| 5 | TBD | MACROECONOMIC | INITIAL_CLAIMS (weekly) | `macro_initial_claims_axis_exerciser.json` | PENDING DATA PULL | **Per-indicator-frequency axis exerciser** (ADR-0001). Weekly cadence vs monthly CPI. Must xfail(strict=True) until Phase B extracts per-indicator tuning from request payload. |

## Candidate Pool — Phase 1 Convexity Analysis

`doc/phase1_convexity_analysis.tsx` at repo root lists 24 VIX-spike events
2015–2025. That list is the *candidate pool* for future anchors — `/trader`
must re-verify each against the primary provider (FRED VIXCLS for VIX,
intraday exchange feeds for exact peak timing) before landing a fixture.
`windowHours` / `exploitable` flags from Phase 1 are ignored for classification
anchors: the classifier measures severity, not exploitability (those belong
to CLS-006 / DEC-001 on the .NET side).

Deferred for Phase B sign-off (strategies not yet implemented):

- 2015-08-24 China devaluation flash crash → CROSS_ASSET_FLOW
- 2023-03-10 SVB collapse → CROSS_ASSET_FLOW
- 2022-02-24 Russia invades Ukraine → GEOPOLITICAL structured
- 2023-10-07 Hamas attack on Israel → GEOPOLITICAL structured
- 2022-07-08 Abe assassination → GEOPOLITICAL unstructured
- 2021-09-20 Evergrande default fears → GEOPOLITICAL unstructured

## /trader Sign-off Checklist (per anchor)

1. Event is correctly categorized (strategy + indicator).
2. Seed window values match the cited provider at `retrieved_at`.
3. `expected_band` — score min/max — wide enough to survive reasonable
   recalibration (`tanh_scale` 18 → 22) but narrow enough to catch
   regressions. Explicit rationale per anchor.
4. Score-type, classification-method, source-reliability minima are correct
   for the strategy.
5. Anchors that depend on per-indicator divergence carry the
   `xfail(strict=True)` marker referencing `ADR-0001`.
