"""
AIMatchEngine — TODO skeleton for PPO-driven match simulation.

Loads the trained PPO model from ``football_ai/models_11v11_v2/best_model.zip`` and
runs ``Football11v11Env`` to produce a ``MatchResult`` compatible with the rest of
the FM26 backend (so the simulate endpoint and the frontend match UI keep working
without changes).

This file is intentionally a SKELETON. The training run is still in progress
(~92M / 1B steps), so we don't actually load the model yet. Once training
finishes, fill in the TODO sections below and add ``USE_AI_ENGINE = True`` to
``app/core/config.py`` to switch the calendar route over.

Design overview (planned):

1. ``__init__`` — load the model lazily on first use; cache as a class attribute
   so we don't re-load on every match (loading a PPO checkpoint is ~200-500 ms).
2. ``simulate_match`` — same signature as ``MatchEngine.simulate_match``:
     a. Pull top-11 players + attributes for both clubs from the DB.
     b. Pull tactics (formation, mentality, pressing, defensive line) from the
        squad/tactics route — fall back to "4-4-2" / Balanced / Medium / Standard
        when the user has not configured anything.
     c. Build a ``Football11v11Env`` instance with attribute-driven player
        speeds / accuracies (CA → speed scale, technique → pass accuracy, etc.).
     d. Run the episode for 90 in-game minutes (``MATCH_STEPS``) with the model's
        deterministic policy. Capture goals, shots, saves, cards as ``MatchEvent``
        objects so the frontend can render the same minute-by-minute timeline.
     e. Return a populated ``MatchResult``.
3. ``_extract_events_from_env`` — convert the env's per-step state changes into
   the ``MatchEvent`` list. Probably easier to add a small event-buffer hook to
   the env itself than to diff state every step.

Open questions for the user once training finishes:
- Should the same model play both teams (self-play), or load two checkpoints?
- How to surface "tactical fit" warnings (e.g. wrong formation for the squad) to
  the player — extra ``MatchEvent`` types, or a separate response field?
- Do we want per-player ratings (1-10) at the end of the match? The env already
  tracks per-agent rewards so this should be easy to expose.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.match_engine import MatchEngine, MatchResult


logger = logging.getLogger(__name__)


# ─── Configuration ────────────────────────────────────────────────────────────


MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "football_ai"
    / "models_11v11_v2"
    / "best_model.zip"
)


# ─── AIMatchEngine ────────────────────────────────────────────────────────────


class AIMatchEngine:
    """
    PPO-driven match simulator. Falls back to ``MatchEngine`` until the model is
    actually wired in (TODO).
    """

    _model = None  # cached PPO model, loaded on first use
    _env_class = None  # cached env class

    def __init__(self, session: AsyncSession):
        self.session = session
        self._fallback = MatchEngine(session)

    # ─── Public API (matches MatchEngine.simulate_match) ──────────────────────

    async def simulate_match(
        self,
        home_club_id: int,
        away_club_id: int,
        home_club_name: str,
        away_club_name: str,
    ) -> MatchResult:
        """
        Simulate a match using the trained PPO policy.

        Currently: delegates to the text-based ``MatchEngine``. Once the PPO run
        finishes, replace the fallback with the real env rollout.
        """
        if not self._is_model_available():
            logger.info(
                "AIMatchEngine: model not yet trained — falling back to MatchEngine"
            )
            return await self._fallback.simulate_match(
                home_club_id, away_club_id, home_club_name, away_club_name,
            )

        # TODO: real PPO rollout
        # 1. Lazy-load the model:
        #
        #     if AIMatchEngine._model is None:
        #         from stable_baselines3 import PPO
        #         AIMatchEngine._model = PPO.load(str(MODEL_PATH), device="cuda")
        #
        # 2. Build env from DB-driven players + tactics:
        #
        #     home_players = await self._fallback._get_top_players(home_club_id)
        #     away_players = await self._fallback._get_top_players(away_club_id)
        #     home_tactics = await self._load_tactics(home_club_id)
        #     away_tactics = await self._load_tactics(away_club_id)
        #     env = self._build_env(home_players, away_players,
        #                           home_tactics, away_tactics,
        #                           home_advantage=True)
        #
        # 3. Roll out one episode:
        #
        #     obs, _ = env.reset()
        #     done = False
        #     while not done:
        #         action, _ = AIMatchEngine._model.predict(obs, deterministic=True)
        #         obs, reward, terminated, truncated, info = env.step(action)
        #         done = terminated or truncated
        #
        # 4. Convert env state → MatchResult + MatchEvent[]:
        #
        #     return self._build_result(env, home_club_name, away_club_name)
        #
        # For now, fall back so the UI keeps working.
        return await self._fallback.simulate_match(
            home_club_id, away_club_id, home_club_name, away_club_name,
        )

    # ─── Helpers (TODO) ───────────────────────────────────────────────────────

    @staticmethod
    def _is_model_available() -> bool:
        """``True`` when the PPO checkpoint has been trained and saved."""
        return MODEL_PATH.exists()

    async def _load_tactics(self, club_id: int) -> Optional[dict]:
        """
        TODO: read tactics from ``careers.tactics_json`` (or a per-club tactics
        table when we add one) and return a dict shaped like ``TeamTactics``.
        Falls back to a balanced 4-4-2 when nothing configured.
        """
        return {
            "formation_name": "4-4-2",
            "mentality": 3,
            "pressing": 1,
            "def_line": 1,
            "width": 1,
            "tempo": 1,
            "pass_style": 1,
        }

    def _build_env(self, home_players, away_players, home_tactics, away_tactics, home_advantage: bool):
        """
        TODO: instantiate ``Football11v11Env`` and inject the player attributes
        + tactical settings. The env currently ignores per-player attributes,
        so this needs an env extension before it can be used.
        """
        raise NotImplementedError("AIMatchEngine env construction is not wired yet")

    def _build_result(self, env, home_club_name: str, away_club_name: str) -> MatchResult:
        """
        TODO: convert env episode state → ``MatchResult``.

        Plan:
        - Read goals from env.score (or per-team goal counters added during
          training).
        - Read possession ratio from env (needs a possession tracker that
          counts which team has the ball each step).
        - Read shot counts from a small event buffer in the env.
        - Build ``MatchEvent`` list from the same buffer.
        """
        raise NotImplementedError("AIMatchEngine result extraction is not wired yet")
