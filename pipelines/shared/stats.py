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
    META_LABELS, STAT_LABELS, FINAL_FEATURES_NO_OPP, LATEST, DEFAULT_SPANS,
)
from shared.scraper import (
    download_gamelogs, get_team_season_file_path,
)
from shared.parser import (
    create_basic_gamelog, create_advanced_gamelog,
    combine_basic_advanced, generate_moving_averages,
)
from shared.blob import upload_blob

logger = logging.getLogger(__name__)


def _load_team_keys(is_womens: bool = False) -> list[str]:
    """Load SR school keys from team CSV."""
    gender = "womens" if is_womens else "mens"
    csv_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", f"{gender}_teams.csv")
    )
    df = pd.read_csv(csv_path)
    return df["SR key"].tolist()


def generate_team_stats(season: int, spans: list[int] = DEFAULT_SPANS, is_womens: bool = False) -> dict:
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
    logger.info(f"Downloading gamelogs for {len(teams)} teams (season {season}, {'W' if is_womens else 'M'})")
    download_gamelogs(teams, season, is_womens)

    # Step 2: Parse basic + advanced CSVs
    logger.info("Parsing basic gamelogs...")
    for key in tqdm(teams, desc="Basic CSV"):
        try:
            create_basic_gamelog(key, season, is_womens)
        except (ValueError, FileNotFoundError):
            continue

    logger.info("Parsing advanced gamelogs...")
    for key in tqdm(teams, desc="Advanced CSV"):
        try:
            create_advanced_gamelog(key, season, is_womens)
        except (ValueError, FileNotFoundError):
            continue

    # Step 3: Combine basic + advanced
    logger.info("Merging basic + advanced gamelogs...")
    for key in tqdm(teams, desc="Merge"):
        try:
            combine_basic_advanced(key, season, is_womens)
        except FileNotFoundError:
            continue

    # Step 4: Generate moving averages with LATEST row
    logger.info("Computing moving averages...")
    for span in spans:
        for key in tqdm(teams, desc=f"MA (span={span})"):
            try:
                generate_moving_averages(key, season, span, keep_latest=True, is_womens=is_womens)
            except FileNotFoundError:
                continue

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
        latest_stats[str(span)] = {}
        for key in tqdm(teams, desc=f"Latest (span={span})"):
            file_path = get_team_season_file_path(key, season, f"{key}_{span}ma.csv", is_womens)

            if not os.path.exists(file_path):
                continue

            df = pd.read_csv(file_path)
            if df.shape[0] < 1:
                logger.warning(f"No data for {key}")
                continue

            # Last real date (not LATEST sentinel)
            real_rows = df.loc[(df["Date"] != LATEST) & (df["Opp key"] != LATEST)]
            date = real_rows["Date"].iat[-1]

            # Only keep the LATEST row
            df = df.loc[(df["Date"] == LATEST) & (df["Opp key"] == LATEST)]
            assert df.shape[0] == 1

            # Remove meta + raw stat columns, keep only MA features
            df = df.drop(META_LABELS, axis=1)
            df = df.drop(STAT_LABELS, axis=1)
            df = df.reindex(FINAL_FEATURES_NO_OPP, axis=1)

            assert len(df.columns) == len(FINAL_FEATURES_NO_OPP)

            latest_stats[str(span)][key] = {
                "lastPlayed": date,
                "stats": df.iloc[0].tolist(),
            }

    return latest_stats


def generate_and_upload_team_stats(
    season: int, spans: list[int] = DEFAULT_SPANS, connection_string: str | None = None
) -> None:
    """Generate team stats for both genders and upload to blob storage."""
    for is_womens in [False, True]:
        sport = "ncaaw_basketball" if is_womens else "ncaam_basketball"
        logger.info(f"=== Generating {sport} team stats ===")

        stats = generate_team_stats(season, spans, is_womens)

        blob_name = f"{sport}/team-stats"
        data = json.dumps(stats, indent=2)

        if connection_string:
            upload_blob(connection_string, blob_name, data)
            logger.info(f"Uploaded {blob_name} to blob storage")
        else:
            # Write locally as fallback
            out_file = f"{sport}_team_stats.json"
            with open(out_file, "w") as f:
                f.write(data)
            logger.info(f"Wrote {out_file} (no connection string — local only)")
