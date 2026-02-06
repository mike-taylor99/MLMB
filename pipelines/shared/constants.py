"""
Constants shared across pipeline jobs.
Mirrors the feature definitions from the training notebook.
"""

# Column labels for metadata (non-stat) fields in gamelogs
META_LABELS = [
    "Rk", "Gtm", "Date", "Location", "Opp key", "Type", "Rslt", "Tm", "Opp"
]

# Column labels for raw stat fields in gamelogs
STAT_LABELS = [
    "OT", "FG", "FGA", "FG%", "3P", "3PA", "3P%", "2P", "2PA", "2P%",
    "eFG%", "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST", "STL", "BLK",
    "TOV", "PF", "ORtg", "DRtg", "Pace", "FTr", "3PAr", "TS%", "TRB%",
    "AST%", "STL%", "BLK%", "TOV%", "ORB%", "FT/FGA",
]

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
    f"{stat}{suffix}"
    for stat in STAT_LABELS
    for suffix in MA_SUFFIXES
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
