"""
Rebaseline anchor fixtures for SRS v2.3.3 signed severity (CLS-001).

For MARKET_DATA fixtures (pct_change deviation_kind):
  - Pulls N_L daily closes from FRED ending the trading day before
    `source.current_value_date`.
  - Computes signed severity:
        m = median(history)
        dev_signed = current_value - m
        history_abs_devs = [|x - m| for x in history]
        score = sign(dev_signed) * ecdf_rank(|dev_signed|, history_abs_devs)
  - Writes long_horizon_window, expected_score_signed, sign_convention_check,
    srs_version="2.3.3" back to the fixture JSON.

For MACROECONOMIC fixtures: skipped here. CPI uses N_L=None (parametric
fallback path); rebaseline of those scores is computed when the parametric
strategy lands. INITIAL_CLAIMS (N_L=312) requires a curated weekly-surprise
history — out of scope for this script run.

Run:
    .\.venv\Scripts\python.exe scripts/rebaseline_fixtures.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import registry  # noqa: E402

FIXTURES = ROOT / "tests" / "acceptance" / "fixtures"


def ecdf_rank(value: float, history: list[float]) -> float:
    if not history:
        return 0.0
    return sum(1 for h in history if h <= value) / len(history)


def fetch_fred_levels(series_id: str, end_date: datetime, n_target: int) -> tuple[list[float], list[str]]:
    from fredapi import Fred

    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        env_path = ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("FRED_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        raise RuntimeError("FRED_API_KEY not found in env or apps/classification/.env")

    fred = Fred(api_key=api_key)
    start = end_date - timedelta(days=int(n_target * 1.8))
    series = fred.get_series(series_id, start, end_date).dropna()
    if series.empty:
        raise RuntimeError(f"FRED returned no data for {series_id} ending {end_date.date()}")
    series = series.iloc[-n_target:]
    levels = [float(v) for v in series.values]
    dates = [idx.strftime("%Y-%m-%d") for idx in series.index]
    if len(levels) < n_target:
        raise RuntimeError(
            f"{series_id}: needed {n_target} samples, got {len(levels)} "
            f"(history may be too short)"
        )
    return levels, dates


def rebaseline_market_data(fixture_path: Path, fixture: dict) -> bool:
    if fixture.get("srs_version") == "2.3.3":
        print(f"  {fixture_path.name}: already 2.3.3 — skip")
        return False

    if fixture.get("request", {}).get("source_category") != "MARKET_DATA":
        return False

    if "PENDING DATA PULL" in fixture.get("status", ""):
        print(f"  {fixture_path.name}: PENDING DATA PULL — skip")
        return False

    symbol = fixture["symbol"]
    entry = registry.get_symbol(symbol)
    klass = entry.indicator_class
    if klass.N_L is None:
        print(f"  {fixture_path.name}: class {klass.name} has N_L=None — skip")
        return False

    if entry.bootstrap is None:
        print(f"  {fixture_path.name}: no bootstrap spec — skip")
        return False

    series_id = entry.bootstrap.series_id
    event_date = datetime.fromisoformat(
        fixture["source"]["current_value_date"]
    ).replace(tzinfo=timezone.utc)
    end = event_date - timedelta(days=1)
    current_value = fixture["request"]["structured_payload"]["current_value"]

    print(f"  {fixture_path.name}: fetching {series_id} N_L={klass.N_L} ending {end.date()}")
    levels, dates = fetch_fred_levels(series_id, end, klass.N_L)

    m = median(levels)
    dev_signed = current_value - m
    history_abs_devs = [abs(v - m) for v in levels]
    rank = ecdf_rank(abs(dev_signed), history_abs_devs)
    sign = 1.0 if dev_signed > 0 else (-1.0 if dev_signed < 0 else 0.0)
    score_signed = round(sign * rank, 4)

    if score_signed > 0.05:
        sign_check = "+1"
    elif score_signed < -0.05:
        sign_check = "-1"
    else:
        sign_check = "near_zero"

    fixture["srs_version"] = "2.3.3"
    fixture["long_horizon_window"] = [round(v, 4) for v in levels]
    fixture["source"]["long_horizon_window_range"] = f"{dates[0]} .. {dates[-1]}"
    fixture["source"]["long_horizon_retrieved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    band = fixture.setdefault("expected_band", {})
    band["expected_score_signed"] = score_signed
    band["score_tolerance"] = 0.05
    band["sign_convention_check"] = sign_check
    band.pop("expected_score", None)
    band.pop("score_min", None)
    band.pop("score_max", None)

    fixture_path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(
        f"    median={m:.4f} dev_signed={dev_signed:+.4f} rank={rank:.4f} "
        f"score_signed={score_signed:+.4f} sign={sign_check}"
    )
    return True


def main() -> int:
    if not FIXTURES.exists():
        print(f"No fixtures directory at {FIXTURES}")
        return 1

    rebaselined = 0
    for fp in sorted(FIXTURES.glob("*.json")):
        try:
            fixture = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"  {fp.name}: JSON error — {exc}")
            continue
        if rebaseline_market_data(fp, fixture):
            rebaselined += 1

    print(f"\nRebaselined {rebaselined} fixture(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
