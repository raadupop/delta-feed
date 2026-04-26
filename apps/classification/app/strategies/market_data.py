"""
MARKET_DATA strategy — ECDF severity over per-symbol rolling |deviation|.

Per ADR-0002: severity = ecdf_rank(|deviation|) / N, where
|deviation| = |current_value - rolling_median(history)| for vol indices.

CLS-009 degraded-confidence fallback fires when:
- The symbol is absent from the registry (UnknownSymbolError).
- The rolling IQR of the history window is below the class's D floor.
- The history is too thin to rank against (< 2 entries).
"""
from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any

from app.math.deviation import pct_change_deviation
from app.math.dispersion import is_dispersion_below_floor, rolling_iqr
from app.math.ecdf import ecdf_rank
from app.math.temporal import compute_temporal_relevance
from app.models.requests import ClassifyRequest, MarketDataPayload
from app.models.responses import ClassifyResponse, ScoreType
from app.state import UnknownSymbolError, state
from app.strategies.base import ClassificationStrategy

_MIN_HISTORY_FOR_RANK = 2


class MarketDataStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        payload = MarketDataPayload(**(request.structured_payload or {}))
        symbol = payload.symbol
        current_value = payload.current_value
        signal_time = datetime.fromisoformat(payload.timestamp)

        try:
            window = state.get_or_create_window(symbol)
        except UnknownSymbolError:
            return _degraded(
                reason=f"{symbol} not in registry — CLS-009 degraded confidence",
                computed_metrics={
                    "deviation": None,
                    "ecdf_rank": None,
                    "unknown_symbol": True,
                },
            )

        indicator_class = window.indicator_class
        temporal_relevance = compute_temporal_relevance(
            signal_time, window.last_update, indicator_class.expected_frequency_seconds,
        )
        source_reliability = round(min(1.0, len(window.values) / indicator_class.N), 4)
        certainty = round(source_reliability * temporal_relevance, 4)

        deviation = pct_change_deviation(current_value, window.values)

        # CLS-009 trip: too little history to rank against.
        if len(window.values) < _MIN_HISTORY_FOR_RANK:
            window.append(current_value, signal_time)
            return _degraded(
                reason=(
                    f"{symbol}={current_value} — insufficient history "
                    f"({len(window.values) - 1} prior values); ECDF undefined"
                ),
                temporal_relevance=temporal_relevance,
                computed_metrics={
                    "deviation": round(deviation, 4),
                    "ecdf_rank": None,
                    "history_length": len(window.values) - 1,
                },
            )

        iqr = rolling_iqr(window.values)
        if is_dispersion_below_floor(window.values, indicator_class.D):
            window.append(current_value, signal_time)
            return _degraded(
                reason=(
                    f"{symbol}={current_value} — history IQR={iqr:.4f} below "
                    f"floor D={indicator_class.D} (CLS-009 dispersion-floor trip)"
                ),
                certainty=certainty,
                source_reliability=source_reliability,
                temporal_relevance=temporal_relevance,
                computed_metrics={
                    "deviation": round(deviation, 4),
                    "ecdf_rank": None,
                    "rolling_iqr": round(iqr, 4),
                    "dispersion_below_floor": True,
                },
            )

        # Rank |deviation| against historical |deviations| derived from the
        # same window (each historical level vs the current rolling median).
        # Rank BEFORE appending so the current observation doesn't bias its
        # own rank.
        levels = list(window.values)
        m = median(levels)
        history_devs = [abs(v - m) for v in levels]
        rank = ecdf_rank(deviation, history_devs)
        window.append(current_value, signal_time)

        return ClassifyResponse(
            score=round(rank, 4),
            score_type=ScoreType.ANOMALY_DETECTION,
            certainty=certainty,
            source_reliability=source_reliability,
            temporal_relevance=temporal_relevance,
            event_taxonomy=None,
            classification_method="RULE_BASED",
            reasoning_trace=(
                f"{symbol}={current_value} vs history median={m:.4f}; "
                f"|deviation|={deviation:.4f}; ECDF rank={rank:.4f} "
                f"(history_n={len(levels)}, D={indicator_class.D}, IQR={iqr:.4f})"
            ),
            computed_metrics={
                "deviation": round(deviation, 4),
                "ecdf_rank": round(rank, 4),
                "rolling_iqr": round(iqr, 4),
                "dispersion_below_floor": False,
            },
        )


def _degraded(
    *,
    reason: str,
    certainty: float = 0.0,
    source_reliability: float = 0.0,
    temporal_relevance: float = 0.0,
    computed_metrics: dict[str, Any],
) -> ClassifyResponse:
    """CLS-009 degraded-confidence response. Severity is 0; reason in trace."""
    return ClassifyResponse(
        score=0.0,
        score_type=ScoreType.ANOMALY_DETECTION,
        certainty=certainty,
        source_reliability=source_reliability,
        temporal_relevance=temporal_relevance,
        event_taxonomy=None,
        classification_method="RULE_BASED",
        reasoning_trace=reason,
        computed_metrics=computed_metrics,
    )
