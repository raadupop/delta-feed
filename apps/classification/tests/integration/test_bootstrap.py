"""
Integration test — verifies MARKET_DATA bootstrap against the real FRED API.

Skipped automatically when FRED_API_KEY is not configured.
Run explicitly with:  python -m pytest tests/test_bootstrap_integration.py -v
"""
import pytest

from app.config import settings
from app.state import state

needs_api_key = pytest.mark.skipif(
    not settings.fred_api_key,
    reason="FRED_API_KEY not set",
)


@pytest.fixture(autouse=True)
def clean_state():
    state.market_data_history.clear()
    state.is_ready = False
    yield
    state.market_data_history.clear()
    state.is_ready = False


@needs_api_key
@pytest.mark.asyncio
async def test_bootstrap_populates_vix_and_ovx():
    """Bootstrap should populate both VIX and OVX with up to 20 daily closes from FRED."""
    from main import _bootstrap_market_data_window

    await _bootstrap_market_data_window()

    for symbol in ("VIX", "OVX"):
        assert symbol in state.market_data_history, f"{symbol} window missing after bootstrap"
        rw = state.market_data_history[symbol]
        assert len(rw.values) >= 15, f"{symbol} window has {len(rw.values)} values, expected >= 15"
        assert len(rw.values) <= 20, f"{symbol} window has {len(rw.values)} values, expected <= 20"
        assert all(isinstance(v, float) for v in rw.values), f"{symbol} window contains non-float"
        assert all(v > 0 for v in rw.values), f"{symbol} window contains non-positive value"
        assert rw.last_update is not None, f"{symbol} last_update not set after bootstrap"

    # VIX sanity: historically ranges ~8–90
    vix_values = list(state.market_data_history["VIX"].values)
    assert all(5.0 <= v <= 100.0 for v in vix_values), (
        f"VIX values outside plausible range [5, 100]: {vix_values}"
    )
