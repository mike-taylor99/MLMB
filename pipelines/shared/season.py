"""
Season date helpers — determine current season and whether we're in-season.
"""

from datetime import date, datetime


def current_season_year() -> int:
    """
    Return the season year for the current date.
    The NCAA basketball season spans Nov–Apr.  A game played in Jan 2026
    belongs to the 2026 season (which started Nov 2025).
    """
    today = date.today()
    # If we're in Nov or Dec, season year is next calendar year
    if today.month >= 11:
        return today.year + 1
    # Jan–Oct: season year is current calendar year
    return today.year


def is_in_season(ref_date: date | None = None) -> bool:
    """
    Return True if ref_date (default: today) falls within the NCAA
    basketball season window: November 1 – April 15.
    """
    today = ref_date or date.today()
    # In-season: Nov 1 – Dec 31 OR Jan 1 – Apr 15
    if today.month >= 11:
        return True
    if today.month <= 3:
        return True
    if today.month == 4 and today.day <= 15:
        return True
    return False
