"""
MACROECONOMIC strategy — surprise magnitude scoring.

Implemented in build step 4.
"""
import math
from collections import deque
from datetime import datetime

import numpy as np

from app.models.requests import ClassifyRequest, MacroeconomicPayload
from app.models.responses import ClassifyResponse, ScoreType
from app.state import RollingWindow, state
from app.strategies.base import ClassificationStrategy

# This is a tunable (lambda) parameter that controls how the raw surprise magnitude
# (in std dev units) maps to a 0-1 severity score.
_TANH_SCALE = 3.0

# Grace period before temporal relevance starts decaying.
# 30 calendar days — CPI releases monthly.
_EXPECTED_FREQUENCY_SECONDS = 2592000.0


def _compute_temporal_relevance(
    signal_time: datetime, last_update: datetime | None, expected_freq: float,
) -> float:
    """Exponential decay of temporal relevance past the expected update frequency."""
    if last_update is None:
        return 1.0  # first observation — assume fresh
    staleness = max(0.0, (signal_time - last_update).total_seconds() - expected_freq)
    return round(math.exp(-staleness / expected_freq), 4)


class MacroeconomicStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        payload = MacroeconomicPayload(**(request.structured_payload or {}))
        symbol = payload.indicator
        actual = payload.actual
        expected = payload.expected
        signal_time = datetime.fromisoformat(payload.release_timestamp)

        surprise_history = state.macro_surprise_histories.setdefault(symbol, RollingWindow(deque(maxlen=30)))
        actual_expected_diff = abs(actual - expected)

        temporal_relevance = _compute_temporal_relevance(
            signal_time, surprise_history.last_update, _EXPECTED_FREQUENCY_SECONDS,
        )

        # --- edge case: not enough history to compute statistics ---
        if len(surprise_history.values) < 2:
            surprise_history.append(actual_expected_diff, signal_time)
            return ClassifyResponse(
                score=0.0,
                score_type=ScoreType.ANOMALY_DETECTION,
                certainty=0.0,
                source_reliability=0.0,
                temporal_relevance=temporal_relevance,
                event_taxonomy=None,
                classification_method="RULE_BASED",
                reasoning_trace=(
                    f"{symbol} actual-expected diff={actual_expected_diff} — insufficient history "
                    f"({len(surprise_history.values) - 1} prior values); cannot compute surprise magnitude"
                ),
                computed_metrics={"surprise_magnitude": None, "baseline_mean": None, "baseline_std": None},
            )

        arr = np.array(surprise_history.values, dtype=float)
        historical_std = float(np.std(arr, ddof=1))

        source_reliability = round(min(1.0, 0.5 + 0.5 * len(surprise_history.values) / 30.0), 4)
        certainty = round(source_reliability * temporal_relevance, 4)

        # --- edge case: historical diffs have zero variance ---
        if historical_std == 0.0:
            surprise_history.append(actual_expected_diff, signal_time)
            return ClassifyResponse(
                score=0.0,
                score_type=ScoreType.ANOMALY_DETECTION,
                certainty=certainty,
                source_reliability=source_reliability,
                temporal_relevance=temporal_relevance,
                event_taxonomy=None,
                classification_method="RULE_BASED",
                reasoning_trace=(
                    f"{symbol} actual-expected diff={actual_expected_diff} — historical diffs have zero variance "
                    f"(mean={float(np.mean(arr)):.4f}); surprise magnitude undefined"
                ),
                computed_metrics={"surprise_magnitude": None, "baseline_mean": float(np.mean(arr)), "baseline_std": 0.0},
            )

        surprise_history.append(actual_expected_diff, signal_time)

        # how surprising is this surprise, given how predictable this indicator normally is (historical_std)?
        surprise_magnitude = round(actual_expected_diff / historical_std, 4)
        # Maps surprise magnitude to a 0-1 severity score using a tanh curve for smooth saturation.
        severity = float(np.tanh(surprise_magnitude / _TANH_SCALE))

        magnitude_label = (
            "extreme surprise" if surprise_magnitude >= 4
            else "large surprise" if surprise_magnitude >= 2
            else "moderate surprise" if surprise_magnitude >= 1
            else "minor surprise"
        )

        historical_mean = float(np.mean(arr))
        reasoning = (
            f"{symbol} actual={actual} expected={expected} diff={actual_expected_diff} "
            f"vs historical std={historical_std:.4f}; "
            f"surprise_magnitude={surprise_magnitude:.2f} ({magnitude_label})"
        )

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
                "surprise_magnitude": round(surprise_magnitude, 4),
                "baseline_mean": round(historical_mean, 4),
                "baseline_std": round(historical_std, 4),
            },
        )
