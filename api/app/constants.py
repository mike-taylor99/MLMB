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
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"


class Span(int, Enum):
    """Valid moving average spans."""

    THREE = 3
    FIVE = 5
    SEVEN = 7


# Type aliases for Literal types (useful for OpenAPI docs)
SportType = Literal["ncaam_basketball", "ncaaw_basketball"]
# Only ensemble is active; individual models can be re-enabled later
ModelTypeStr = Literal["ensemble"]
SpanType = Literal[3, 5, 7]

# Lists for validation (derived from enums)
VALID_SPORTS = [s.value for s in Sport]
VALID_SPANS = [s.value for s in Span]

# Only ensemble models are active; individual models can be re-enabled later
VALID_MODELS = [ModelType.ENSEMBLE.value]
