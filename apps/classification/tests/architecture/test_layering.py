"""
Fitness function: Clean Architecture layering + dependency-direction contracts.

Lineage: Martin, Clean Architecture (2017); Cockburn, Hexagonal / Ports &
Adapters; Evans, DDD layered architecture; Seddon, import-linter (Python port
of ArchUnit conventions).

Contracts (declared in `pyproject.toml` under `[tool.importlinter]`):
  - strategies_are_peers: `app.strategies.*` modules must not import from each
    other. Shared logic lives in `app.math` / `app.state`.
  - layered: `app.routing` -> `app.strategies` -> (`app.state`, `app.models`).
    No upward imports, no cycles.
  - models_are_pure: `app.models` has no imports from other `app.*` packages.

Today's expectation: PASS. Establishes the guardrail before the degenerate
"fix" (one strategy importing another's private helper) is taken.
"""
from __future__ import annotations

import pytest

from .conftest import CLASSIFICATION_ROOT, run_python_module


def test_import_linter_contracts_pass() -> None:
    """`lint-imports` must report zero contract violations against pyproject.toml."""
    pytest.importorskip("importlinter")
    from .conftest import require_tool, run_tool

    lint_imports = require_tool("lint-imports")
    result = run_tool([lint_imports, "--config", str(CLASSIFICATION_ROOT / "pyproject.toml")])
    assert result.returncode == 0, (
        f"import-linter found layering violations.\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
