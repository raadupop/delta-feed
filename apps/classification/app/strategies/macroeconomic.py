"""
MACROECONOMIC strategy — ECDF severity over per-indicator |actual - expected|.

Per ADR-0002: severity = ecdf_rank(|deviation|) / N, where
|deviation| = |actual - expected| for surprise-based indicators.

CLS-009 degraded-confidence fallback fires when:
- The indicator is absent from the registry (UnknownSymbolError).
- The history window is degenerate (ADR-0002: fewer than k_min distinct
  values after rounding).
- The history is too thin to rank against (< 2 entries).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.math.deviation import surprise_yoy_deviation
from app.math.ecdf import ecdf_rank, is_window_flat
from app.math.temporal import compute_temporal_relevance
from app.models.requests import ClassifyRequest, MacroeconomicPayload
from app.models.responses import ClassifyResponse, ScoreType
from app.state import UnknownSymbolError, state
from app.strategies.base import ClassificationStrategy

_MIN_HISTORY_FOR_RANK = 2


class MacroeconomicStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        payload = MacroeconomicPayload(**(request.structured_payload or {}))
        symbol = payload.indicator
        actual = payload.actual
        expected = payload.expected
        signal_time = datetime.fromisoformat(payload.release_timestamp)

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
            cadence=indicator_class.cadence,
        )
        history_sufficiency = round(min(1.0, len(window.values) / indicator_class.N), 4)
        certainty = round(history_sufficiency * temporal_relevance, 4)

        deviation = surprise_yoy_deviation(actual, expected)

        if len(window.values) < _MIN_HISTORY_FOR_RANK:
            window.append(deviation, signal_time)
            return _degraded(
                reason=(
                    f"{symbol} actual={actual} expected={expected} "
                    f"|deviation|={deviation} — insufficient history "
                    f"({len(window.values) - 1} prior surprises); ECDF undefined"
                ),
                temporal_relevance=temporal_relevance,
                computed_metrics={
                    "deviation": round(deviation, 4),
                    "ecdf_rank": None,
                    "history_length": len(window.values) - 1,
                },
            )

        # Rank current |deviation| against the stored |deviation| history.
        # For surprise_yoy, the window already contains |deviation| values
        # (we append `deviation`, not `actual`), so the rank is direct.
        # Rank BEFORE appending so the current observation doesn't bias its rank.
        # Flat-window guard: zero-spread history is a guaranteed false positive
        # (any non-zero |deviation| ranks at 1.0). See ADR-0002 2026-04-27
        # amendment 2.
        if is_window_flat(window.values):
            window.append(deviation, signal_time)
            return _degraded(
                reason=(
                    f"{symbol} |deviation|={deviation:.4f} — history window flat "
                    f"(zero spread; rank is undefined)"
                ),
                certainty=certainty,
                history_sufficiency=history_sufficiency,
                temporal_relevance=temporal_relevance,
                computed_metrics={
                    "deviation": round(deviation, 4),
                    "ecdf_rank": None,
                    "window_flat": True,
                },
            )
        rank = ecdf_rank(deviation, window.values)
        window.append(deviation, signal_time)

        return ClassifyResponse(
            score=round(rank, 4),
            score_type=ScoreType.ANOMALY_DETECTION,
            certainty=certainty,
            history_sufficiency=history_sufficiency,
            temporal_relevance=temporal_relevance,
            event_taxonomy=None,
            classification_method="RULE_BASED",
            reasoning_trace=(
                f"{symbol} actual={actual} expected={expected} "
                f"|deviation|={deviation:.4f}; ECDF rank={rank:.4f} "
                f"(history_n={len(window.values) - 1})"
            ),
            computed_metrics={
                "deviation": round(deviation, 4),
                "ecdf_rank": round(rank, 4),
                "window_flat": False,
            },
        )


def _degraded(
    *,
    reason: str,
    certainty: float = 0.0,
    history_sufficiency: float = 0.0,
    temporal_relevance: float = 0.0,
    computed_metrics: dict[str, Any],
) -> ClassifyResponse:
    """CLS-009 degraded-confidence response. Severity is 0; reason in trace."""
    return ClassifyResponse(
        score=0.0,
        score_type=ScoreType.ANOMALY_DETECTION,
        certainty=certainty,
        history_sufficiency=history_sufficiency,
        temporal_relevance=temporal_relevance,
        event_taxonomy=None,
        classification_method="RULE_BASED",
        reasoning_trace=reason,
        computed_metrics=computed_metrics,
    )
