# DeltaFeed

DeltaFeed is a two-part repository. The visible surface is a volatility-exploitation
trading system called **INVEX**; the research instrument it embeds is **DeltaFeed**, an
experimental harness for measuring how AI coding agents perform when
architecture is treated as a controlled variable rather than an emergent
outcome.

The trading system exists so DeltaFeed has something real to measure. A toy
example would produce toy results; a production-shaped system with a stable
external contract, live data feeds, and domain-informed acceptance criteria
exposes the decisions that agents actually struggle with — wrong-level
abstractions, premature optimization, contract drift, shortcut refactors
across module boundaries.

---

## DeltaFeed — the research instrument

DeltaFeed frames a question that the industry discusses anecdotally but rarely
measures: **given the same external contract and the same requirements, does
the architecture an agent is asked to work within materially change the
correctness, cost, and maintainability of its output?**

To isolate that effect, DeltaFeed fixes every other variable and reimplements
the same system under six named architecture paradigms. The agent context
(`AGENTS.md`, per-component), the external API contract
(`doc/INVEX-API-v1.yaml`), the acceptance suite derived from it, the feedback
protocol, and the tooling baseline are identical across iterations. Only the
architectural constraints change.

The instrument rests on four components, each drawn from established practice
rather than invented for this project:

- **Architecture as constraint space.** Six paradigms chosen to span the
  spectrum from procedural to distributed: transaction script, vertical
  slices, clean architecture with a rich domain, event sourcing, modular
  monolith, service extraction.
- **Fitness functions for structure.** Executable assertions about layering,
  dependency direction, complexity, and typing — lineage from Ford, Parsons,
  and Kua (*Building Evolutionary Architectures*) and the ArchUnit /
  import-linter / NetArchTest family. Rules are tool-configured, not
  hand-coded per bug.
- **Black-box acceptance tests.** Contract-driven tests grounded in
  consumer-driven contract practice (Pact lineage). Assertions are contract
  shapes plus domain bands on trader-curated reference scenarios, never
  implementation internals. This keeps the acceptance layer stable when
  internals are rewritten across iterations.
- **Bounded-retry feedback loop.** The agent receives a structured failure
  report (which fitness function, which acceptance case), a fixed retry
  budget, and no out-of-band hints. The loop terminates; the run is measured.

Every iteration is scored on three axes: structural compliance (fitness
functions green), functional correctness (acceptance suite green), and
operational cost (tokens, wall time, retries). Comparisons across paradigms
are what the experiment produces.

---

## INVEX — the system being measured

INVEX is an autonomous volatility-exploitation engine. It consumes market
data, macroeconomic releases, geopolitical events, and cross-asset flows;
synthesizes a signal-implied volatility forecast; compares that forecast
against the market's observed implied volatility; and, when the dislocation
is large enough to justify the trade, constructs convex options positions
(long straddles, long strangles, put spreads, call spreads) sized to cap
downside at allocated capital while preserving asymmetric upside.

The full pipeline:

1. **Signal ingestion** (.NET) — WebSocket streams (Twelve Data), FRED
   polling, GDELT polling
2. **Classification** (Python, see below) — per-signal severity and certainty
3. **Composite scoring** (.NET, CLS-002) — aggregation across classifier
   outputs
4. **IV dislocation detection** (.NET, CLS-006) — signal-implied vs.
   market-observed implied volatility
5. **Deploy decision** (.NET, DEC-001) — capital allocation gate
6. **Position management** (.NET, POS-001) — open and manage options
   structures
7. **Exit** (.NET, EXT-001) — close positions on thesis expiry or stop

The six architecture iterations each reimplement the .NET side of this
pipeline. Requirements are specified once in `doc/srs/INVEX-SRS-v2.3.2.md`; the
external contract is `doc/INVEX-API-v1.yaml`; neither changes across
iterations.

| # | Iteration | Relationship |
| --- | --- | --- |
| 1 | Transaction Script | Baseline — every Must requirement implemented procedurally |
| 2 | Vertical Slice Architecture | Refactor of 1, same features, sliced by use case |
| 3 | Clean Architecture + Rich Domain Model | Rewrite — domain invariants pushed into entities |
| 4 | Clean Architecture + Event Sourcing | Refactor of 3, append-only event log replaces mutable state |
| 5 | Modular Monolith | Sourced from 3, bounded contexts with enforced module boundaries |
| 6 | Service Extraction (Decision Engine) | Decomposition of 5, decision engine as separate service |

