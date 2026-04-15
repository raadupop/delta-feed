"""
Application entry point — FastAPI app, lifecycle hooks, and endpoint definitions.
"""
import logging
from collections import deque
from typing import cast
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.requests import ClassifyRequest
from app.models.responses import ClassifyResponse
from app.routing.dispatcher import dispatch
from app.state import RollingWindow, state

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Startup / shutdown lifecycle
# ---------------------------------------------------------------------------

# Maps internal symbol names to FRED series IDs
_MARKET_DATA_FRED_SERIES = {"VIX": "VIXCLS", "OVX": "OVXCLS"}


async def _bootstrap_market_data_window() -> None:
    """Fetch last 20 daily closes for VIX and OVX from FRED."""
    if not settings.fred_api_key:
        logger.warning("FRED_API_KEY not set — skipping MARKET_DATA bootstrap")
        return
    try:
        from fredapi import Fred

        fred = Fred(api_key=settings.fred_api_key)
        end = datetime.now()
        start = end - timedelta(days=45)  # ~20 trading days with weekend/holiday margin

        for symbol, series_id in _MARKET_DATA_FRED_SERIES.items():
            try:
                series = fred.get_series(series_id, start, end).dropna()
                closes = [float(v) for v in series.values[-20:]]
                if closes:
                    last_date = series.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
                    state.market_data_history[symbol] = RollingWindow(
                        values=deque(closes, maxlen=20),
                        last_update=last_date,
                    )
                    logger.info("MARKET_DATA %s: %d values loaded from FRED %s", symbol, len(closes), series_id)
                else:
                    logger.warning("FRED %s returned no data for %s", series_id, symbol)
            except Exception as exc:
                logger.warning("MARKET_DATA bootstrap failed for %s: %s", symbol, exc)
    except Exception as exc:
        logger.warning("FRED bootstrap init failed: %s", exc)


_MACRO_INDICATORS = {
    "CPI_YOY": "CPIAUCSL",  # CPI for All Urban Consumers, seasonally adjusted
}


async def _bootstrap_macro_windows() -> None:
    """Populate MACROECONOMIC surprise history windows from Finnhub economic calendar.

    Finnhub provides actual/estimate pairs for economic releases. We compute
    |actual - expected| for each release and store the last 30 per indicator.

    Fallback: if FINNHUB_API_KEY is unavailable, use FRED actuals with a static
    consensus map. This is a bootstrap-only limitation — live classify requests
    always receive actual/expected from the .NET caller.
    """
    if settings.finnhub_api_key:
        await _bootstrap_macro_from_finnhub()
        return

    if not settings.fred_api_key:
        logger.warning("No FINNHUB_API_KEY or FRED_API_KEY — skipping MACROECONOMIC bootstrap")
        return

    logger.info("FINNHUB_API_KEY not set — falling back to FRED + static consensus for MACROECONOMIC bootstrap")
    try:
        from fredapi import Fred

        fred = Fred(api_key=settings.fred_api_key)
        end = datetime.now()
        start = end - timedelta(days=365 * 3)  # ~36 monthly releases

        for indicator, series_id in _MACRO_INDICATORS.items():
            try:
                series = fred.get_series(series_id, start, end).dropna()
                yoy = series.pct_change(periods=12) * 100
                yoy = yoy.dropna()

                # Static consensus estimates — used only when Finnhub is unavailable.
                # In production, use Finnhub paid tier for actual/estimate pairs.
                cpi_consensus = {
                    '2022-01': 7.3, '2022-02': 7.9, '2022-03': 8.4, '2022-04': 8.1,
                    '2022-05': 8.3, '2022-06': 8.6, '2022-07': 8.7, '2022-08': 8.0,
                    '2022-09': 8.1, '2022-10': 7.9, '2022-11': 7.3, '2022-12': 6.5,
                    '2023-01': 6.2, '2023-02': 6.0, '2023-03': 5.2, '2023-04': 5.0,
                    '2023-05': 4.1, '2023-06': 3.1, '2023-07': 3.3, '2023-08': 3.6,
                    '2023-09': 3.6, '2023-10': 3.3, '2023-11': 3.1, '2023-12': 3.2,
                    '2024-01': 2.9, '2024-02': 3.1, '2024-03': 3.5, '2024-04': 3.4,
                    '2024-05': 3.3, '2024-06': 3.0, '2024-07': 2.9, '2024-08': 2.6,
                    '2024-09': 2.4, '2024-10': 2.6, '2024-11': 2.7, '2024-12': 2.9,
                }

                surprises: list[float] = []
                for date, val in yoy.items():
                    key = cast(datetime, date).strftime('%Y-%m')
                    if key in cpi_consensus:
                        actual = round(float(val), 1)
                        expected = cpi_consensus[key]
                        surprises.append(round(abs(actual - expected), 1))

                recent = surprises[-30:]
                if recent:
                    last_date = yoy.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
                    state.macro_surprise_histories[indicator] = RollingWindow(
                        values=deque(recent, maxlen=30),
                        last_update=last_date,
                    )
                    logger.info("MACROECONOMIC %s: %d surprise values loaded (FRED fallback)", indicator, len(recent))
                else:
                    logger.warning("No surprise data computed for %s", indicator)
            except Exception as exc:
                logger.warning("MACROECONOMIC bootstrap failed for %s: %s", indicator, exc)
    except Exception as exc:
        logger.warning("FRED bootstrap init failed for MACROECONOMIC: %s", exc)


