"""
Fitness function: no dead code / unused symbols in `app/`.

Lineage: Fowler, Refactoring — "Dead Code"; Martelli et al., vulture.

Today's expectation: PASS. When Phase B extracts `_compute_temporal_relevance`
to `app/math/temporal.py`, vulture will fire on any duplicate left behind —
catches incomplete refactors without a dedicated rule.
"""
from __future__ import annotations

import pytest

from .conftest import run_python_module


def test_no_dead_code() -> None:
    """vulture must report zero dead code above the confidence threshold."""
    pytest.importorskip("vulture")
    result = run_python_module("vulture", ["app", "--min-confidence", "80"])
    # vulture exits non-zero iff it finds something.
    assert result.returncode == 0, (
        f"Dead code detected in `app/`:\n{result.stdout}"
    )
