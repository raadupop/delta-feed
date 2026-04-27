# Python naming conventions

Treat Python names with the same care as .NET file/type names. A reader who
has never seen the code should be able to guess return type and effect
from the name alone.

## Module filenames

Module filename describes the primary export, not a bare noun or
abbreviation. If a .NET dev would write `FredFetcher.cs`, the Python file
is `fred_fetcher.py`, not `fred.py`.

**Banned** (unless the export is genuinely that broad):

- `service.py`, `utils.py`, `helpers.py`, `common.py`, `core.py`, `base.py`
- Single-word vendor names: `fred.py`, `finnhub.py`, `stripe.py` —
  acceptable *only* when the containing package supplies the role
  (`app/clients/fred.py`, `app/adapters/stripe.py`). At the top of a
  package or alongside unrelated modules, add the role suffix
  (`fred_fetcher.py`).
- Single-word verbs: `transforms.py`, `handlers.py`, `consumers.py`

**Preferred:**

- `fred_fetcher.py` (exports `fetch_window`)
- `window_builders.py` (exports `build_*_window` functions)
- `cpi_consensus.py` (exports `CPI_CONSENSUS_YOY`)
- `order_validator.py`, `quote_publisher.py`

If a module exports one class, name it `snake_case` of the class
(`OrderValidator` → `order_validator.py`). If it exports a small family of
related functions, name it after the family + role
(`window_builders.py`).

## Function and method names

**Banned: naming functions after enum or discriminator tags.**

A function named after a registry tag (`deviation_kind == "pct_change"`)
describes the dispatch key, not the behavior, and almost always misleads.

Real examples from this codebase:

| Current name              | What it actually does                                                            | Correct name                |
| ------------------------- | -------------------------------------------------------------------------------- | --------------------------- |
| `_fetch_pct_change`       | Fetches a level series                                                           | `_fetch_level_series`       |
| `build_pct_change_window` | Builds a level window                                                            | `build_level_window`        |
| `pct_change_deviation`    | Returns `\|current - median(history)\|`                                          | `level_vs_median_deviation` |
| `surprise_yoy_deviation`  | Returns `\|actual - expected\|` (YoY happens upstream when `expected` is computed) | `surprise_deviation`        |

The pattern: the function name describes the *output*, not the
discriminator branch that selected it.

## Pre-edit self-check

Before writing or accepting any new function/method/class/module name,
ask:

1. **Does the name describe what it produces, not what dispatched to it?**
   If the name matches an enum value, registry tag, config key, or
   strategy-pattern discriminator, it's wrong. Rename to the output.
2. **Could a .NET dev read this name and guess the return type or
   effect?** `pct_change_deviation` fails this — sounds like "deviation
   of a pct change," actually returns `|current - median(history)|`.
3. **Is there a hidden noun-phrase being abbreviated?** If the function
   name keeps only the adjective from a discriminator and drops the noun,
   it will mislead. Add the noun back.

If any answer is unclear, stop and rename before finalizing the edit.

## Fixing existing violations

Existing bad names are fixed when adjacent code is touched in the normal
course of work — not as a standalone refactor. The `pct_change_deviation`
and `surprise_yoy_deviation` functions in
[apps/classification/app/math/deviation.py](../../apps/classification/app/math/deviation.py)
are the known-violations queue at the time of writing.
