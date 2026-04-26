"""
Window-degeneracy guard for CLS-009 (RULE_BASED degraded-confidence fallback).

When the rolling history of `|deviation|` collapses to fewer than `_K_MIN`
distinct values (after rounding to `_ROUND_NDIGITS` decimals), the ECDF
rank is not informative regardless of distribution shape. The strategy
emits a degraded response in that case rather than a misleading
high-severity signal.

ADR-0003 supersedes the earlier per-class `D` (rolling-IQR floor): a
global degeneracy check is sample-size independent and distribution-free,
which the per-class threshold could not be at the sample sizes available
for monthly / weekly series. `rolling_iqr` is retained as a diagnostic
statistic exposed in `computed_metrics` for trader inspection; it no
longer drives any guard.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

# IQR is undefined for fewer than two samples; degenerate windows return 0.0.
_MIN_SAMPLES_FOR_IQR = 2

# Global window-degeneracy parameters (ADR-0003). A percentile rank over
# fewer than 10 distinct values has resolution coarser than 10 percentage
# points; below that the rank is not informative regardless of the
# underlying distribution. Rounding precision matches the significance of
# our inputs (FRED daily closes, pct-change `|deviation|` carrying at most
# 4-5 significant decimals).
_K_MIN = 10
_ROUND_NDIGITS = 4


def rolling_iqr(history: Iterable[float]) -> float:
    """Interquartile range (Q3 - Q1) of `history`.

    Returns 0.0 for empty or single-element history. Diagnostic only;
    the CLS-009 guard is `is_window_degenerate`, not an IQR threshold.
    """
    history_list = list(history)
    if len(history_list) < _MIN_SAMPLES_FOR_IQR:
        return 0.0
    arr = np.asarray(history_list, dtype=float)
    q1, q3 = np.percentile(arr, [25, 75])
    return float(q3 - q1)


def is_window_degenerate(history: Iterable[float]) -> bool:
    """True iff the window has fewer than `_K_MIN` distinct values after rounding.

    Caller emits CLS-009 degraded response. Single global threshold; no
    per-class tuning. See ADR-0003.
    """
    distinct = {round(v, _ROUND_NDIGITS) for v in history}
    return len(distinct) < _K_MIN
