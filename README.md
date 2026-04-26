# DeltaFeed

A two-part repository:

- **INVEX** — a volatility-exploitation trading system (the carrier)
- **DeltaFeed** — a research harness measuring how AI coding agents perform
  when architecture is treated as a controlled variable

INVEX exists so DeltaFeed has something real to measure. A toy example
produces toy results; a production-shaped system with a stable external
contract, live data feeds, and domain-informed acceptance criteria exposes
the decisions agents actually struggle with — wrong-level abstractions,
contract drift, shortcut refactors across module boundaries.

---

## DeltaFeed — the research instrument

**Question.** Given the same external contract and the same requirements,
does the architecture an agent is asked to work within materially change the
correctness, cost, and maintainability of its output?

**Method.** Reimplement the same system under six named architecture
paradigms. Hold the agent context, the API contract, the acceptance suite,
the feedback protocol, and the tooling baseline constant. Vary only the
architectural constraints.

**Components**

- **Architecture as constraint space** — six paradigms spanning procedural to
  distributed (transaction script, vertical slices, clean architecture with
  rich domain, event sourcing, modular monolith, service extraction).
- **Fitness functions for structure** — executable assertions about layering,
  dependency direction, complexity, and typing (Ford/Parsons/Kua lineage;
  ArchUnit / import-linter / NetArchTest family). Tool-configured, not
  hand-coded per bug.
- **Black-box acceptance tests** — contract-driven, grounded in
  consumer-driven contract practice (Pact lineage). Assertions are contract
  shapes plus domain bands on trader-curated reference scenarios; never
  implementation internals.
- **Bounded-retry feedback loop** — structured failure reports, fixed retry
  budget, no out-of-band hints.

**Scoring.** Three axes per iteration: structural compliance (fitness
functions green), functional correctness (acceptance suite green),
operational cost (tokens, wall time, retries).

---

## INVEX — the system being measured

INVEX consumes market data, macroeconomic releases, geopolitical events, and
cross-asset flows; produces a signal-implied volatility forecast; compares
that forecast against observed implied volatility; and, when the dislocation
is large enough, constructs convex options positions sized to cap downside at
allocated capital while preserving asymmetric upside.

Pipeline:

1. Signal ingestion (.NET) — Twelve Data WebSocket, FRED polling, GDELT polling
2. Classification (Python) — per-signal severity and certainty
3. Composite scoring (.NET, CLS-002)
4. IV dislocation detection (.NET, CLS-006)
5. Deploy decision (.NET, DEC-001)
6. Position management (.NET, POS-001)
7. Exit (.NET, EXT-001)

The six iterations each reimplement the .NET side. Requirements live in
[doc/srs/INVEX-SRS-v2.3.2.md](doc/srs/INVEX-SRS-v2.3.2.md); the external
contract is [doc/INVEX-API-v1.yaml](doc/INVEX-API-v1.yaml). Neither changes
across iterations.

| # | Iteration | Relationship |
| --- | --- | --- |
| 1 | Transaction Script | Baseline — every Must requirement, procedural |
| 2 | Vertical Slice Architecture | Refactor of 1, sliced by use case |
| 3 | Clean Architecture + Rich Domain | Rewrite — invariants in entities |
| 4 | Clean Architecture + Event Sourcing | Refactor of 3, append-only event log |
| 5 | Modular Monolith | From 3, enforced module boundaries |
| 6 | Service Extraction | Decomposition of 5, decision engine extracted |

---

## Classification service — constant infrastructure

The Python service at [apps/classification/](apps/classification/) is
deliberately not under measurement. It is shared by every .NET iteration. If
it varied, the measurement could not distinguish "iteration 4 scored better
because event sourcing fits" from "iteration 4 scored better because the
classifier was more accurate that week."

The service owns all classification intelligence — ECDF-based severity,
surprise magnitudes, correlation deviations, LLM-judged event severities. The
.NET pipeline calls `POST /classify` and does not reason about statistical
methods.

**Contract.** [apps/classification/doc/openapi.yaml](apps/classification/doc/openapi.yaml)
(OpenAPI 3.1). Responses carry a score in `[0.0, 1.0]`, a `score_type`
discriminator (`ANOMALY_DETECTION` vs. `EVENT_ASSESSMENT`), a certainty
composed of source-reliability and temporal-relevance dimensions, and a
reasoning trace.

**Strategies.** Five, dispatched by `source_category` and `payload_type`:

| Route | Method | What it computes |
| --- | --- | --- |
| `MARKET_DATA` + `STRUCTURED` | Rule-based | ECDF rank vs. rolling level window (VIX, OVX) |
| `MACROECONOMIC` + `STRUCTURED` | Rule-based | ECDF rank of YoY surprise vs. historical surprise distribution |
| `CROSS_ASSET_FLOW` + `STRUCTURED` | Rule-based | Correlation deviation vs. baseline across a six-asset basket |
| `GEOPOLITICAL` + `STRUCTURED` | AI model | Rule score plus LLM enrichment |
| `GEOPOLITICAL` + `UNSTRUCTURED` | AI model | LLM extraction with RAG context |

**Harness.** Lives under [apps/classification/tests/](apps/classification/tests/):

- `acceptance/` — contract-shape tests against `doc/openapi.yaml` and
  anchor-event tests on trader-curated historical scenarios. Source provenance
  is strict (FRED, BLS, Twelve Data, Finnhub); no synthetic seed windows.
- `architecture/` — import-linter layering, ruff hygiene, mypy strict,
  xenon complexity ceilings, vulture dead-code detection.
- `integration/` — live-API bootstrap, skipped when API keys absent.

ADRs in Michael Nygard format under
[apps/classification/doc/adr/](apps/classification/doc/adr/). Framework
overview in [apps/classification/HARNESS.md](apps/classification/HARNESS.md).

---

## Further reading

- [AGENTS.md](AGENTS.md) — repository-level conventions for AI agents
- [apps/classification/AGENTS.md](apps/classification/AGENTS.md) — service-local conventions
- [apps/classification/HARNESS.md](apps/classification/HARNESS.md) — harness framework and test inventory
- [apps/classification/doc/adr/](apps/classification/doc/adr/) — architectural decision records
- [doc/srs/INVEX-SRS-v2.3.2.md](doc/srs/INVEX-SRS-v2.3.2.md) — full requirements
- [doc/INVEX-API-v1.yaml](doc/INVEX-API-v1.yaml) — external .NET API contract
