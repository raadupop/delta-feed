"""Pure functions that shape raw provider series into `WindowSeed` values.

No I/O, no logging, no settings access — every input is explicit so these
functions can be unit-tested without mocks. Provider modules call into here
after they have decoded the upstream response into plain Python lists.
"""
from datetime import datetime

from app.bootstrap.provider_fetcher import WindowSeed


def build_level_window(
    levels: list[float],
    dates: list[datetime],
    n: int,
) -> WindowSeed | None:
    """Take the last `n` raw level values for `pct_change` indicator classes.

    Returns `None` if `levels` is empty.
    """
    if not levels or not dates:
        return None
    values = [float(v) for v in levels[-n:]]
    return WindowSeed(values=values, last_update=dates[-1])


def build_yoy_surprise_window(
    monthly_levels: list[float],
    dates: list[datetime],
    consensus: dict[str, float],
    n: int,
) -> WindowSeed | None:
    """Build |actual - expected| surprises for `surprise_yoy` classes.

    `monthly_levels` is a level series sampled monthly. We compute YoY
    percent change at each month, look up consensus by `YYYY-MM` key, and
    keep the absolute deviation. Returns `None` if no overlap with
    `consensus` or fewer than 12 months of data.
    """
    months_per_year = 12
    if len(monthly_levels) <= months_per_year:
        return None

    surprises: list[float] = []
    last_yoy_date: datetime | None = None
    for i in range(months_per_year, len(monthly_levels)):
        prev = monthly_levels[i - months_per_year]
        if prev == 0:
            continue
        yoy_pct = (monthly_levels[i] / prev - 1.0) * 100.0
        date = dates[i]
        key = date.strftime('%Y-%m')
        expected = consensus.get(key)
        if expected is None:
            continue
        surprises.append(round(abs(round(yoy_pct, 1) - expected), 1))
        last_yoy_date = date

    recent = surprises[-n:]
    if not recent or last_yoy_date is None:
        return None
    return WindowSeed(values=recent, last_update=last_yoy_date)
