"""
Fitness function: cyclomatic complexity ceilings on `app/`.

Lineage: McCabe, A Complexity Measure (1976); Martin, Clean Code (2008) — small
functions; SEI/NIST guidance on complexity thresholds.

Thresholds (declared in `pyproject.toml` under `[tool.xenon]`):
  - max-absolute: B (any function > B fails)
  - max-modules: B (any module average > B fails)
  - max-average: A

Today's expectation: PASS. Establishes the ceiling before strategy logic
grows branches that could hide wrong-level modeling.
"""
from __future__ import annotations

import pytest

from .conftest import run_python_module


def test_cyclomatic_complexity_within_thresholds() -> None:
    """xenon must report zero complexity violations on `app/`."""
    pytest.importorskip("xenon")
    result = run_python_module(
        "xenon",
        ["--max-absolute", "B", "--max-modules", "B", "--max-average", "A", "app"],
    )
    assert result.returncode == 0, (
        f"Cyclomatic complexity ceiling exceeded.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
