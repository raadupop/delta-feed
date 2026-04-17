# ADR-0002: ECDF severity mapping, two-parameter per-class calibration, and backtest harness layer

- **Status:** Accepted (design locked; implementation deferred to `/chief-architect` engagement)
- **Date:** 2026-04-18
- **Deciders:** Radu Pop
- **Supersedes:** —
- **Superseded by:** —
- **Relates to:** ADR-0001 (per-indicator tuning parameters)

## Context

During the 4-fixture axis-coverage work (OVX Aramco, VIX COVID mid-crisis,
VIX vol crush, VIX normal day) a structural problem in the acceptance suite
surfaced: the suite cannot catch a class of AI-generated bugs in which
tests and implementation co-evolve from the same wrong assumption. The
four fixtures collapsed to regression guards — their bands reflect whatever
the classifier currently outputs, because no cross-tech formula exists to
independently compute the "correct" severity.

Root cause: [CLS-001 in the SRS](../../../../doc/INVEX-SRS-v2.3.1.pdf) is
deliberately qualitative ("severity is quantified; certainty has two
independent dimensions combined somehow") with no formula. This is
intentional per Insight 7 (spec precision treated as an experimental
variable in DeltaFeed), but at the product layer it produces an
unfixable bug class: if the SRS does not specify how severity is
computed, an agent can encode any formula in the implementation and any
expected band in the test, and both pass trivially.

Three external inputs sharpened the diagnosis:

1. **`/trader` critique of fixed-scale `tanh`.** `tanh(|z| / _TANH_SCALE)`
   assumes a time-invariant distribution. No vol indicator has that across
   2017–2024. Window absorption and regime shifts silently degrade the
   mapping.
2. **`/trader` stress-test of OVX vs VIX under an ECDF replacement.** ECDF
   closes the *scale* gap (VIX 10–80 vs OVX supply-shock tails are
   normalised by rank within each indicator's own history). It does **not**
   close the *non-stationarity / event-clustering* gap: OVX's sparse-event
   history produces false p95 ranks on modest moves off a flat window, and
   autocorrelated post-event ramps mean the second identical shock ranks
   lower than the first because the window has absorbed the first.
3. **Market-reality oracle gap.** The acceptance suite oracle is the SRS
   contract. A separate oracle — what IV actually did after the event — is
   needed to catch the self-validating-loop class. Same fixture data, a
   different oracle, a different bug class. No duplication.

## Decision

Four co-decided pieces:

### 1. ECDF / percentile-rank mapping for all RULE_BASED strategies

Replace `severity = tanh(|z| / _TANH_SCALE)` with:

```text
severity = ecdf_rank(|deviation|) / N
```

over a per-indicator rolling history of length `N`, where `deviation`
depends on the strategy:

| Strategy | `deviation` |
| --- | --- |
| MARKET_DATA | `\|current − rolling_median\|` |
| MACROECONOMIC | `\|actual − expected\|` |
| CROSS_ASSET_FLOW | `\|pairwise_correlation − rolling_baseline_correlation\|` |

The mapping from `|deviation|` to severity is identical across strategies;
only the `deviation` variable differs. ECDF is distribution-free,
regime-adaptive, and paper-computable per indicator without a magic scale
constant.

**GEOPOLITICAL stays out.** EVENT_ASSESSMENT via LLM, severity not derived
from a statistical distribution, different oracle class entirely.

### 2. Two per-class parameters, not one

Per-indicator-class registry entries carry two parameters:

- **`N`** — history-window length.
- **`D`** — minimum-informative-dispersion floor. When rolling dispersion
  (IQR or std) of the history falls below `D`, the strategy emits a
  degraded-confidence signal (CLS-004 fallback shape) with
  `computed_metrics.dispersion_below_floor = true`, instead of inflating a
  modest move to p95 off a flat history. Guards quiet-regime false-highs
  (the OVX pathology).

One per-class parameter (`N` alone) is insufficient — `/trader` rejected
this explicitly. `D` is the minimum honest answer for the
non-stationarity / event-clustering gap.

### 3. Closed-universe indicator registry

The classifier does not own the indicator catalogue. A shared registry
maps `symbol → { indicator_class, N, D, deviation_kind }`. Approvals
gate additions (trader-reviewed). Unknown indicators trigger the CLS-004
degraded-confidence fallback rather than silent zeros.

### 4. Backtest harness — Layer A

A new harness layer with a market-reality oracle. Per-event assertions of
the form *"IV moved > 20% in the 48h after event X → severity must be ≥
0.7"*. Different oracle from the acceptance suite (SRS contract), so
different bug classes catch. Python-only, buildable today.

Layer B (system backtest, .NET replay of SRS §9's 10 events) is noted
here for completeness; scaffolding waits until the .NET iterations exist.

### Scope of the ECDF pivot

In scope: MARKET_DATA, MACROECONOMIC, CROSS_ASSET_FLOW (currently stubbed —
build-step 5 lands directly on ECDF, not on tanh-then-rewrite).

Out of scope: GEOPOLITICAL (LLM-judged).

## SRS requirements impacted

This ADR does not modify the SRS body (deferred to the next SRS
revision), but fixes the revision scope. Two requirements need rewriting:

- **CLS-001 — Per-signal classification.** Currently qualitative on
  severity ("severity is quantified"). Must become normative against
  the ECDF formula. The annex stub at
  [`srs-annex-cls-001-severity-formula.md`](srs-annex-cls-001-severity-formula.md)
  is the authoritative interim text; the next SRS revision folds it in.
- **SIG-001 — Signal source categories.** Currently defines the four
  source categories only. Must be extended (or complemented by a new
  sub-requirement SIG-001.1) with the **closed-universe indicator
  registry** constraint: within each source category, admissible
  indicators are those present in the registry, and the registry is the
  single source of truth for classifier bootstrap depth, ingestion-side
  subscription lists, and per-class ECDF calibration parameters (`N`,
  `D`, `deviation_kind`). Unknown indicators return a well-formed
  CLS-004 degraded-confidence response rather than an error.

Both revisions are carried by the `/chief-architect` engagement (see
`doc/research/chief-architect-briefing-harness-redesign.md`) and land
together with the ECDF implementation.

## Consequences

### Positive

- Magic `_TANH_SCALE` constants eliminated. Per-signal severity becomes
  paper-computable against the CLS-001 annex.
- CLS-001 shifts from Insight-7 category (b) qualitative to (a)
  quantitative — one qualitative data point lost among many, not a
  collapsed experimental variable. This is a principled statistical
  choice, not a test-passing workaround.
- Acceptance suite can catch formula misimplementation; backtest Layer A
  can catch calibration drift and the self-validating-loop class the
  acceptance suite structurally cannot see.
- CROSS_ASSET_FLOW (build-step 5) lands on the final formula first —
  avoids a tanh-then-rewrite cycle and its associated test churn.

### Negative / cost

- `/chief-architect` engagement required to design the full transition
  (ingestion contract, registry format, bootstrap reload semantics).
- Backtest suite becomes a required harness layer. New maintenance
  surface.
- One Insight-7 qualitative data point is spent (CLS-001 tightened).
  Acceptable — many others remain; this one collapsed under
  product-level pressure to eliminate the bug class.

### Ingestion-job impact (.NET side)

The registry is a shared artefact between the .NET ingestion job and the
Python classifier:

- **Bootstrap depth is registry-derived.** Some classes will need
  `N > 20` days, changing the Twelve Data / FRED / Finnhub REST pull
  shape at classifier startup.
- **Symbol → indicator-class mapping lives in the registry** and both
  sides must agree.
- **WebSocket subscription list (.NET side) becomes registry-derived** —
  only registered symbols stream.
- **Unknown symbols trigger the CLS-004 degraded-confidence fallback**
  across the HTTP boundary, not a silent zero.
- **No formula computation moves to .NET.** Plumbing stays thin. Only
  the registry-as-contract is new between the two services.

Registry ownership, file format, and reload semantics are a
`/chief-architect` decision.

### CROSS_ASSET_FLOW build-order impact

Step 5 (currently stubbed at
`apps/classification/app/strategies/cross_asset.py`) lands directly on
the ECDF formula. Anchor fixtures for the two CROSS_ASSET_FLOW events
(China deval 2015, SVB flight-to-quality 2023) will be authored against
the ECDF formula from the start.

## References

- Plan: `C:\Users\Radu\.claude\plans\structured-percolating-parrot.md`
- ADR-0001: [`0001-per-indicator-tuning-parameters.md`](0001-per-indicator-tuning-parameters.md)
- CLS-001 severity-formula SRS annex stub: [`srs-annex-cls-001-severity-formula.md`](srs-annex-cls-001-severity-formula.md)
- Limitations cross-reference: [`../../LIMITATIONS.md`](../../LIMITATIONS.md) #1, #3, #4, #5
- Harness framework: [`../../HARNESS.md`](../../HARNESS.md)
- `/chief-architect` briefing: `doc/research/chief-architect-briefing-harness-redesign.md`
- SRS: `doc/INVEX-SRS-v2.3.1.pdf` (CLS-001, CLS-004, §9 Validation Event Set)
- ADR format: Michael Nygard, *Documenting Architecture Decisions* (2011)
