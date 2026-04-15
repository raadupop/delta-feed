# Invex.Classification — Python Classification Service

Stateless HTTP classification engine. Receives signal payloads from the .NET API, routes to the appropriate strategy by source category, returns score + certainty. The `score_type` discriminator tells the consumer whether the score is a statistical anomaly measure or an LLM-judged event impact.

Constant across all six .NET architecture iterations. Not part of the measurement framework.

## Contract

### POST /classify

**Request:**
```json
{
  "source_category": "MARKET_DATA | MACROECONOMIC | GEOPOLITICAL | CROSS_ASSET_FLOW",
  "payload_type": "STRUCTURED | UNSTRUCTURED",
  "structured_payload": { },
  "unstructured_payload": { "text": "...", "language": "en", "source_url": "..." }
}
```

Payloads match the OpenAPI spec schemas: MarketDataPayload, MacroeconomicPayload, GeopoliticalPayload, CrossAssetFlowPayload, UnstructuredPayload. The .NET ingestion job sends raw data — no pre-computed z-scores or surprise magnitudes.

**Response:**
```json
{
  "score": 0.82,
  "score_type": "ANOMALY_DETECTION | EVENT_ASSESSMENT",
  "certainty": 0.71,
  "source_reliability": 0.90,
  "temporal_relevance": 0.79,
  "event_taxonomy": "RATE_SURPRISE",
  "classification_method": "AI_MODEL | RULE_BASED",
  "reasoning_trace": "VIX jumped 47% vs 20-day mean, z-score 6.2...",
  "computed_metrics": {
    "z_score": 6.2,
    "baseline_mean": 15.1,
    "baseline_std": 2.0
  }
}
```

- `score`: 0.0–1.0. Classification score. Semantics depend on `score_type`.
- `score_type`: discriminator telling the consumer what the score represents.
  - `ANOMALY_DETECTION`: statistical deviation from rolling baseline (z-score, surprise magnitude). Produced by MARKET_DATA, MACROECONOMIC, CROSS_ASSET_FLOW.
  - `EVENT_ASSESSMENT`: LLM-judged event impact. Produced by GEOPOLITICAL structured and unstructured.
- `certainty`: 0.0–1.0. Combined certainty composed of two independent dimensions: source reliability (accuracy/trustworthiness of the source) and temporal relevance (whether the market has already priced this signal). Both quantified independently and combined (SRS CLS-001).
- `source_reliability`: 0.0–1.0. Optional. Source reliability dimension of certainty, provided when computed independently.
- `temporal_relevance`: 0.0–1.0. Optional. Temporal relevance dimension — 1.0 means market has not yet absorbed the signal.
- `event_taxonomy`: nullable. Not all strategies produce one.
- `classification_method`: self-describing. AI_MODEL for LLM strategies, RULE_BASED for statistical.
- `reasoning_trace`: always present. Audit trail.
- `computed_metrics`: strategy-specific intermediate values (z_score, baseline, surprise_magnitude, etc.). The .NET app uses these to populate OpenAPI response fields like CrossAssetFlowPayload.z_score.

## Architecture Responsibility Split

The classifier owns **all classification intelligence**. The .NET ingestion job is thin plumbing.

| .NET ingestion job | Python classifier |
|---|---|
| WebSocket subscription (Twelve Data) | Rolling windows (in-memory, bootstrapped from APIs) |
| FRED/GDELT polling | Z-score computation |
| Raw data → SignalInput shaping | Surprise magnitude computation |
| Signal storage | Correlation deviation scoring |
| Composite scoring (CLS-002) | GEOPOLITICAL rule scoring + LLM calls |
| IV dislocation (CLS-006) | RAG retrieval (GEOPOLITICAL unstructured) |
| Response validation + fallback (CLS-004) | Severity/certainty mapping |
| Monitoring alerts (CLS-008) | Reasoning trace generation |

## Startup Bootstrap

On startup, the classifier pulls historical data from public APIs to populate in-memory rolling windows:

- **Twelve Data**: last 20 days VIX/OVX closes (MARKET_DATA window), last 60+ days basket prices for correlation computation (CROSS_ASSET_FLOW window)
- **Finnhub**: istorical actual/estimate pairs (MACROECONOMIC window)
- **Twelve Data**: 60 days of daily closes for basket (CROSS_ASSET_FLOW)

