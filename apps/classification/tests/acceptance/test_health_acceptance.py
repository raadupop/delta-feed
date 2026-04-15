"""
Health endpoint acceptance tests — readiness + staleness block.

Only asserts contract-level shape and semantics. Numeric staleness values are
side-effects of wall-clock time and are not asserted.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import seed_market_data_window


def test_health_reports_ready(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert "windows" in body
    assert isinstance(body["windows"], dict)


def test_health_surfaces_seeded_window_under_namespaced_key(client: TestClient) -> None:
    """Seeded windows must appear under `<CATEGORY>/<id>` in the staleness block."""
    seed_market_data_window("VIX", [10.0] * 20, "2018-02-02T00:00:00+00:00")
    resp = client.get("/health")
    assert resp.status_code == 200
    windows = resp.json()["windows"]
    assert "MARKET_DATA/VIX" in windows
    entry = windows["MARKET_DATA/VIX"]
    assert entry["values_count"] == 20
    assert "last_update" in entry
    assert "staleness_seconds" in entry
    assert entry["staleness_seconds"] >= 0
