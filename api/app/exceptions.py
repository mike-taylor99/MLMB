"""Custom exceptions for the API.

Raise these exceptions in route handlers - they'll be caught by
exception handlers in main.py and converted to proper HTTP responses.
"""

from app.constants import VALID_SPORTS


class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(APIError):
    """Request is not authenticated."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__("authentication_required", message, 401)


class ValidationError(APIError):
    """Input validation failed."""

    def __init__(self, message: str):
        super().__init__("validation_error", message, 400)


class NotFoundError(APIError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__("not_found", f"{resource} not found: {identifier}", 404)


class InvalidSportError(APIError):
    """Invalid sport code provided."""

    def __init__(self, sport: str):
        super().__init__(
            "invalid_sport",
            f"sport must be one of: {', '.join(VALID_SPORTS)}",
            400,
        )


class BatchTooLargeError(APIError):
    """Batch size exceeds maximum."""

    def __init__(self, size: int, max_size: int):
        super().__init__(
            "batch_too_large",
            f"Batch size {size} exceeds maximum of {max_size}",
            400,
        )


class TeamNotFoundError(NotFoundError):
    """Team not found."""

    def __init__(self, team_id: str):
        super().__init__("Team", team_id)


class PredictionNotFoundError(NotFoundError):
    """Prediction not found."""

    def __init__(self, prediction_id: str):
        super().__init__("Prediction", prediction_id)


class TournamentNotFoundError(NotFoundError):
    """Tournament not found."""

    def __init__(self, tournament_id: str):
        super().__init__("Tournament", tournament_id)


class BracketNotFoundError(NotFoundError):
    """Bracket not found."""

    def __init__(self, bracket_id: str):
        super().__init__("Bracket", bracket_id)


class BracketLockedError(APIError):
    """Tournament brackets are locked."""

    def __init__(self):
        super().__init__(
            "bracket_locked",
            "Tournament brackets are locked — picks can no longer be changed",
            403,
        )


class BracketLimitError(APIError):
    """User has too many brackets for this tournament."""

    def __init__(self, limit: int):
        super().__init__(
            "bracket_limit",
            f"Maximum of {limit} brackets per tournament",
            400,
        )
