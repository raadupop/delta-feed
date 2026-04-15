"""
CROSS_ASSET_FLOW strategy stub — correlation deviation scoring.

Implemented in build step 5.
"""
from app.models.requests import ClassifyRequest
from app.models.responses import ClassifyResponse
from app.strategies.base import ClassificationStrategy


class CrossAssetStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        # TODO (step 5): parse CrossAssetFlowPayload, compute pairwise correlation z-score
        raise NotImplementedError("CrossAssetStrategy not yet implemented")
