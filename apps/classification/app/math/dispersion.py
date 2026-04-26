"""
Dispersion guard for CLS-009 (RULE_BASED degraded-confidence fallback).

When the rolling IQR of the history window falls below the indicator class's
`D` floor, ECDF ranks become unreliable: a modest move off a flat history
ranks at p95 not because it is genuinely surprising, but because the
reference distribution has collapsed. The strategy emits a degraded
response in that case rather than a misleading high-severity signal.

This is the OVX-quiet-regime pathology called out in ADR-0002.
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np

# IQR is undefined for fewer than two samples; degenerate windows return 0.0.
_MIN_SAMPLES_FOR_IQR = 2


def rolling_iqr(history: Iterable[float]) -> float:
    """Interquartile range (Q3 - Q1) of `history`.

    Returns 0.0 for empty or single-element history.
    """
    history_list = list(history)
    if len(history_list) < _MIN_SAMPLES_FOR_IQR:
        return 0.0
    arr = np.asarray(history_list, dtype=float)
    q1, q3 = np.percentile(arr, [25, 75])
    return float(q3 - q1)


def is_dispersion_below_floor(history: Iterable[float], floor: float) -> bool:
    """True iff rolling IQR < floor — caller emits CLS-009 degraded response."""
    return rolling_iqr(history) < floor
