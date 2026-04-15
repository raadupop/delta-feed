"""
Shared helpers for the architecture fitness suite.

Each test in this package wraps an industry-standard Python tool
(`import-linter`, `ruff`, `xenon`, `mypy`, `vulture`) and asserts its exit code
/ structured output. Config for each tool lives in `pyproject.toml` so the same
rules are visible to IDEs and pre-commit, not hidden in test glue.

Lineage: Ford/Parsons/Kua, Building Evolutionary Architectures (2017) — fitness
functions as first-class tests; Paul/Ford, Software Architecture Metrics (2022).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


CLASSIFICATION_ROOT = Path(__file__).resolve().parents[2]
APP_DIR = CLASSIFICATION_ROOT / "app"


def require_tool(name: str) -> str:
    """Skip the test if the tool is not installed in the active environment."""
    path = shutil.which(name)
    if path is None:
        pytest.skip(f"{name} is not installed in this environment")
    return path


def run_tool(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a CLI tool and capture output. Uses the current interpreter's scripts."""
    return subprocess.run(
        args,
        cwd=cwd or CLASSIFICATION_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def run_python_module(module: str, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run `python -m <module> <args>` so we don't depend on shim scripts."""
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=cwd or CLASSIFICATION_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
