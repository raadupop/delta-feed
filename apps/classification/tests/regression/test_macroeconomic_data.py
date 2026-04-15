"""
MACROECONOMIC strategy tests — two historical CPI events.

Windows are seeded from fixture JSON files containing real |actual - expected|
surprise histories computed from FRED CPI-U actuals and Bloomberg/Reuters
consensus estimates. No invented data.
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
def reset_macro_window():
    """Clear and re-ready state before each test; clean up after."""
    state.macro_surprise_histories.clear()
    state.is_ready = True
    yield
    state.macro_surprise_histories.clear()


def _run_fixture(client: TestClient, filename: str) -> dict:
    data = json.loads((FIXTURES / filename).read_text())
    indicator = data["indicator"]
    last_update = datetime.fromisoformat(data["last_update"])
    state.macro_surprise_histories[indicator] = RollingWindow(
        values=deque(data["window"], maxlen=30),
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
    assert m["surprise_magnitude"] == exp["surprise_magnitude"], (
        f"surprise_magnitude: got {m['surprise_magnitude']}, expected {exp['surprise_magnitude']}"
    )
    assert m["baseline_mean"] == exp["baseline_mean"], (
        f"baseline_mean: got {m['baseline_mean']}, expected {exp['baseline_mean']}"
    )
    assert m["baseline_std"] == exp["baseline_std"], (
        f"baseline_std: got {m['baseline_std']}, expected {exp['baseline_std']}"
    )

    return body


def test_cpi_june_2022(client: TestClient):
    """CPI YoY 9.1% vs 8.6% expected (2022-06) — large upside surprise during peak inflation."""
    _run_fixture(client, "macro_cpi_june_2022.json")


def test_cpi_nov_2021(client: TestClient):
    """CPI YoY 6.9% vs 6.7% expected (2021-11) — modest surprise during inflation ramp."""
    _run_fixture(client, "macro_cpi_nov_2021.json")
