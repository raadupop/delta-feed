"""
Strategy dispatcher — routes a ClassifyRequest to the correct strategy.
"""
from app.models.requests import ClassifyRequest
from app.models.responses import ClassifyResponse
from app.strategies.base import ClassificationStrategy
from app.strategies.cross_asset import CrossAssetStrategy
from app.strategies.geopolitical import (
    GeopoliticalStructuredStrategy,
    GeopoliticalUnstructuredStrategy,
)
from app.strategies.macroeconomic import MacroeconomicStrategy
from app.strategies.market_data import MarketDataStrategy

# Instantiated once at import time — strategies are stateless (state lives in app/state.py).
_STRATEGY_MAP: dict[tuple[str, str], ClassificationStrategy] = {
    ("MARKET_DATA", "STRUCTURED"):    MarketDataStrategy(),
    ("MACROECONOMIC", "STRUCTURED"):  MacroeconomicStrategy(),
    ("CROSS_ASSET_FLOW", "STRUCTURED"): CrossAssetStrategy(),
    ("GEOPOLITICAL", "STRUCTURED"):   GeopoliticalStructuredStrategy(),
    ("GEOPOLITICAL", "UNSTRUCTURED"): GeopoliticalUnstructuredStrategy(),
}


async def dispatch(request: ClassifyRequest) -> ClassifyResponse:
    """
    Resolve and invoke the correct strategy.

    Raises ValueError for unsupported combinations — FastAPI will convert this
    to a 422 via the exception handler wired up in main.py.
    """
    key = (request.source_category, request.payload_type)
    strategy = _STRATEGY_MAP.get(key)

    if strategy is None:
        raise ValueError(
            f"No strategy registered for source_category={request.source_category!r} "
            f"payload_type={request.payload_type!r}"
        )

    return await strategy.classify(request)
