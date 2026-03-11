"""
Gamelog parsing — extract CSVs from raw HTML, compute moving averages,
merge home/away opponent data.
"""

import logging
from io import StringIO
import numpy as np
import pandas as pd

from shared.constants import META_LABELS, LATEST, RENAME_OPPOSING_COLS
from shared.scraper import get_team_season_file_path, get_opposing_school_keys

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Basic gamelog CSV
# ---------------------------------------------------------------------------


def create_basic_gamelog(school_key: str, season: int, is_womens: bool = False) -> None:
    """Parse basic gamelog HTML into a clean CSV.

    Keeps opponent box score columns prefixed with 'def_' to capture
    the team's defensive profile (what opponents did against them).
    """
    html_path = get_team_season_file_path(
        school_key, season, f"{school_key}_basic.html", is_womens
    )
    with open(html_path, "r", encoding="utf-8") as f:
        df = pd.read_html(StringIO(f.read()))[0]

    # Flatten multi-level columns, prefixing opponent box score stats with 'def_'
    # These represent the team's DEFENSIVE performance (what opponents did against them)
    df.columns = [f"def_{c[1]}" if c[0] == "Opponent" else c[1] for c in df.columns]
    df = df.rename(columns={"Unnamed: 3_level_1": "Location"})

    # Remove unnamed columns
    unnamed = [c for c in df.columns if "Unnamed" in c]
    df = df.drop(unnamed, axis=1)

    # Drop repeating header rows
    df = df[df.Tm != "Tm"]
    df = df[df.FG != "School"]

    # Replace Opp name with Opp key
    idx = df.columns.to_list().index("Opp")
    df.columns.values[idx] = "Opp name"
    opp_keys = get_opposing_school_keys(school_key, season, False, is_womens)
    assert df.shape[0] == len(opp_keys), (
        f"Basic gamelog row count mismatch for {school_key}: "
        f"{df.shape[0]} rows vs {len(opp_keys)} opponent keys"
    )
    df["Opp name"] = opp_keys
    df = df.rename(columns={"Opp name": "Opp key"})

    # Remove averages row
    df["Rk"] = pd.to_numeric(df["Rk"], errors="coerce")
    df = df.dropna(subset=["Rk"])

    csv_path = get_team_season_file_path(
        school_key, season, f"{school_key}_basic.csv", is_womens
    )
    df.to_csv(csv_path, index=False)


# ---------------------------------------------------------------------------
# Advanced gamelog CSV
# ---------------------------------------------------------------------------


def create_advanced_gamelog(
    school_key: str, season: int, is_womens: bool = False
) -> None:
    """Parse advanced gamelog HTML into a clean CSV.

    Keeps defensive four factors prefixed with 'def_'.
    Normalizes 'def_DRB%' to 'def_ORB%' for cross-season consistency
    (Sports Reference renamed this column around the 2025 season).
    """
    html_path = get_team_season_file_path(
        school_key, season, f"{school_key}_advanced.html", is_womens
    )
    with open(html_path, "r", encoding="utf-8") as f:
        df = pd.read_html(StringIO(f.read()))[0]

    # Flatten multi-level columns, prefixing defensive four factors with 'def_'
    df.columns = [
        f"def_{c[1]}" if "Defensive" in str(c[0]) else c[1] for c in df.columns
    ]

    # Normalize: older seasons (pre-2025) use 'def_DRB%', newer use 'def_ORB%'
    df.rename(columns={"def_DRB%": "def_ORB%"}, inplace=True)

    df = df.rename(columns={"Unnamed: 3_level_1": "Location"})

    unnamed = [c for c in df.columns if "Unnamed" in c]
    df = df.drop(unnamed, axis=1)

    df = df[df.Tm != "Tm"]
    df = df[df["eFG%"] != "Offensive Four Factors"]

    # Replace Opp name with Opp key
    idx = df.columns.to_list().index("Opp")
    df.columns.values[idx] = "Opp name"
    opp_keys = get_opposing_school_keys(school_key, season, True, is_womens)
    assert df.shape[0] == len(opp_keys), (
        f"Advanced gamelog row count mismatch for {school_key}: "
        f"{df.shape[0]} rows vs {len(opp_keys)} opponent keys"
    )
    df["Opp name"] = opp_keys
    df = df.rename(columns={"Opp name": "Opp key"})

    df["Rk"] = pd.to_numeric(df["Rk"], errors="coerce")
    df = df.dropna(subset=["Rk"])

    csv_path = get_team_season_file_path(
        school_key, season, f"{school_key}_advanced.csv", is_womens
    )
    df.to_csv(csv_path, index=False)


# ---------------------------------------------------------------------------
# Merge basic + advanced
# ---------------------------------------------------------------------------


