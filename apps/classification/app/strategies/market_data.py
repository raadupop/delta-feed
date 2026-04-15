"""
MARKET_DATA strategy — z-score anomaly detection.

Computes how many standard deviations the current value deviates from
the per-symbol 20-day rolling window mean. Severity is mapped via tanh
so it is naturally bounded [0, 1] and calibrated for extreme VIX spikes:
  z=20 → 0.76,  z=30 → 0.91,  z=47 → 0.98,  z=60 → 0.994
"""
import math
from collections import deque
from datetime import datetime

import numpy as np

from app.models.requests import ClassifyRequest, MarketDataPayload
from app.models.responses import ClassifyResponse, ScoreType
from app.state import RollingWindow, state
from app.strategies.base import ClassificationStrategy

_TANH_SCALE = 20.0  # divisor inside tanh; controls sensitivity curve

# Grace period before temporal relevance starts decaying.
# 3 calendar days accounts for normal weekend gaps (Friday close → Monday signal).
_EXPECTED_FREQUENCY_SECONDS = 259200.0


def _compute_temporal_relevance(
    signal_time: datetime, last_update: datetime | None, expected_freq: float,
) -> float:
    """Exponential decay of temporal relevance past the expected update frequency."""
    if last_update is None:
        return 1.0  # first observation — assume fresh
    # 0 when signal within the expected frequency
    staleness = max(0.0, (signal_time - last_update).total_seconds() - expected_freq)
    # 1 when signal is exactly at the expected frequency and decays exponentially towards 0 as staleness increases
    return round(math.exp(-staleness / expected_freq), 4)


class MarketDataStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        # ** unpacks a dictionary into keyword arguments for the MarketDataPayload constructor
        payload = MarketDataPayload(**(request.structured_payload or {}))
        symbol = payload.symbol
        current_value = payload.current_value
        signal_time = datetime.fromisoformat(payload.timestamp)

        # Gets the rolling 20-item window for the symbol (if present) or creates a new one if not.
        window = state.market_data_history.setdefault(symbol, RollingWindow(deque(maxlen=20)))

        # Temporal relevance decays as the signal gets stale relative to the last update time of the window.
        temporal_relevance = _compute_temporal_relevance(
            signal_time, window.last_update, _EXPECTED_FREQUENCY_SECONDS,
        )

        # --- edge case: not enough history to compute statistics ---
        if len(window.values) < 2:
            window.append(current_value, signal_time)
            return ClassifyResponse(
                score=0.0,
                score_type=ScoreType.ANOMALY_DETECTION,
                certainty=0.0,
                source_reliability=0.0,
                temporal_relevance=temporal_relevance,
                event_taxonomy=None,
                classification_method="RULE_BASED",
                reasoning_trace=(
                    f"{symbol}={current_value} — insufficient history "
                    f"({len(window.values) - 1} prior values); cannot compute z-score"
                ),
                computed_metrics={"z_score": None, "baseline_mean": None, "baseline_std": None},
            )

        arr = np.array(window.values, dtype=float)
        mean_rolling_window = float(np.mean(arr))
        # Measures variability in the 20-day rolling window
        # using sample correction (ddof=1) for an unbiased estimate since
        # we're treating the window as a subset of the underlying distribution.
        standard_deviation = float(np.std(arr, ddof=1))

        source_reliability = round(0.9 * len(window.values) / 20.0, 4)
        certainty = round(source_reliability * temporal_relevance, 4)

        # --- edge case: flat window (std == 0) ---
        if standard_deviation == 0.0:
            window.append(current_value, signal_time)
            return ClassifyResponse(
                score=0.0,
                score_type=ScoreType.ANOMALY_DETECTION,
                certainty=certainty,
                source_reliability=source_reliability,
                temporal_relevance=temporal_relevance,
                event_taxonomy=None,
                classification_method="RULE_BASED",
                reasoning_trace=(
                    f"{symbol}={current_value} — rolling window has zero variance "
                    f"(mean={mean_rolling_window:.4f}); z-score undefined"
                ),
                computed_metrics={"z_score": None, "baseline_mean": mean_rolling_window, "baseline_std": 0.0},
            )

        z_score = (current_value - mean_rolling_window) / standard_deviation
        severity = float(np.tanh(abs(z_score) / _TANH_SCALE))

        magnitude = (
            "extreme anomaly" if abs(z_score) >= 10
            else "significant anomaly" if abs(z_score) >= 3
            else "moderate deviation" if abs(z_score) >= 2
            else "normal variation"
        )
        reasoning = (
            f"{symbol}={current_value} vs 20-day mean={mean_rolling_window:.4f} std={standard_deviation:.4f}; "
            f"z-score={z_score:.2f} ({magnitude})"
        )

        window.append(current_value, signal_time)

        return ClassifyResponse(
            score=round(severity, 4),
            score_type=ScoreType.ANOMALY_DETECTION,
            certainty=certainty,
            source_reliability=source_reliability,
            temporal_relevance=temporal_relevance,
            event_taxonomy=None,
            classification_method="RULE_BASED",
            reasoning_trace=reasoning,
            computed_metrics={
                "z_score": round(z_score, 4),
                "baseline_mean": round(mean_rolling_window, 4),
                "baseline_std": round(standard_deviation, 4),
            },
        )
