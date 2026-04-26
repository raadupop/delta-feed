# infra/

Shared infrastructure artifacts read by multiple INVEX components.

## Contents

- **`registry.yaml`** — Indicator registry. Single source of truth for the
  Python classifier (`apps/classification/`) and the .NET ingestion job
  (future iterations). Governs ECDF calibration parameters per indicator
  class, symbol → class resolution, and bootstrap provider/series mapping.
  Schema and decision rationale in
  [ADR-0002](../apps/classification/doc/adr/0002-ecdf-severity-and-backtest-harness.md).

## Schema

```yaml
classes:
  <class_name>:
    N:                          int   # history-window length
    D:                          float # minimum-informative-dispersion floor
    deviation_kind:             enum  # pct_change | surprise_yoy | corr_delta
    expected_frequency_seconds: int   # normal update cadence

symbols:
  <symbol>:
    class:     <class_name>
    bootstrap:                        # optional — startup history pull
      provider:  enum                 # fred | finnhub | twelve_data
      series_id: str                  # provider-specific identifier
      derive:    enum (optional)      # pct_change_yoy | none
      verified:  bool                 # false → bootstrap skips with warning
```

Symbols without a `bootstrap` block are registered for class membership
only; their windows populate from live `/classify` traffic instead of a
startup pull. `verified: false` flags series IDs the operator has not
confirmed against the provider — the loader accepts the entry but the
bootstrap function skips it with a warning, so unverified guesses cannot
silently pollute history with wrong data.

## Why this folder

The registry is a **shared contract** between Python and .NET. Putting it
under `apps/classification/` would imply the classifier owns it; putting
it under a future `dotnet/` folder would imply the ingestion job owns it.
Neither is true. The registry is a configuration artifact at the same
level of authority as the OpenAPI specs in `doc/`, and lives at the repo
boundary between the two consumers.

## Reload semantics

Files in this folder are read **once at process startup** by their
consumers. Changes require restart. Hot-reload is deferred Phase-2 work
per the chief-architect review (see
[doc/session-notes/2026-04-26-classifier-architecture-three-questions.md](../doc/session-notes/2026-04-26-classifier-architecture-three-questions.md)).

## Approval gate

Changes to `registry.yaml` are trading-risk decisions. PR review by
`/trader` is required before merge for:

- Adding a new indicator class
- Adding a symbol to an existing class
- Tuning `N` or `D` for an existing class
- Changing `deviation_kind` (this is a structural break — should be a new
  class, not a mutation)
