"""
Temporal-relevance computation.

Shared by all RULE_BASED strategies (closes ADR-0001 Decision 4 — previously
duplicated in app/strategies/market_data.py and app/strategies/macroeconomic.py).

The expected update frequency is sourced from the indicator class
(`IndicatorClass.expected_frequency_seconds`) rather than a strategy-level
constant. This is the structural fix for ADR-0001's wrong-level modeling bug.
"""
from __future__ import annotations

import math
from datetime import datetime


def compute_temporal_relevance(
    signal_time: datetime,
    last_update: datetime | None,
    expected_frequency_seconds: float,
) -> float:
    """Exponential decay of temporal relevance past the expected update cadence.

    - Returns 1.0 if `last_update` is None (first observation).
    - Returns 1.0 while `signal_time - last_update <= expected_frequency_seconds`
      (signal arrived on or before the next expected tick).
    - Decays exponentially as staleness grows past the expected frequency.

    Result is rounded to 4 decimals for stable comparisons in tests / contracts.
    """
    if last_update is None:
        return 1.0
    staleness = max(
        0.0,
        (signal_time - last_update).total_seconds() - expected_frequency_seconds,
    )
    return round(math.exp(-staleness / expected_frequency_seconds), 4)