def combine_basic_advanced(
    school_key: str, season: int, is_womens: bool = False
) -> None:
    """Merge basic and advanced gamelog CSVs into a single file."""
    basic_path = get_team_season_file_path(
        school_key, season, f"{school_key}_basic.csv", is_womens
    )
    adv_path = get_team_season_file_path(
        school_key, season, f"{school_key}_advanced.csv", is_womens
    )

    basic_df = pd.read_csv(basic_path)
    adv_df = pd.read_csv(adv_path)

    # Drop def_eFG% from advanced (already present in basic opponent stats) to avoid merge conflicts
    adv_df = adv_df.drop(columns=["def_eFG%"], errors="ignore")

    merge_cols = [
        "Rk",
        "Gtm",
        "Date",
        "Location",
        "Opp key",
        "Type",
        "Rslt",
        "Tm",
        "Opp",
        "OT",
        "eFG%",
    ]
    merged = pd.merge(basic_df, adv_df, on=merge_cols)

    merged["Location"] = merged["Location"].fillna("H")
    merged["OT"] = np.where(merged["OT"].notna(), 1, 0)

    out_path = get_team_season_file_path(
        school_key, season, f"{school_key}_merged.csv", is_womens
    )
    merged.to_csv(out_path, index=False)


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------


def generate_moving_averages(
    school_key: str,
    season: int,
    span: int = 5,
    keep_latest: bool = False,
    is_womens: bool = False,
) -> None:
    """Compute SMA/CMA/EMA for all stat columns and save to CSV."""
    file_path = get_team_season_file_path(
        school_key, season, f"{school_key}_merged.csv", is_womens
    )
    df = pd.read_csv(file_path)
    df.dropna(inplace=True)

    if keep_latest:
        # Append synthetic "LATEST" row with last-game stats
        last_row = pd.DataFrame(df.tail(1).values, columns=df.columns)
        df = pd.concat([df, last_row], ignore_index=True)
        df.loc[df.index[-1], "Date"] = LATEST
        df.loc[df.index[-1], "Opp key"] = LATEST

    for col in df.columns:
        if col in META_LABELS:
            continue

        sma = df[col].rolling(window=span).mean().shift(1)
        cma = df[col].expanding(min_periods=span).mean().shift(1)
        ema = df[col].ewm(span=span, adjust=False).mean().shift(1)

        ma_df = pd.DataFrame(
            {
                f"{col}_SMA": sma,
                f"{col}_CMA": cma,
                f"{col}_EMA": ema,
            }
        )
        df = pd.concat([df, ma_df], axis=1)

    df.dropna(inplace=True)

    out_path = get_team_season_file_path(
        school_key, season, f"{school_key}_{span}ma.csv", is_womens
    )
    df.to_csv(out_path, index=False)


# ---------------------------------------------------------------------------
# Merge opponent data
# ---------------------------------------------------------------------------


def merge_opponent_data(
    school_key: str, season: int, span: int = 5, is_womens: bool = False
) -> None:
    """For each game, look up opponent stats and merge into home/away rows."""
    file_path = get_team_season_file_path(
        school_key, season, f"{school_key}_{span}ma.csv", is_womens
    )
    df = pd.read_csv(file_path)

    if df.shape[0] < 1:
        return

    home_df, away_df = pd.DataFrame(), pd.DataFrame()

    for _, row in df.iterrows():
        try:
            game = row.to_dict()
            opp_key = game.get("Opp key")

            opp_path = get_team_season_file_path(
                opp_key, season, f"{opp_key}_{span}ma.csv", is_womens
            )
            opp_df = pd.read_csv(opp_path)

            opp_df = opp_df.loc[
                (opp_df["Opp key"] == school_key) & (opp_df["Date"] == game.get("Date"))
            ]
            cur_df = df[
                (df["Opp key"] == game.get("Opp key"))
                & (df["Date"] == game.get("Date"))
            ]

            if game.get("Location") == "@":
                home_df = pd.concat([home_df, opp_df])
                away_df = pd.concat([away_df, cur_df])
            else:
                home_df = pd.concat([home_df, cur_df])
                away_df = pd.concat([away_df, opp_df])
        except FileNotFoundError:
            continue

    # Flip score columns for away team
    away_df.rename(columns={"Tm": "Opp", "Opp": "Tm"}, inplace=True)
    away_df = away_df.drop(["Location", "Opp key", "Rslt", "Rk", "Gtm", "Type"], axis=1)
    away_df.rename(columns=RENAME_OPPOSING_COLS, inplace=True)

    merged = pd.merge(home_df, away_df, on=["Date", "Tm", "Opp"])
    merged = merged.sort_values(by="Date")

    out_path = get_team_season_file_path(
        school_key, season, f"{school_key}_{span}span_full.csv", is_womens
    )
    merged.to_csv(out_path, index=False)
