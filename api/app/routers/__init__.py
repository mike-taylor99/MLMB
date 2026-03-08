"""Routers package for FastAPI endpoints."""

from app.routers import predictions, rankings, teams, tournaments, brackets

__all__ = ["predictions", "rankings", "teams", "tournaments", "brackets"]
