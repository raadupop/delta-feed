"""
Abstract base class for all classification strategies.
"""
from abc import ABC, abstractmethod

from app.models.requests import ClassifyRequest
from app.models.responses import ClassifyResponse


class ClassificationStrategy(ABC):
    """All strategies implement this contract."""

    @abstractmethod
    async def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        """Run classification and return a fully-populated response."""
        ...
