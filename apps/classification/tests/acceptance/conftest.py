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
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

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
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Clear windows between tests, keep bootstrap-ready flag."""
    state.market_data_history.clear()
    state.macro_surprise_histories.clear()
    state.is_ready = True
    yield
    state.market_data_history.clear()
    state.macro_surprise_histories.clear()


def seed_market_data_window(symbol: str, values: list[float], last_update_iso: str) -> None:
    state.market_data_history[symbol] = RollingWindow(
        values=deque(values, maxlen=20),
        last_update=datetime.fromisoformat(last_update_iso),
    )


def seed_macro_window(indicator: str, values: list[float], last_update_iso: str) -> None:
    state.macro_surprise_histories[indicator] = RollingWindow(
        values=deque(values, maxlen=30),
        last_update=datetime.fromisoformat(last_update_iso),
    )
