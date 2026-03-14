"""
Azure AI Foundry agent service for matchup analysis.

Uses the Foundry Agent Service (prompt agent) to generate natural-language
analysis of basketball matchup predictions.
"""

import logging
from threading import Lock
from typing import Any, Dict, List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class AgentService:
    """
    Singleton service for calling the Foundry matchup-analyzer agent.

    Lazily initialises the AIProjectClient and OpenAI client on first use.
    """

    _instance: Optional["AgentService"] = None
    _lock = Lock()

    def __new__(cls) -> "AgentService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._project_client = None
        self._openai_client = None
        self._initialized = True
        logger.info("AgentService initialised (lazy — client created on first call)")

    def _ensure_client(self):
        """Lazily create the AIProjectClient and OpenAI client."""
        if self._openai_client is not None:
            return

        settings = get_settings()
        if not settings.foundry_project_endpoint:
            raise ValueError(
                "FOUNDRY_PROJECT_ENDPOINT not configured — "
                "matchup analysis is unavailable"
            )

        from azure.identity import DefaultAzureCredential
        from azure.ai.projects import AIProjectClient

        self._project_client = AIProjectClient(
            endpoint=settings.foundry_project_endpoint,
            credential=DefaultAzureCredential(),
        )
        self._openai_client = self._project_client.get_openai_client()
        logger.info("Foundry AIProjectClient + OpenAI client created")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_matchup(
        self,
        home_team: str,
        away_team: str,
        sport: str,
        neutral: bool,
        predictions: List[Dict[str, Any]],
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
        home_last_played: str,
        away_last_played: str,
    ) -> str:
        """
        Call the Foundry agent to produce a matchup analysis.

        Args:
            home_team: Home team key
            away_team: Away team key
            sport: Sport code
            neutral: Whether the matchup is neutral-site
            predictions: List of prediction summary dicts
            home_stats: Curated stats for the home team
            away_stats: Curated stats for the away team
            home_last_played: Home team's last game date
            away_last_played: Away team's last game date

        Returns:
            The agent's analysis text.
        """
        self._ensure_client()

        settings = get_settings()
        agent_name = settings.foundry_agent_name

        prompt = self._build_prompt(
            home_team=home_team,
            away_team=away_team,
            sport=sport,
            neutral=neutral,
            predictions=predictions,
            home_stats=home_stats,
            away_stats=away_stats,
            home_last_played=home_last_played,
            away_last_played=away_last_played,
        )

        logger.info(
            f"Calling Foundry agent '{agent_name}' for {home_team} vs {away_team}"
        )

        # Create a conversation and get a response
        conversation = self._openai_client.conversations.create()
        response = self._openai_client.responses.create(
            conversation=conversation.id,
            extra_body={
                "agent_reference": {
                    "name": agent_name,
                    "type": "agent_reference",
                }
            },
            input=prompt,
        )

        analysis_text = response.output_text
        logger.info(
            f"Agent response received ({len(analysis_text)} chars) "
            f"for {home_team} vs {away_team}"
        )
        return analysis_text

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        home_team: str,
        away_team: str,
        sport: str,
        neutral: bool,
        predictions: List[Dict[str, Any]],
        home_stats: Dict[str, float],
        away_stats: Dict[str, float],
        home_last_played: str,
        away_last_played: str,
    ) -> str:
        """Build the structured prompt sent to the agent."""

        gender = "Men's" if sport == "ncaam_basketball" else "Women's"
        site_label = "neutral court" if neutral else f"{home_team} home court"

        # Format predictions table
        pred_lines = []
        for p in predictions:
            winner = (
                p["home_team"] if p["home_win_probability"] > 0.5 else p["away_team"]
            )
            prob = max(p["home_win_probability"], 1 - p["home_win_probability"])
            pred_lines.append(
                f"  Span {p['span']}: "
                f"{p['home_team']} vs {p['away_team']} — "
                f"{winner} wins ({prob:.1%}), "
                f"home_win_prob={p['home_win_probability']:.4f}"
            )

        # Stat labels for readability
        stat_labels = {
            "ortg": "Offensive Rating",
            "drtg": "Defensive Rating",
            "pace": "Pace",
            "efg_pct": "eFG%",
            "tov_pct": "Turnover %",
            "orb_pct": "Offensive Rebound %",
            "fta_rate": "FT Rate (FT/FGA)",
            "def_efg_pct": "Opp eFG%",
            "def_tov_pct": "Opp Turnover %",
            "def_orb_pct": "Opp Offensive Rebound %",
            "def_fta_rate": "Opp FT Rate",
            "fg_pct": "FG%",
            "three_pct": "3P%",
            "two_pct": "2P%",
            "ft_pct": "FT%",
            "ts_pct": "True Shooting %",
            "def_fg_pct": "Opp FG%",
            "def_three_pct": "Opp 3P%",
            "def_two_pct": "Opp 2P%",
            "def_ft_pct": "Opp FT%",
            "stl_pct": "Steal %",
            "blk_pct": "Block %",
            "three_pa_rate": "3PA Rate",
        }

        def format_stats(stats: Dict[str, float]) -> str:
            lines = []
            for key, val in stats.items():
                label = stat_labels.get(key, key)
                lines.append(f"    {label}: {val}")
            return "\n".join(lines)

        prompt = f"""NCAA {gender} Basketball Matchup Analysis

Matchup: {home_team} vs {away_team}
Site: {site_label}
{home_team} stats through: {home_last_played}
{away_team} stats through: {away_last_played}

ML Ensemble Model Predictions (across 3 moving-average windows):
{chr(10).join(pred_lines)}

{home_team} Advanced Stats (5-game SMA):
{format_stats(home_stats)}

{away_team} Advanced Stats (5-game SMA):
{format_stats(away_stats)}

Analyze this matchup for a bracket pick."""

        return prompt


def get_agent_service() -> AgentService:
    """Get the agent service singleton."""
    return AgentService()