---

## Classification service — constant infrastructure

The Python classification service at `apps/classification/` is deliberately
not under measurement. It is constant infrastructure shared by every
.NET iteration. If it varied across iterations, the measurement could not
distinguish "iteration 4 scored better because event sourcing is a fit" from
"iteration 4 scored better because the classifier happened to be more
accurate that week."

The service owns all classification intelligence. The .NET ingestion job is
thin plumbing; the classifier is where z-scores, surprise magnitudes,
correlation deviations, and LLM-judged event severities are produced. The
.NET pipeline consumes the classifier's output via `POST /classify` and does
not reason about statistical methods.

**Contract.** `apps/classification/doc/openapi.yaml` (OpenAPI 3.1). Every
response is a score in `[0.0, 1.0]` with a `score_type` discriminator
(`ANOMALY_DETECTION` vs. `EVENT_ASSESSMENT`), a certainty composed of
source-reliability and temporal-relevance dimensions, and a reasoning trace.

**Strategies.** Five, dispatched by `source_category` and `payload_type`:

| Route | Method | What it computes |
| --- | --- | --- |
| `MARKET_DATA` + `STRUCTURED` | Rule-based | Z-score vs. 20-day rolling window (VIX, OVX) |
| `MACROECONOMIC` + `STRUCTURED` | Rule-based | Surprise magnitude vs. historical surprise distribution |
| `CROSS_ASSET_FLOW` + `STRUCTURED` | Rule-based | Correlation deviation vs. 60-day baseline across a six-asset basket |
| `GEOPOLITICAL` + `STRUCTURED` | AI model | Rule score plus LLM enrichment |
| `GEOPOLITICAL` + `UNSTRUCTURED` | AI model | LLM extraction with RAG context |

**Harness.** The service carries its own fitness-function layer and
contract-driven acceptance suite under `apps/classification/tests/`:

- `tests/acceptance/` — contract-shape tests (responses validate against
  `doc/openapi.yaml`) and anchor-event tests (trader-curated historical
  scenarios with strict source provenance from FRED, BLS, Twelve Data,
  Finnhub; no synthetic seed windows)
- `tests/architecture/` — import-linter layering contracts, ruff hygiene,
  mypy strict typing, xenon complexity ceilings, vulture dead-code detection
- `tests/integration/` — live-API bootstrap, skipped when API keys absent

Architectural decisions are recorded as ADRs under
`apps/classification/doc/adr/` in Michael Nygard format. The framework
document is `apps/classification/HARNESS.md`.

---

## Repository layout

```text
apps/
  classification/          Python / FastAPI classification service
    app/                   Strategies, routing, state, models
    doc/
      openapi.yaml         Service contract (OpenAPI 3.1)
      adr/                 Architectural decision records
    tests/
      acceptance/          Black-box contract + anchor-event tests
      architecture/        Fitness functions
      integration/         Live-API bootstrap
    HARNESS.md             Framework, inventory, gap map
    AGENTS.md              Service-local agent context
doc/
  srs/INVEX-SRS-v2.3.2.md  Software Requirements Specification (Markdown-native)
  INVEX-API-v1.yaml        External .NET API contract
  archive/                 Superseded binaries (v2.3.1 .docx/.pdf)
AGENTS.md                  Repository-level agent context
.github/
  copilot-instructions.md  Pointer to AGENTS.md for Copilot
```

---

## Status

- Classification service — acceptance, architecture, and
  integration test layers installed. Harness under ADR-0001 covers
  `_TANH_SCALE` / `_EXPECTED_FREQUENCY_SECONDS` wrong-level abstraction;
  remediation scheduled for Phase B (per-indicator parameters sourced at
  request time via the payload).
- .NET iterations — not yet started. Iteration 1 (Transaction Script) is
  next.
- DeltaFeed measurement framework — axes and scoring methodology defined in
  SRS; implementation pending the first two iterations to calibrate
  thresholds.

---

## Further reading

- `AGENTS.md` — repository-level conventions for AI agents
- `apps/classification/AGENTS.md` — service-local conventions
- `apps/classification/HARNESS.md` — harness framework and test inventory
- `apps/classification/doc/adr/` — architectural decision records
- `doc/srs/INVEX-SRS-v2.3.2.md` — full requirements
- `doc/INVEX-API-v1.yaml` — external .NET API contract
