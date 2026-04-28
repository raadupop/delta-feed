"""
Anchor-event acceptance tests — black-box replay of trader-curated historical
events.

Lineage: quant-shop "golden runs" — reference-scenario tests where the inputs
are real historical data and the assertions are domain bands wide enough to
survive reasonable recalibration (e.g. `tanh_scale` 18 → 22) but narrow
enough to catch regressions.

Each anchor is a JSON fixture under `tests/fixtures/acceptance/` with:
  - `source` block — provider, series_id, retrieved_at, url (strict provenance)
  - `window` — seed values for the rolling window
  - `last_update` — ISO timestamp of the latest seed point
  - `request` — the POST /classify body
  - `expected_band` — { score_min, score_max, score_type, ... }
  - `xfail` (optional) — { reason, strict }

See `tests/fixtures/acceptance/ANCHORS.md` for the curated event catalogue
and source-provenance rule.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from .conftest import ACCEPTANCE_FIXTURES, seed_macro_window, seed_market_data_window


def _load_anchors() -> list[tuple[str, dict[str, Any]]]:
    if not ACCEPTANCE_FIXTURES.exists():
        return []
    items: list[tuple[str, dict[str, Any]]] = []
    for fp in sorted(ACCEPTANCE_FIXTURES.glob("*.json")):
        with fp.open("r", encoding="utf-8") as fh:
            items.append((fp.stem, json.load(fh)))
    return items


ANCHORS = _load_anchors()


@pytest.mark.skipif(not ANCHORS, reason="No acceptance anchor fixtures authored yet (awaiting /trader curation)")
@pytest.mark.parametrize("anchor_name,anchor", ANCHORS, ids=[a[0] for a in ANCHORS] or ["_placeholder"])
def test_anchor_event(client: TestClient, anchor_name: str, anchor: dict[str, Any], request: pytest.FixtureRequest) -> None:
    """Seed window per anchor, POST /classify, assert score lands in declared band."""
    if "PENDING DATA PULL" in anchor.get("status", ""):
        pytest.skip(
            f"{anchor_name}: awaiting /trader data pull from the cited provider. "
            f"Per HARNESS.md source-provenance rule, no values are invented to make a test runnable."
        )

    srs_version = anchor.get("srs_version", "2.3.2")
    if srs_version != "2.3.3":
        pytest.skip(
            f"{anchor_name}: fixture is srs_version={srs_version!r}; awaiting v2.3.3 "
            "rebaseline (long_horizon_window of length N_L from FRED, signed expected_score). "
            "Per HARNESS.md source-provenance rule, no values are invented."
        )

    xfail = anchor.get("xfail")
    if xfail:
        request.applymarker(pytest.mark.xfail(reason=xfail.get("reason", ""), strict=xfail.get("strict", True)))

    long_horizon = anchor.get("long_horizon_window")
    category = anchor["request"]["source_category"]
    if category == "MARKET_DATA":
        seed_market_data_window(
            anchor["symbol"], anchor["window"], anchor["last_update"],
            long_horizon_values=long_horizon,
        )
    elif category == "MACROECONOMIC":
        seed_macro_window(
            anchor["indicator"], anchor["window"], anchor["last_update"],
            long_horizon_values=long_horizon,
        )
    else:
        pytest.skip(f"Anchor category {category} not yet supported by acceptance seeding")

    resp = client.post("/classify", json=anchor["request"])
    assert resp.status_code == 200, f"{anchor_name}: {resp.status_code} {resp.text}"
    body = resp.json()

    band = anchor["expected_band"]
    score = body["score"]
    if "expected_score_signed" in band:
        tol = band.get("score_tolerance", 0.0)
        target = band["expected_score_signed"]
        assert abs(score - target) <= tol, (
            f"{anchor_name}: signed score {score} differs from {target} by more than tol={tol}"
        )
    elif "score_min_signed" in band and "score_max_signed" in band:
        assert band["score_min_signed"] <= score <= band["score_max_signed"], (
            f"{anchor_name}: signed score {score} outside band "
            f"[{band['score_min_signed']}, {band['score_max_signed']}]"
        )
    else:
        raise AssertionError(
            f"{anchor_name}: srs_version=2.3.3 fixture must declare "
            "expected_score_signed or [score_min_signed, score_max_signed]"
        )

    if "sign_convention_check" in band:
        expected_sign = band["sign_convention_check"]
        if expected_sign == "+1":
            assert score > 0, f"{anchor_name}: expected positive score, got {score}"
        elif expected_sign == "-1":
            assert score < 0, f"{anchor_name}: expected negative score, got {score}"
        elif expected_sign == "near_zero":
            assert abs(score) < 0.1, f"{anchor_name}: expected near-zero score, got {score}"
        else:
            raise AssertionError(
                f"{anchor_name}: sign_convention_check={expected_sign!r} not in "
                "{'+1', '-1', 'near_zero'}"
            )

    assert body["score_type"] == band["score_type"]

    if "classification_method" in band:
        assert body["classification_method"] == band["classification_method"]
    if "temporal_relevance_min" in band:
        assert body["temporal_relevance"] is not None
        assert body["temporal_relevance"] >= band["temporal_relevance_min"]
    if "temporal_relevance_max" in band:
        assert body["temporal_relevance"] is not None
        assert body["temporal_relevance"] <= band["temporal_relevance_max"], (
            f"{anchor_name}: temporal_relevance {body['temporal_relevance']} exceeds max {band['temporal_relevance_max']}"
        )