No persistent storage. No SQLite. No seed files in production. The service is self-bootstrapping on every deploy.

A `/health` endpoint reports "not ready" until all windows are populated. The .NET app checks health before routing signals. Startup retries with backoff if APIs are unavailable.

**Seed files exist only for tests** — deterministic fixtures under `tests/fixtures/` that replace API bootstrap, ensuring reproducible test runs.

Each incoming `POST /classify` updates the relevant rolling window (append new value, drop oldest).

## Strategies

Five strategies, routed by `source_category` + `payload_type`:

| Route | Strategy | Method | What it computes |
|---|---|---|---|
| MARKET_DATA + STRUCTURED | Z-score anomaly detection | RULE_BASED | Current value vs 20-day rolling window mean/std |
| MACROECONOMIC + STRUCTURED | Surprise magnitude scoring | RULE_BASED | \|actual − expected\| / historical_std of surprises |
| CROSS_ASSET_FLOW + STRUCTURED | Correlation deviation scoring | RULE_BASED | Pairwise correlations vs 60-day baseline z-score |
| GEOPOLITICAL + STRUCTURED | Rule scoring + LLM enrichment | AI_MODEL | severity_estimate + event_type → rule score → LLM reasoning |
| GEOPOLITICAL + UNSTRUCTURED | LLM extraction + RAG context | AI_MODEL | Full text → LLM + RAG → score (EVENT_ASSESSMENT) + certainty |

Routing: dispatch on `source_category`, GEOPOLITICAL splits on `payload_type`. The Python service owns routing — the .NET caller does not specify strategy.

## Data Sources

### Real-time (production — consumed by .NET ingestion job, not the classifier)

| Category | Source | Frequency | Cost |
|---|---|---|---|
| MARKET_DATA (VIX, OVX) | Twelve Data WebSocket | Streaming (~170ms) | Free tier |
| MARKET_DATA (basket prices) | Twelve Data WebSocket | Streaming | Free tier |
| MACROECONOMIC | FRED API + Finnhub calendar | On-release (scheduled) | Free |
| CROSS_ASSET_FLOW | Derived from Twelve Data basket | Computed by .NET job | Free tier |
| GEOPOLITICAL structured | GDELT Events | 15-min cycle | Free |
| GEOPOLITICAL unstructured | GDELT DOC API | 15-min cycle | Free |

### Bootstrap (consumed by classifier on startup)

| Window | Source | Lookback |
|---|---|---|
| MARKET_DATA rolling window | Twelve Data REST API | 20 days VIX/OVX daily |
| CROSS_ASSET_FLOW baseline | Twelve Data REST API | 60+ days basket daily |
| MACROECONOMIC surprise baseline | Finnhub | ~30 releases historical actual/estimate pairs |

### CROSS_ASSET_FLOW Basket

| Ticker | Asset class |
|---|---|
| SPY | US equities |
| TLT | US treasuries (bonds) |
| GLD | Gold (precious metal) |
| USO | Crude oil (commodity) |
| EEM | Emerging markets equities |
| UUP | US dollar |

## LLM Dependency

Claude API (Sonnet) for the two GEOPOLITICAL strategies only. All other strategies are pure computation.

## RAG Store

Minimal ChromaDB corpus for GEOPOLITICAL unstructured strategy. Contains:
- Event type reference definitions
- Region risk profiles
- Historical severity benchmarks

Seeded from files under `data/rag/`. Read-only at runtime. LangChain orchestrates retrieval → prompt → structured extraction.

## Test Suite — 10 Historical Events

Two per strategy. Each event is a JSON fixture under `tests/fixtures/`. Tests use seed files (not live API calls) to bootstrap windows. Assertions on score, score_type, and certainty with exact values.

