"""
Generate latest team statistics JSON and upload to blob storage.
Orchestrates: download → parse → moving averages → extract latest → upload.
"""

import json
import logging
import os
import pandas as pd
from tqdm import tqdm

from shared.constants import (
    META_LABELS,
    STAT_LABELS,
    FINAL_FEATURES_NO_OPP,
    LATEST,
    DEFAULT_SPANS,
)
from shared.scraper import (
    download_gamelogs,
    get_team_season_file_path,
)
from shared.parser import (
    create_basic_gamelog,
    create_advanced_gamelog,
    combine_basic_advanced,
    generate_moving_averages,
)
from shared.blob import upload_blob

logger = logging.getLogger(__name__)


def _load_team_keys(is_womens: bool = False) -> list[str]:
    """Load SR school keys from team CSV."""
    gender = "womens" if is_womens else "mens"
    csv_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "data", f"{gender}_teams.csv"
        )
    )
    df = pd.read_csv(csv_path)
    return df["SR key"].tolist()


def _run_per_team(teams: list[str], desc: str, fn) -> None:
    """Apply fn to each team, logging and skipping per-team failures.

    A single malformed gamelog must not abort stats generation for every team.
    """
    for key in tqdm(teams, desc=desc):
        try:
            fn(key)
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.warning(f"{desc} failed for {key}: {type(e).__name__}: {e}")


def _last_played_date(key: str, season: int, is_womens: bool) -> str | None:
    """Return the date of the team's most recent completed game."""
    merged_path = get_team_season_file_path(
        key, season, f"{key}_merged.csv", is_womens
    )
    df = pd.read_csv(merged_path).dropna()
    if df.empty:
        return None
    return str(df["Date"].iat[-1])


def _extract_latest(
    key: str, season: int, span: int, is_womens: bool
) -> dict | None:
    """Return {"lastPlayed", "stats"} for a team's LATEST row, or None if unavailable."""
    file_path = get_team_season_file_path(
        key, season, f"{key}_{span}ma.csv", is_womens
    )
    if not os.path.exists(file_path):
        return None

    df = pd.read_csv(file_path)
    df = df.loc[(df["Date"] == LATEST) & (df["Opp key"] == LATEST)]
    # Teams with fewer than `span` completed games have no LATEST row yet
    if df.empty:
        return None
    assert df.shape[0] == 1

    # Remove meta + raw stat columns, keep only MA features
    df = df.drop(META_LABELS, axis=1)
    df = df.drop(STAT_LABELS, axis=1)
    df = df.reindex(FINAL_FEATURES_NO_OPP, axis=1)

    assert len(df.columns) == len(FINAL_FEATURES_NO_OPP)

    return {
        "lastPlayed": _last_played_date(key, season, is_womens),
        "stats": df.iloc[0].tolist(),
    }


def generate_team_stats(
    season: int, spans: list[int] = DEFAULT_SPANS, is_womens: bool = False
) -> dict:
    """
    Full pipeline: scrape gamelogs → parse → compute stats → return JSON dict.

    Returns the stats dict with shape:
    {
        "_meta": { "features": [...], "away_prefix": "opp_", "extra_features": ["Neutral"] },
        "3": { "school_key": { "lastPlayed": "...", "stats": [...] }, ... },
        "5": { ... },
        "7": { ... }
    }
    """
    teams = _load_team_keys(is_womens)
    sport = "ncaaw_basketball" if is_womens else "ncaam_basketball"

    # Step 1: Download gamelogs
    logger.info(
        f"Downloading gamelogs for {len(teams)} teams (season {season}, {'W' if is_womens else 'M'})"
    )
    download_gamelogs(teams, season, is_womens)

    # Step 2: Parse basic + advanced CSVs
    logger.info("Parsing basic gamelogs...")
    _run_per_team(
        teams, "Basic CSV", lambda k: create_basic_gamelog(k, season, is_womens)
    )

    logger.info("Parsing advanced gamelogs...")
    _run_per_team(
        teams, "Advanced CSV", lambda k: create_advanced_gamelog(k, season, is_womens)
    )

    # Step 3: Combine basic + advanced
    logger.info("Merging basic + advanced gamelogs...")
    _run_per_team(
        teams, "Merge", lambda k: combine_basic_advanced(k, season, is_womens)
    )

    # Step 4: Generate moving averages with LATEST row
    logger.info("Computing moving averages...")
    for span in spans:
        _run_per_team(
            teams,
            f"MA (span={span})",
            lambda k: generate_moving_averages(
                k, season, span, keep_latest=True, is_womens=is_womens
            ),
        )

    # Step 5: Extract latest stats
    logger.info("Extracting latest stats per team...")
    latest_stats = {
        "_meta": {
            "features": FINAL_FEATURES_NO_OPP,
            "away_prefix": "opp_",
            "extra_features": ["Neutral"],
        }
    }

    for span in spans:
        span_stats = latest_stats[str(span)] = {}

        def extract(key: str) -> None:
            entry = _extract_latest(key, season, span, is_womens)
            if entry:
                span_stats[key] = entry

        _run_per_team(teams, f"Latest (span={span})", extract)
        logger.info(f"span={span}: latest stats for {len(span_stats)} teams")

    return latest_stats


def generate_and_upload_team_stats(
    season: int, spans: list[int] = DEFAULT_SPANS
) -> bool:
    """Generate team stats for both genders and upload to blob storage.

    Returns True if all sports generated successfully, False otherwise.
    """
    failures = []
    for is_womens in [False, True]:
        sport = "ncaaw_basketball" if is_womens else "ncaam_basketball"
        logger.info(f"=== Generating {sport} team stats ===")

        try:
            stats = generate_team_stats(season, spans, is_womens)
        except Exception as e:
            logger.error(f"Failed to generate {sport} team stats: {e}")
            failures.append(sport)
            continue

        if not any(stats.get(str(span)) for span in spans):
            logger.warning(f"No stats generated for {sport} — keeping existing blob")
            failures.append(sport)
            continue

        blob_name = f"{sport}/team-stats"
        data = json.dumps(stats, indent=2)

        upload_blob(blob_name, data)
        logger.info(f"Uploaded {blob_name} to blob storage")

    return len(failures) == 0
