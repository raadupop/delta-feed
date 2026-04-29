# Invex.Classification — Python Classification Service

Stateless HTTP classification engine. Receives signal payloads from the
.NET API over `POST /classify`, routes to the appropriate strategy by
`source_category` + `payload_type`, returns a signed score, certainty,
and reasoning trace.

Constant infrastructure across all six .NET architecture iterations. Not
under measurement.

This file is the agent-context onboarding doc for this component. It
holds only what lives nowhere else. Everything else is a pointer.

## Pointers (canonical sources)

| Concern | Canonical source |
|---|---|
| Contract (request/response shapes, score semantics) | [`doc/openapi.yaml`](doc/openapi.yaml) (normative) |
| Requirements (severity formula, certainty, composite, dislocation, exits) | [SRS](../../doc/srs/INVEX-SRS.md) — see CLS-001, CLS-002, CLS-003, CLS-004, CLS-006, CLS-008, CLS-009, EXT-004 |
| Harness framework (three layers, oracles, controls) | [`HARNESS.md`](HARNESS.md) |
| Architectural decisions and bug postmortems | [`doc/adr/`](doc/adr/) (Michael Nygard format) — start with [ADR-0003](doc/adr/0003-harness-architecture.md) for the harness, ADR-0001 / ADR-0002 for the calibration story |
| Trader-curated reference scenarios + band-derivation rule | [`tests/acceptance/fixtures/ANCHORS.md`](tests/acceptance/fixtures/ANCHORS.md) |
| Indicator registry (per-class `N_L`, `deviation_kind`, `expected_frequency_seconds`) | [`app/registry.py`](app/registry.py) and `data/registry/` (per ADR-0002) |

## Routing convention

Five strategies, routed by `source_category` + `payload_type`:

- **RULE_BASED** (`MARKET_DATA`, `MACROECONOMIC`, `CROSS_ASSET_FLOW`,
  all `STRUCTURED`) — compute signed ECDF-rank severity per SRS
  CLS-001. Sign encodes vol-expansion vs vol-compression per the
  per-strategy sign convention in SRS §3.
- **AI_MODEL** (`GEOPOLITICAL` `STRUCTURED` and `UNSTRUCTURED`) — emit
  `score_type = EVENT_ASSESSMENT` per SRS CLS-003. LLM-judged severity;
  not derived from a statistical distribution.

The Python service owns routing — the .NET caller does not specify
strategy. Unknown indicators trigger the CLS-009 degraded-confidence
fallback rather than silent zeros.

## Bootstrap

On startup the classifier pulls historical data from public APIs to
populate per-symbol long-horizon reference windows. Bootstrap depth is
**registry-derived** (per-class `N_L`); see ADR-0002. `/health` returns
"not ready" until all required windows populate; the .NET app gates on
that. No persistent storage. Seed files exist only for tests under
`tests/fixtures/`.

## .NET integration boundary

The Python service classifies individual signals. Aggregation, storage,
and serving live on the .NET side.

| .NET ingestion job | Python classifier |
|---|---|
| WebSocket subscription (Twelve Data) | Per-symbol long-horizon reference windows (in-memory, bootstrapped from public APIs) |
| FRED / GDELT polling | ECDF rank of `\|deviation_signed\|` |
| Raw data → SignalInput shaping | Surprise magnitude (MACROECONOMIC) |
| Signal storage | Correlation deviation (CROSS_ASSET_FLOW) |
| Composite scoring (CLS-002) | GEOPOLITICAL rule scoring + LLM calls |
| IV dislocation (CLS-006) | RAG retrieval (GEOPOLITICAL unstructured) |
| Response validation + fallback (CLS-004) | Severity + certainty mapping |
| Monitoring alerts (CLS-008) | Reasoning-trace generation |

This boundary is real and lives in no other doc.

## LLM dependency

Anthropic Claude API for the two `GEOPOLITICAL` strategies only. Every
other strategy is pure computation.

## RAG store

Minimal ChromaDB corpus for the `GEOPOLITICAL` unstructured strategy.
Contains event-type reference definitions, region risk profiles, and
historical severity benchmarks. Seeded from files under `data/rag/`,
read-only at runtime. LangChain orchestrates retrieval → prompt →
structured extraction.

## Tech stack

- **Framework:** FastAPI
- **Validation:** Pydantic v2
- **Statistical:** numpy
- **LLM:** anthropic SDK (Claude Sonnet)
- **RAG:** LangChain + ChromaDB
- **Tests:** pytest + pytest-asyncio
- **Bootstrap data:** Twelve Data REST + FRED API (fredapi) + Finnhub

## Conventions

Naming: see [doc/conventions/python-naming.md](../../doc/conventions/python-naming.md).
Functions and modules describe their *output*, not the discriminator
that dispatched to them. Run the pre-edit self-check before introducing
any new name.

Change history lives in [`doc/adr/`](doc/adr/).
