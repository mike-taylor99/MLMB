"""
Top 25 Rankings Pipeline — Container Apps Job entrypoint.

Scrapes the AP Top 25, runs batch predictions via the MLMB API,
aggregates win probabilities, and uploads rankings to blob storage.

Usage:
    python -m top25.generate

Environment variables:
    AZURE_STORAGE_CONNECTION_STRING  — Required for blob upload.
    API_BASE_URL                     — MLMB API URL (default: production FQDN).
"""

import json
import logging
import os
import sys
import time
from itertools import permutations

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

# Ensure shared modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.season import current_season_year, is_in_season
from shared.scraper import get_ap_top_25
from shared.blob import upload_blob
from shared.constants import DEFAULT_SPANS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [top25] %(message)s",
)
logger = logging.getLogger(__name__)

# Max predictions per API batch call
BATCH_SIZE = 500

# Default API URL (Container Apps internal or public FQDN)
DEFAULT_API_URL = "https://mlmb-api.purplesand-9a1718e2.eastus.azurecontainerapps.io"

def _create_retry_session() -> requests.Session:
    """Create a requests session with retry + exponential backoff for cold-start tolerance."""
    retry = Retry(
        total=5,
        backoff_factor=5,                      # 5s, 10s, 20s, 40s, 80s
        status_forcelist=[503, 507],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _warmup_api(session: requests.Session, api_base_url: str) -> None:
    """Send a health check to wake the API if it's scaled to zero."""
    logger.info("Warming up API...")
    try:
        resp = session.get(f"{api_base_url}/health", timeout=180)
        if resp.status_code == 200:
            logger.info("API is ready.")
            return
        logger.warning(f"API warmup returned {resp.status_code} — proceeding anyway.")
    except requests.exceptions.ConnectionError:
        logger.warning("API warmup failed — proceeding anyway.")


def generate_top25(
    sport: str,
    api_base_url: str,
    season: int,
    session: requests.Session,
    spans: list[int] = DEFAULT_SPANS,
) -> dict:
    """
    Generate top 25 rankings for a sport by running all pairwise predictions.

    Returns:
        Dict of { school_key: aggregated_score } sorted descending.
    """
    is_womens = sport == "ncaaw_basketball"
    top_25_teams = get_ap_top_25(season=season, is_womens=is_womens)

    if len(top_25_teams) < 25:
        logger.warning(f"Only found {len(top_25_teams)} AP Top 25 teams")

    if not top_25_teams:
        logger.error("No teams found — aborting.")
        return {}

    # Build all prediction requests
    matchups = list(permutations(top_25_teams, 2))
    batch_requests = []
    for team1, team2 in matchups:
        for span in spans:
            for neutral in [True, False]:
                batch_requests.append({
                    "home_team": team1,
                    "away_team": team2,
                    "sport": sport,
                    "span": span,
                    "neutral": neutral,
                })

    total = len(batch_requests)
    logger.info(f"Sending {total} predictions in {(total + BATCH_SIZE - 1) // BATCH_SIZE} batches")

    # Send batch requests
    all_predictions = []
    start = time.time()

    for i in tqdm(range(0, total, BATCH_SIZE), desc="Batches"):
        chunk = batch_requests[i : i + BATCH_SIZE]
        try:
            resp = session.post(f"{api_base_url}/predictions/batch", json={"input": chunk}, timeout=300)
        except requests.exceptions.ConnectionError:
            logger.error(f"Batch {i // BATCH_SIZE + 1} failed after retries")
            continue

        if resp.status_code != 200:
            logger.error(f"Batch {i // BATCH_SIZE + 1} failed: {resp.status_code} — {resp.text}")
            continue

        result = resp.json()
        all_predictions.extend(result.get("output", []))

    elapsed = time.time() - start
    logger.info(f"Complete in {elapsed:.1f}s ({len(all_predictions)} predictions)")

    # Aggregate scores
    scores: dict[str, float] = {}
    errors = 0

    for pred in all_predictions:
        if pred.get("type") == "error":
            errors += 1
            continue

        home = pred["home_team"]
        away = pred["away_team"]
        home_prob = pred.get("home_win_probability", 0.5)

        scores[home] = scores.get(home, 0) + round(home_prob, 4)
        scores[away] = scores.get(away, 0) + round(1 - home_prob, 4)

    if errors:
        logger.warning(f"{errors} prediction errors encountered")

    # Sort descending
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))


def generate_and_upload_top25(
    api_base_url: str,
    season: int,
    connection_string: str | None = None,
) -> bool:
    """Generate top 25 for both genders and upload to blob storage.

    Returns True if all sports generated successfully, False otherwise.
    """
    session = _create_retry_session()
    _warmup_api(session, api_base_url)
    failures = []
    for sport in ["ncaam_basketball", "ncaaw_basketball"]:
        logger.info(f"=== Generating {sport} top 25 ===")

        rankings = generate_top25(sport, api_base_url, season, session)

        if not rankings:
            logger.warning(f"No rankings generated for {sport}")
            failures.append(sport)
            continue

        # Log top 5
        for i, (team, score) in enumerate(list(rankings.items())[:5], 1):
            logger.info(f"  #{i} {team}: {score:.2f}")

        blob_name = f"{sport}/top25"
        data = json.dumps(rankings, indent=2)

        if connection_string:
            upload_blob(connection_string, blob_name, data)
            logger.info(f"Uploaded {blob_name} to blob storage")
        else:
            out_file = f"{sport}_top25.json"
            with open(out_file, "w") as f:
                f.write(data)
            logger.info(f"Wrote {out_file} (no connection string — local only)")

    return len(failures) == 0


def main() -> None:
    if not is_in_season():
        logger.info("Off-season — skipping top 25 generation.")
        return

    season = current_season_year()
    api_base_url = os.environ.get("API_BASE_URL", DEFAULT_API_URL)
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING not set — results will only be written locally.")

    logger.info(f"Starting top 25 pipeline for season {season}")
    logger.info(f"API base URL: {api_base_url}")

    success = generate_and_upload_top25(api_base_url, season, connection_string)
    logger.info("Top 25 pipeline complete.")

    if not success:
        logger.error("One or more sports failed to generate rankings.")
        sys.exit(1)


if __name__ == "__main__":
    main()
