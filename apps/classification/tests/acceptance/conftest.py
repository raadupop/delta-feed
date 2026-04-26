"""
Shared fixtures for the acceptance suite.

Acceptance tests interact with the service ONLY via its public HTTP surface
(`POST /classify`, `GET /health`) and its contract (`doc/openapi.yaml`). They
must not import strategy internals or assert on implementation-specific
fields like `computed_metrics.z_score`.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import registry
from app.state import RollingWindow, state
from main import app

CLASSIFICATION_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = CLASSIFICATION_ROOT / "doc" / "openapi.yaml"
ACCEPTANCE_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def openapi_spec() -> dict[str, Any]:
    with OPENAPI_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    """Clear windows between tests, keep bootstrap-ready flag."""
    state.windows.clear()
    state.is_ready = True
    yield
    state.windows.clear()


def _seed_window(symbol: str, values: list[float], last_update_iso: str) -> None:
    """Seed a rolling window from registry-defined indicator class.

    The window's deque is sized from `IndicatorClass.N` via RollingWindow.__post_init__,
    so callers don't have to know N — they only provide the seed values they
    have on hand.
    """
    entry = registry.get_symbol(symbol)
    state.windows[symbol] = RollingWindow(
        indicator_class=entry.indicator_class,
        values=deque(values),
        last_update=datetime.fromisoformat(last_update_iso),
    )


def seed_market_data_window(symbol: str, values: list[float], last_update_iso: str) -> None:
    _seed_window(symbol, values, last_update_iso)


def seed_macro_window(indicator: str, values: list[float], last_update_iso: str) -> None:
    _seed_window(indicator, values, last_update_iso)
