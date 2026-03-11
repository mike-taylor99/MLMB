"""
Web scraping helpers for Sports Reference.
Downloads gamelog HTML and parses opponent keys.
"""

import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup

from shared.constants import SCRAPE_HEADERS, SCRAPE_DELAY

logger = logging.getLogger(__name__)


def _get_gamelog_url(
    school_key: str, season: int, advanced: bool = False, is_womens: bool = False
) -> str:
    gender = "women" if is_womens else "men"
    suffix = "-gamelogs-advanced.html" if advanced else "-gamelogs.html"
    return f"https://www.sports-reference.com/cbb/schools/{school_key}/{gender}/{season}{suffix}"


def get_data_dir(school_key: str, season: int, is_womens: bool = False) -> str:
    """Return the local directory path for a team's season data."""
    gender = "women" if is_womens else "men"
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    path = os.path.join(base, "seasons", str(season), school_key, gender)
    os.makedirs(path, exist_ok=True)
    return path


def get_team_season_file_path(
    school_key: str, season: int, filename: str, is_womens: bool = False
) -> str:
    """Return the full file path for a team's season data file."""
    return os.path.join(get_data_dir(school_key, season, is_womens), filename)


def download_gamelog(school_key: str, season: int, is_womens: bool = False) -> None:
    """Download basic and advanced gamelog HTML for a single team/season."""
    for advanced in [False, True]:
        url = _get_gamelog_url(school_key, season, advanced, is_womens)
        suffix = "advanced" if advanced else "basic"

        time.sleep(SCRAPE_DELAY)
        response = requests.get(url, headers=SCRAPE_HEADERS)

        if response.status_code == 429:
            logger.warning(f"Rate limited on {school_key}, waiting 10s...")
            time.sleep(10)
            response = requests.get(url, headers=SCRAPE_HEADERS)

        if response.status_code != 200:
            logger.warning(
                f"Failed to download {suffix} gamelog for {school_key} ({response.status_code})"
            )
            return

        file_path = get_team_season_file_path(
            school_key, season, f"{school_key}_{suffix}.html", is_womens
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response.content.decode("utf-8"))


def download_gamelogs(
    school_keys: list[str], season: int, is_womens: bool = False
) -> None:
    """Download gamelogs for all teams in a season."""
    for i, key in enumerate(school_keys):
        logger.info(f"Downloading gamelogs: {key} ({i + 1}/{len(school_keys)})")
        download_gamelog(key, season, is_womens)


def get_opposing_school_keys(
    school_key: str, season: int, advanced: bool = False, is_womens: bool = False
) -> list[str]:
    """Parse HTML table to extract opponent SR school keys."""
    suffix = "advanced" if advanced else "basic"
    html_path = get_team_season_file_path(
        school_key, season, f"{school_key}_{suffix}.html", is_womens
    )

    opp_keys = []
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr")

        for row in rows[2:]:
            # Skip mid-table header rows (class="thead") that have no <td> cells
            tds = row.find_all("td")
            if not tds:
                continue
            try:
                link = tds[3].find("a")["href"]
                key = re.search(r"/schools/([^/]+)/", link).group(1)
                if is_womens and "_w" in key:
                    key = key.replace("_w", "")
                opp_keys.append(key)
            except (IndexError, TypeError, AttributeError):
                opp_keys.append("")

    return opp_keys


def get_ap_top_25(season: int, is_womens: bool = False) -> list[str]:
    """Scrape AP Top 25 team keys from Sports Reference polls page."""
    gender = "women" if is_womens else "men"
    url = f"https://www.sports-reference.com/cbb/seasons/{gender}/{season}-polls.html"

    logger.info(f"Fetching AP Top 25 from: {url}")
    response = requests.get(url, headers=SCRAPE_HEADERS)

    if response.status_code == 429:
        logger.warning("Rate limited, waiting 10s...")
        time.sleep(10)
        response = requests.get(url, headers=SCRAPE_HEADERS)

    if response.status_code != 200:
        logger.error(f"Failed to fetch AP Top 25: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    teams = []

    for table in soup.find_all("table"):
        table_id = table.get("id", "")
        if "current-poll" in table_id.lower() or "ap" in table_id.lower():
            for link in table.find_all("a"):
                href = link.get("href", "")
                match = re.search(r"/cbb/schools/([^/]+)/", href)
                if match:
                    school_key = match.group(1)
                    if school_key not in teams:
                        teams.append(school_key)
                    if len(teams) >= 25:
                        break
            if teams:
                break

    logger.info(f"Found {len(teams)} AP Top 25 teams")
    return teams[:25]