| # | Strategy | Event | Date | Score Type | Expected Score |
|---|---|---|---|---|---|
| 1 | MARKET_DATA | Volmageddon — VIX 10→37 (FRED close) | 2018-02-05 | ANOMALY_DETECTION | ~0.88 |
| 2 | MARKET_DATA | COVID first spike — VIX 17→25 | 2020-02-24 | ANOMALY_DETECTION | ~0.31 |
| 3 | MACROECONOMIC | CPI YoY 9.1% vs 8.6% expected — peak inflation | 2022-07-13 | ANOMALY_DETECTION | ~0.87 |
| 4 | MACROECONOMIC | CPI YoY 6.9% vs 6.7% expected — inflation ramp | 2021-12-10 | ANOMALY_DETECTION | ~0.49 |
| 5 | CROSS_ASSET_FLOW | China devaluation flash crash | 2015-08-24 | ANOMALY_DETECTION | ~0.80 |
| 6 | CROSS_ASSET_FLOW | SVB collapse flight-to-quality | 2023-03-10 | ANOMALY_DETECTION | ~0.70 |
| 7 | GEO structured | Russia invades Ukraine | 2022-02-24 | EVENT_ASSESSMENT | ~0.90 |
| 8 | GEO structured | Hamas attack on Israel | 2023-10-07 | EVENT_ASSESSMENT | ~0.85 |
| 9 | GEO unstructured | Abe assassination (news text) | 2022-07-08 | EVENT_ASSESSMENT | ~0.55 |
| 10 | GEO unstructured | Evergrande default fears (analyst report) | 2021-09-20 | EVENT_ASSESSMENT | ~0.70 |

## Tech Stack

- **Framework:** FastAPI
- **Validation:** Pydantic v2
- **Statistical:** numpy
- **LLM:** anthropic SDK (Claude Sonnet)
- **RAG:** LangChain + ChromaDB
- **Tests:** pytest + pytest-asyncio
- **Bootstrap data:** Twelve Data REST + FRED API (fredapi)

## Build Order

1. ✅ AGENTS.md (this file; formerly CLAUDE.md)
2. Project scaffold — FastAPI app, Pydantic models, strategy routing, health endpoint
3. MARKET_DATA strategy — z-score anomaly computation + bootstrap logic + tests
4. MACROECONOMIC strategy — surprise magnitude scoring computation + bootstrap logic + tests
5. CROSS_ASSET_FLOW strategy — correlation z-score + bootstrap logic + tests
6. GEOPOLITICAL structured — rule scoring + LLM enrichment + tests
7. GEOPOLITICAL unstructured — LangChain + RAG + LLM extraction + tests
8. Integration tests against all 10 historical events

**Current step: 5 — CROSS_ASSET_FLOW strategy**

## Contract & Acceptance

The authoritative machine-readable contract for this service is
[`doc/openapi.yaml`](doc/openapi.yaml) (OpenAPI 3.1). The prose in the
"Contract" section above is informative; the YAML is normative.

- **Acceptance tests** under `tests/acceptance/` replay anchor events against
  `POST /classify` and validate responses against `doc/openapi.yaml`.
  `tests/acceptance/fixtures/ANCHORS.md` is the trader-reviewed catalogue.
- **Source-provenance rule.** Every fixture value — seed windows, `actual`,
  `expected`, price points — must trace to a verifiable public provider
  (FRED series id, BLS release, Twelve Data, Finnhub, Reuters/Bloomberg
  consensus archive). No synthetic or interpolated values. An anchor that
  cannot cite provenance fails review.
- **Fitness-function suite** under `tests/architecture/` enforces
  architectural invariants using standard Python tooling — `import-linter`
  (layering), `ruff` (magic numbers, DRY, complexity), `mypy --strict`
  (typing at boundaries), `xenon` (McCabe), `vulture` (dead code). Config
  lives in `pyproject.toml`. Strategy files may not define module-level
  numeric tuning constants; tuning is sourced per-indicator (Phase B moves
  it into the request payload). See `HARNESS.md` for the framework and
  `doc/adr/` for architectural decisions and postmortem-style entries
  (Nygard format) — start with `doc/adr/0001-per-indicator-tuning-parameters.md`.

## .NET Integration

The .NET app calls this service over HTTP. The .NET side owns:
- Composite scoring (CLS-002 formula)
- IV dislocation (CLS-006 formula)
- Response validation + fallback (CLS-004)
- Monitoring alerts (CLS-008)
- WebSocket subscription and signal ingestion
- Signal storage and API serving

This service only classifies individual signals. Aggregation, storage, and serving are not its concern.