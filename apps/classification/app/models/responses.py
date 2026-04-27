"""
Outbound contract — ClassifyResponse.
"""
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ClassificationMethod = str  # "AI_MODEL" | "RULE_BASED" — kept as str for extensibility


class ScoreType(str, Enum):
    """Discriminator telling the consumer what the score represents.

    ANOMALY_DETECTION: statistical deviation from rolling baseline (z-score, surprise magnitude).
        Produced by MARKET_DATA, MACROECONOMIC, CROSS_ASSET_FLOW strategies.
    EVENT_ASSESSMENT: LLM-judged event impact.
        Produced by GEOPOLITICAL structured and unstructured strategies.
    """
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    EVENT_ASSESSMENT = "EVENT_ASSESSMENT"


class ClassifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0.0, le=1.0)
    score_type: ScoreType
    certainty: float = Field(ge=0.0, le=1.0)
    history_sufficiency: float | None = Field(default=None, ge=0.0, le=1.0)
    temporal_relevance: float | None = Field(default=None, ge=0.0, le=1.0)
    event_taxonomy: str | None = None          # not all strategies produce one
    classification_method: ClassificationMethod
    reasoning_trace: str                        # always present — audit trail
    computed_metrics: dict[str, Any] = Field(default_factory=dict)
