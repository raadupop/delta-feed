"""
MARKET_DATA strategy tests — two historical events.

Windows are seeded from fixture JSON files containing real VIX daily closes
from FRED (VIXCLS series). No invented data.
"""
import json
from collections import deque
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.state import RollingWindow, state
from main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_market_window():
    """Clear and re-ready state before each test; clean up after."""
    state.market_data_history.clear()
    state.is_ready = True
    yield
    state.market_data_history.clear()


def _run_fixture(client: TestClient, filename: str) -> dict:
    data = json.loads((FIXTURES / filename).read_text())
    symbol = data["symbol"]
    last_update = datetime.fromisoformat(data["last_update"])
    state.market_data_history[symbol] = RollingWindow(
        values=deque(data["window"], maxlen=20),
        last_update=last_update,
    )

    resp = client.post("/classify", json=data["request"])
    assert resp.status_code == 200

    body = resp.json()
    exp = data["expected"]

    assert body["score"] == exp["score"], (
        f"score: got {body['score']}, expected {exp['score']}"
    )
    assert body["score_type"] == exp["score_type"]
    assert body["certainty"] == exp["certainty"], (
        f"certainty: got {body['certainty']}, expected {exp['certainty']}"
    )
    assert body["source_reliability"] == exp["source_reliability"], (
        f"source_reliability: got {body['source_reliability']}, expected {exp['source_reliability']}"
    )
    assert body["temporal_relevance"] == exp["temporal_relevance"], (
        f"temporal_relevance: got {body['temporal_relevance']}, expected {exp['temporal_relevance']}"
    )
    assert body["classification_method"] == exp["classification_method"]
    assert body["reasoning_trace"], "reasoning_trace must be a non-empty string"

    m = body["computed_metrics"]
    assert m["z_score"] == exp["z_score"], (
        f"z_score: got {m['z_score']}, expected {exp['z_score']}"
    )
    assert m["baseline_mean"] == exp["baseline_mean"], (
        f"baseline_mean: got {m['baseline_mean']}, expected {exp['baseline_mean']}"
    )
    assert m["baseline_std"] == exp["baseline_std"], (
        f"baseline_std: got {m['baseline_std']}, expected {exp['baseline_std']}"
    )

    return body


def test_volmageddon(client: TestClient):
    """VIX 10→37 spike on 2018-02-05 — extreme z-score against calm window."""
    _run_fixture(client, "market_data_volmageddon.json")


def test_covid_first_spike(client: TestClient):
    """VIX 17→25 on 2020-02-24 — first COVID signal against pre-pandemic window."""
    _run_fixture(client, "market_data_covid.json")
