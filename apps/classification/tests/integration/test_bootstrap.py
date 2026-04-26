"""
Integration test — verifies bootstrap against the real FRED API.

Skipped automatically when FRED_API_KEY is not configured.
Run explicitly with:  python -m pytest tests/integration/test_bootstrap.py -v
"""
import pytest

from app.bootstrap import populate_windows
from app.config import settings
from app.state import state

needs_api_key = pytest.mark.skipif(
    not settings.fred_api_key,
    reason="FRED_API_KEY not set",
)


@pytest.fixture(autouse=True)
def clean_state():
    state.windows.clear()
    state.is_ready = False
    yield
    state.windows.clear()
    state.is_ready = False


@needs_api_key
@pytest.mark.asyncio
async def test_bootstrap_populates_vix_and_ovx():
    """Bootstrap should populate both VIX and OVX with up to N daily closes from FRED."""
    await populate_windows()

    for symbol in ("VIX", "OVX"):
        assert symbol in state.windows, f"{symbol} window missing after bootstrap"
        rw = state.windows[symbol]
        n = rw.indicator_class.N
        # Allow some slack for weekends/holidays vs. the calendar-day fetch range.
        assert len(rw.values) >= int(n * 0.6), (
            f"{symbol} window has {len(rw.values)} values, expected >= {int(n * 0.6)} (N={n})"
        )
        assert len(rw.values) <= n, (
            f"{symbol} window has {len(rw.values)} values, expected <= {n} (N={n})"
        )
        assert all(isinstance(v, float) for v in rw.values), f"{symbol} window contains non-float"
        assert all(v > 0 for v in rw.values), f"{symbol} window contains non-positive value"
        assert rw.last_update is not None, f"{symbol} last_update not set after bootstrap"

    # VIX sanity: historically ranges ~8–90
    vix_values = list(state.windows["VIX"].values)
    assert all(5.0 <= v <= 100.0 for v in vix_values), (
        f"VIX values outside plausible range [5, 100]: {vix_values}"
    )
