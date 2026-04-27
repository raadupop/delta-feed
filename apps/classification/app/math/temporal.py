"""
Temporal-relevance computation.

Shared by all RULE_BASED strategies (closes ADR-0001 Decision 4 — previously
duplicated in app/strategies/market_data.py and app/strategies/macroeconomic.py).

The expected update frequency and cadence (calendar-day vs business-day)
are sourced from the indicator class. Business-day cadence skips weekends
when measuring staleness — a Friday-close → Monday-close gap is one
business day, not three calendar days.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

import numpy as np

Cadence = Literal["business_day", "calendar_day"]


def compute_temporal_relevance(
    signal_time: datetime,
    last_update: datetime | None,
    expected_frequency_seconds: float,
    cadence: Cadence = "calendar_day",
) -> float:
    """Exponential decay of temporal relevance past the expected update cadence.

    - Returns 1.0 if `last_update` is None (first observation).
    - Returns 1.0 while elapsed-time <= `expected_frequency_seconds`.
    - Decays exponentially as staleness grows past the expected frequency.
    - When `cadence == "business_day"`, weekends are not counted as elapsed
      time (Fri-close → Mon-close is one business day).

    Result is rounded to 4 decimals for stable comparisons in tests / contracts.
    """
    if last_update is None:
        return 1.0
    if cadence == "business_day":
        elapsed_seconds = float(
            np.busday_count(last_update.date(), signal_time.date())
        ) * 86400.0
    else:
        elapsed_seconds = (signal_time - last_update).total_seconds()
    staleness = max(0.0, elapsed_seconds - expected_frequency_seconds)
    return round(math.exp(-staleness / expected_frequency_seconds), 4)
