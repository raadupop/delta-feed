"""
GEOPOLITICAL strategy stubs — two variants split by payload_type.

Implemented in build steps 6 (structured) and 7 (unstructured).
"""
from app.models.requests import ClassifyRequest
from app.models.responses import ClassifyResponse
from app.strategies.base import ClassificationStrategy


class GeopoliticalStructuredStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        # TODO (step 6): parse GeopoliticalPayload, apply rule scoring, call Claude for reasoning
        raise NotImplementedError("GeopoliticalStructuredStrategy not yet implemented")


class GeopoliticalUnstructuredStrategy(ClassificationStrategy):
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        # TODO (step 7): LangChain + ChromaDB RAG retrieval → Claude extraction
        raise NotImplementedError("GeopoliticalUnstructuredStrategy not yet implemented")
