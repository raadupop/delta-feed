"""
ECDF (empirical cumulative distribution function) rank.

Replaces tanh-of-z-score severity mapping per ADR-0002. Distribution-free,
regime-adaptive, paper-computable per indicator without a magic scale constant.
"""
from __future__ import annotations

from collections.abc import Iterable


def ecdf_rank(value: float, history: Iterable[float]) -> float:
    """Empirical-CDF rank of `value` against `history`.

    Returns the fraction of history values <= `value`, in [0, 1].
    Returns 0.0 for an empty history (caller's responsibility to short-circuit
    on insufficient data; this function is a pure mathematical primitive and
    doesn't carry domain semantics about "enough" history).
    """
    history_list = list(history)
    if not history_list:
        return 0.0
    n = len(history_list)
    count_le = sum(1 for h in history_list if h <= value)
    return count_le / n
