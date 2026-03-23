"""
Base classes for all REIOS AI models.
Provides a common interface for loading, predicting, and versioning.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ModelOutput:
    """Standard output from any AI model."""
    prediction: Any
    confidence: float | None = None
    features_used: dict | None = None
    model_version: str = "unknown"
    latency_ms: float = 0.0


class ModelBase(ABC):
    """Base class for all REIOS ML models."""

    def __init__(self, model_name: str, model_dir: str = "./data/models"):
        self.model_name = model_name
        self.model_dir = Path(model_dir)
        self.model_version = "0.0.0"
        self.is_loaded = False
        self._model = None

    @abstractmethod
    def load(self, model_path: str | None = None) -> None:
        """Load model from disk."""
        ...

    @abstractmethod
    def predict(self, features: dict) -> ModelOutput:
        """Run prediction on input features."""
        ...

    def get_version(self) -> str:
        return self.model_version

    def health_check(self) -> bool:
        return self.is_loaded

    def get_model_path(self) -> Path:
        return self.model_dir / self.model_name


class HeuristicModel(ModelBase):
    """Base for rule-based models (used before ML models are trained)."""

    def load(self, model_path: str | None = None) -> None:
        self.is_loaded = True
        self.model_version = "heuristic_v1"

    def health_check(self) -> bool:
        return True
