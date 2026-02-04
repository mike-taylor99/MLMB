"""Domain constants and enums for the API.

Single source of truth for all domain-specific constants.
"""

from enum import Enum
from typing import Literal


class Sport(str, Enum):
    """Supported sports."""
    NCAAM_BASKETBALL = "ncaam_basketball"
    NCAAW_BASKETBALL = "ncaaw_basketball"


class ModelType(str, Enum):
    """Available prediction models."""
    ENSEMBLE = "ensemble"
    LOGISTIC_REGRESSION = "logistic_regression"
    KNN = "knn"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    MLP = "mlp"
    SVM = "svm"


class Span(int, Enum):
    """Valid moving average spans."""
    THREE = 3
    FIVE = 5
    SEVEN = 7


# Type aliases for Literal types (useful for OpenAPI docs)
SportType = Literal["ncaam_basketball", "ncaaw_basketball"]
ModelTypeStr = Literal[
    "ensemble", "logistic_regression", "knn", "random_forest",
    "gradient_boosting", "mlp", "svm"
]
SpanType = Literal[3, 5, 7]

# Lists for validation (derived from enums)
VALID_SPORTS = [s.value for s in Sport]
VALID_MODELS = [m.value for m in ModelType]
VALID_SPANS = [s.value for s in Span]
