"""
Constants shared across pipeline jobs.
Mirrors the feature definitions from the training notebook.
"""

# Column labels for metadata (non-stat) fields in gamelogs
META_LABELS = ["Rk", "Gtm", "Date", "Location", "Opp key", "Type", "Rslt", "Tm", "Opp"]

# Column labels for offensive stat fields in gamelogs
# From basic Team box score + advanced Offensive Four Factors
OFFENSIVE_STAT_LABELS = [
    "OT",
    "FG",
    "FGA",
    "FG%",
    "3P",
    "3PA",
    "3P%",
    "2P",
    "2PA",
    "2P%",
    "eFG%",
    "FT",
    "FTA",
    "FT%",
    "ORB",
    "DRB",
    "TRB",
    "AST",
    "STL",
    "BLK",
    "TOV",
    "PF",
    "ORtg",
    "DRtg",
    "Pace",
    "FTr",
    "3PAr",
    "TS%",
    "TRB%",
    "AST%",
    "STL%",
    "BLK%",
    "TOV%",
    "ORB%",
    "FT/FGA",
]

# Column labels for defensive stat fields in gamelogs
# From basic Opponent box score (21) + advanced Defensive Four Factors (3)
# These capture what opponents did AGAINST this team (i.e., this team's defensive profile)
# Note: Sports Reference renamed 'DRB%' to 'ORB%' in the Defensive Four Factors around 2025;
#       we normalize to 'def_ORB%' in create_advanced_gamelog for consistency across all seasons.
DEFENSIVE_STAT_LABELS = [
    "def_FG",
    "def_FGA",
    "def_FG%",
    "def_3P",
    "def_3PA",
    "def_3P%",
    "def_2P",
    "def_2PA",
    "def_2P%",
    "def_eFG%",
    "def_FT",
    "def_FTA",
    "def_FT%",
    "def_ORB",
    "def_DRB",
    "def_TRB",
    "def_AST",
    "def_STL",
    "def_BLK",
    "def_TOV",
    "def_PF",
    "def_TOV%",
    "def_ORB%",
    "def_FT/FGA",
]

# Combined: all raw stat columns (35 offensive + 24 defensive = 59)
STAT_LABELS = OFFENSIVE_STAT_LABELS + DEFENSIVE_STAT_LABELS

# Sentinel value for the synthetic "latest" row
LATEST = "LATEST"

# Moving average suffixes
MA_SUFFIXES = ["_SMA", "_CMA", "_EMA"]

# Default spans for moving averages
DEFAULT_SPANS = [3, 5, 7]

# HTTP headers to avoid rate limiting on Sports Reference
SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

# Delay between Sports Reference requests (seconds)
SCRAPE_DELAY = 3

# Final ordered feature list for the model (home + away + Neutral + Win)
FINAL_FEATURES_NO_OPP = [
    f"{stat}{suffix}" for stat in STAT_LABELS for suffix in MA_SUFFIXES
]

FINAL_FEATURES = (
    FINAL_FEATURES_NO_OPP
    + [f"opp_{f}" for f in FINAL_FEATURES_NO_OPP]
    + ["Neutral", "Win"]
)

# Rename map: stat columns → opp_ prefixed columns
RENAME_OPPOSING_COLS = {
    item: f"opp_{item}"
    for stat in STAT_LABELS
    for item in [stat, f"{stat}_SMA", f"{stat}_CMA", f"{stat}_EMA"]
}
