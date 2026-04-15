"""
Fitness function: strict typing at strategy and contract boundaries.

Lineage: Pierce, Types and Programming Languages (2002); Instagram / Dropbox
public engineering blogs on adopting `mypy --strict`.

Scope: `app/models`, `app/routing`, `app/strategies`. Config in `pyproject.toml`
under `[tool.mypy]`. Had the per-indicator tuning parameters been typed as an
`IndicatorParams` object at the strategy boundary, the wrong abstraction level
would have been a type-system conversation, not a silent global.

Today's expectation: PASS on the declared strict-typed packages. Phase B
expands the strict-typed set as packages are refactored.
"""
from __future__ import annotations

import pytest

from .conftest import run_python_module


def test_strict_typing_passes_on_declared_packages() -> None:
    """mypy must report zero errors on the strict-typed packages."""
    pytest.importorskip("mypy")
    result = run_python_module("mypy", ["--config-file", "pyproject.toml", "app"])
    assert result.returncode == 0, (
        f"mypy reported type errors.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
