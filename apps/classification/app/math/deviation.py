"""
Deviation computation.

`indicator_class.deviation_kind` is a string in the registry; this module
maps it to the concrete `|deviation|` formula. Strategies pull the right
deviation kind from the symbol's class and call the matching function.

Per ADR-0002:
    | deviation_kind  | formula                                            |
    | --------------- | -------------------------------------------------- |
    | pct_change      | |current - rolling_median(history)|                |
    | surprise_yoy    | |actual - expected|                                |
    | corr_delta      | |pairwise_corr - rolling_baseline_corr|             |

Only `pct_change` and `surprise_yoy` are implemented today (CROSS_ASSET_FLOW
lands directly on this infrastructure in build-step 5; `corr_delta` will
follow the same pattern).
"""
from __future__ import annotations

from collections.abc import Iterable
from statistics import median


def pct_change_deviation(current_value: float, history: Iterable[float]) -> float:
    """|deviation| for level series (vol indices, prices).

    Uses median rather than mean to be robust to the same fat-tailed events
    we're trying to rank — mean-baseline severity self-suppresses on shocks.
    """
    history_list = list(history)
    if not history_list:
        return 0.0
    return abs(current_value - median(history_list))


def surprise_yoy_deviation(actual: float, expected: float) -> float:
    """|deviation| for surprise series (inflation, claims). History not used —
    the consensus IS the baseline."""
    return abs(actual - expected)
