"""
Contract-shape acceptance tests.

Lineage: Ian Robinson / Pact, consumer-driven contracts; OpenAPI 3.1 spec.

These tests assert that responses from `POST /classify` and `GET /health`
validate against `doc/openapi.yaml`. They do NOT assert numeric values — only
shapes, ranges, enums, and required fields. The companion `test_anchor_events`
file asserts values via trader-curated domain bands.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from .conftest import seed_market_data_window


def _resolve_schema(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Follow a `#/components/schemas/X` reference in the spec."""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for p in parts:
        node = node[p]
    return node


def _validator_for(spec: dict[str, Any], ref: str) -> Draft202012Validator:
    """Build a JSON Schema validator with the full `components` namespace as resolver scope."""
    # Resolve the reference by embedding the spec's components so $ref chains work.
    schema = {"$ref": ref, "components": spec.get("components", {})}
    return Draft202012Validator(schema)


def test_health_ready_matches_contract(client: TestClient, openapi_spec: dict[str, Any]) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    validator = _validator_for(openapi_spec, "#/components/schemas/HealthReady")
    errors = sorted(validator.iter_errors(resp.json()), key=lambda e: e.path)
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_classify_market_data_response_matches_contract(
    client: TestClient, openapi_spec: dict[str, Any]
) -> None:
    """Seed a minimal VIX window and assert response is contract-valid."""
    seed_market_data_window(
        "VIX",
        [10.18, 11.04, 9.77, 9.15, 9.22, 9.22, 9.52, 10.08, 9.82, 9.88,
         10.16, 11.66, 11.91, 12.22, 11.27, 11.03, 11.10, 11.47, 11.58, 11.08],
        "2018-02-02T00:00:00+00:00",
    )
    payload = {
        "source_category": "MARKET_DATA",
        "payload_type": "STRUCTURED",
        "structured_payload": {
            "symbol": "VIX",
            "current_value": 37.32,
            "timestamp": "2018-02-05T00:00:00Z",
        },
    }
    resp = client.post("/classify", json=payload)
    assert resp.status_code == 200
    validator = _validator_for(openapi_spec, "#/components/schemas/ClassifyResponse")
    errors = sorted(validator.iter_errors(resp.json()), key=lambda e: e.path)
    assert not errors, "\n".join(f"{list(e.path)}: {e.message}" for e in errors)


def test_classify_rejects_unknown_source_category(client: TestClient) -> None:
    """Pydantic rejects unknown enum values (contract: 422 with ErrorDetail)."""
    resp = client.post(
        "/classify",
        json={"source_category": "INVALID", "payload_type": "STRUCTURED", "structured_payload": {}},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body


def test_classify_rejects_missing_required_field(client: TestClient) -> None:
    """source_category is required by the contract — omission → 422."""
    resp = client.post(
        "/classify",
        json={"payload_type": "STRUCTURED", "structured_payload": {}},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_classify_rejects_unsupported_combination(client: TestClient) -> None:
    """MARKET_DATA + UNSTRUCTURED has no strategy → 422 with ErrorDetail."""
    resp = client.post(
        "/classify",
        json={
            "source_category": "MARKET_DATA",
            "payload_type": "UNSTRUCTURED",
            "unstructured_payload": {"text": "news"},
        },
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_classify_stub_returns_501(client: TestClient) -> None:
    """CROSS_ASSET_FLOW is a scaffold stub (contract: 501)."""
    resp = client.post(
        "/classify",
        json={
            "source_category": "CROSS_ASSET_FLOW",
            "payload_type": "STRUCTURED",
            "structured_payload": {
                "basket_prices": {
                    "SPY": 400.0, "TLT": 100.0, "GLD": 180.0,
                    "USO": 70.0, "EEM": 40.0, "UUP": 28.0,
                },
                "timestamp": "2023-03-10T15:00:00Z",
            },
        },
    )
    assert resp.status_code == 501
    assert "detail" in resp.json()


def test_openapi_spec_is_valid() -> None:
    """Guardrail: the spec itself must be valid OpenAPI 3.1."""
    pytest.importorskip("openapi_spec_validator")
    from openapi_spec_validator import validate

    from .conftest import OPENAPI_PATH
    import yaml

    with OPENAPI_PATH.open("r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    validate(spec)  # raises on invalid