async def _bootstrap_macro_from_finnhub() -> None:
    """Fetch actual/estimate pairs from Finnhub economic calendar (paid tier)."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            end = datetime.now()
            start = end - timedelta(days=365 * 3)

            for indicator, _ in _MACRO_INDICATORS.items():
                try:
                    resp = await client.get(
                        "https://finnhub.io/api/v1/calendar/economic",
                        params={
                            "from": start.strftime("%Y-%m-%d"),
                            "to": end.strftime("%Y-%m-%d"),
                            "token": settings.finnhub_api_key,
                        },
                    )
                    if resp.status_code == 403:
                        logger.warning("Finnhub economic calendar requires paid tier — MACROECONOMIC window not populated")
                        return

                    data = resp.json()
                    events = data.get("economicCalendar", [])
                    cpi_events = [
                        e for e in events
                        if "CPI" in e.get("event", "") and e.get("country") == "US"
                        and e.get("actual") is not None and e.get("estimate") is not None
                    ]

                    surprises = [abs(e["actual"] - e["estimate"]) for e in cpi_events]
                    recent = surprises[-30:]
                    if recent:
                        last_event_date = datetime.strptime(
                            cpi_events[-1]["date"], "%Y-%m-%d",
                        ).replace(tzinfo=timezone.utc)
                        state.macro_surprise_histories[indicator] = RollingWindow(
                            values=deque(recent, maxlen=30),
                            last_update=last_event_date,
                        )
                        logger.info("MACROECONOMIC %s: %d values from Finnhub", indicator, len(recent))
                    else:
                        logger.warning("No CPI events from Finnhub for %s", indicator)
                except Exception as exc:
                    logger.warning("Finnhub bootstrap failed for %s: %s", indicator, exc)
    except Exception as exc:
        logger.warning("Finnhub bootstrap init failed: %s", exc)




async def _bootstrap_windows() -> None:
    """
    Populate in-memory rolling windows from external APIs.
    Called on startup — sets state.is_ready = True when complete.
    """
    logger.info("Bootstrap starting — populating rolling windows...")
    await _bootstrap_market_data_window()
    await _bootstrap_macro_windows()
    # TODO (step 5): _bootstrap_cross_asset_windows()
    state.is_ready = True
    logger.info("Bootstrap complete — service is ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup → yield → shutdown."""
    await _bootstrap_windows()
    yield
    # Shutdown cleanup (nothing to release yet — no DB connections, no sockets owned here)
    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Invex Classification Service",
    version="0.1.0",
    description="Stateless HTTP classification engine for financial signal events.",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Convert strategy dispatch errors (bad source_category/payload_type combos) to 422."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )

@app.exception_handler(NotImplementedError)
async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
    """Scaffold stubs return NotImplementedError — surface as 501."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _build_window_staleness() -> dict:
    """Build per-window staleness info for the health endpoint."""
    now = datetime.now(timezone.utc)
    windows: dict[str, dict] = {}

    for symbol, rw in state.market_data_history.items():
        entry: dict[str, object] = {"values_count": len(rw.values)}
        if rw.last_update:
            entry["last_update"] = rw.last_update.isoformat()
            entry["staleness_seconds"] = round((now - rw.last_update).total_seconds(), 1)
        windows[f"MARKET_DATA/{symbol}"] = entry

    for indicator, rw in state.macro_surprise_histories.items():
        entry = {"values_count": len(rw.values)}
        if rw.last_update:
            entry["last_update"] = rw.last_update.isoformat()
            entry["staleness_seconds"] = round((now - rw.last_update).total_seconds(), 1)
        windows[f"MACROECONOMIC/{indicator}"] = entry

    return windows


@app.get("/health")
async def health() -> JSONResponse:
    """
    Readiness probe. Returns 200 once bootstrap is complete, 503 during startup.
    Includes per-window staleness info when ready.
    """
    if state.is_ready:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "windows": _build_window_staleness(),
            },
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready"},
    )


@app.post("/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest) -> ClassifyResponse:
    """Main classification endpoint."""
    if not state.is_ready:
        return JSONResponse(  # type: ignore[return-value]
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service is bootstrapping — not ready yet."},
        )

    return await dispatch(request)


# ---------------------------------------------------------------------------
# Dev runner — `python main.py` starts uvicorn directly
# Production: `uvicorn main:app --host 0.0.0.0 --port 8000`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
