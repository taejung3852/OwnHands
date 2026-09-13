"""Read-only Dashboard projections and the Presentation cache."""

from .generator import GeneratorError, OpenAICompatibleGenerator, ProviderConfig
from .presentation import PresentationService
from .read_model import DashboardReadModel, ReadModelError

__all__ = [
    "DashboardReadModel",
    "GeneratorError",
    "OpenAICompatibleGenerator",
    "PresentationService",
    "ProviderConfig",
    "ReadModelError",
]
