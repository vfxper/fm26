"""
Football 11v11 v4 — v3 + dense ball-distance shaping.

Why v4:
The 111M-step v3 run produced a degenerate equilibrium where both
sides "circled the ball without touching it". The eval reward bounced
between 50 and 89, and `std=2.09` after 111M steps means the policy
never collapsed onto a confident strategy.

The most likely culprit (other than self-play instability and a too-
large clip_range) is the absence of dense feedback for *moving toward
the ball*. A team without the ball gets `-0.003` per step (possession
penalty) but no signal for closing distance, so wandering near the
sidelines is locally as good as approaching it.

This env adds:
1. **Approach reward**: every step, the closest agent player to the
   ball gets a small positive reward proportional to `1 - d/D_max`,
   where `D_max ≈ pitch diagonal`. Tiny per-step (so it can't override
   goals) but accumulates if the team consistently closes in.
2. **Inactivity penalty**: if NEITHER side has owned the ball for the
   last `INACTIVITY_WINDOW` steps, every agent player gets a small
   negative reward. This breaks Nash stand-offs without changing the
   shape of the optimum (any policy that touches the ball at all
   beats the inactive baseline).
3. **First-touch bonus**: when an agent player becomes ball_owner
   after a period of no-owner, +0.05 once. Cheap reward for
   "the first one to actually touch it".

All shaping rewards are capped to small magnitudes (<0.05/step) so
the +15 goal reward still dominates. They only fix the credit-
assignment hole that produced the circling equilibrium.
"""
from __future__ import annotations

import numpy as np

from football_ai.football_env_11v11 import (
    FIELD_W,
    FIELD_H,
    MATCH_STEPS,
    STEPS_PER_MIN,
)
from football_ai.football_env_11v11_v3 import Football11v11EnvV3


# Pitch diagonal (≈125m on a 105×68 field). Used to normalise the
# distance-to-ball shaping reward into [0, 1].
_PITCH_DIAG = float(np.sqrt(FIELD_W * FIELD_W + FIELD_H * FIELD_H))

# Per-step shaping reward awarded to the closest agent player when
# their team does NOT own the ball. Tiny so that 90 minutes of perfect
# approach rewards ~ 90*60*30 * 0.0008 ≈ 130, comparable to a few goals
# but never enough to outweigh actually scoring.
_APPROACH_BONUS_MAX = 0.0008

# How many consecutive steps with no ball owner before we start
# penalising inactivity. 30 steps ≈ 1 second at 30 FPS.
INACTIVITY_WINDOW = 60  # ~2 seconds without anyone touching the ball

# Per-step penalty applied to the agent's reward once we cross the
# inactivity window. Stays small (< approach bonus * 11) so it isn't
# punitive when the ball is in the air for a single pass.
_INACTIVITY_PENALTY = 0.0015

# One-shot reward when an agent player becomes ball_owner after the
# ball was loose for at least `INACTIVITY_WINDOW//2` steps.
_FIRST_TOUCH_BONUS = 0.05


class Football11v11EnvV4(Football11v11EnvV3):
    """v3 + ball-approach shaping + inactivity penalty + first-touch bonus."""

    def __init__(self, render_mode=None, team_side="home", opponent_policy=None):
        super().__init__(
            render_mode=render_mode,
            team_side=team_side,
            opponent_policy=opponent_policy,
        )
        # Steps since the last time anyone owned the ball. Drives the
        # inactivity penalty and the first-touch bonus.
        self._loose_ball_steps = 0
        # Snapshot of `ball_owner` at the start of the previous step,
        # used to detect a "loose -> owned" transition for the first-
        # touch bonus.
        self._prev_owner = -1

    # ------------------------------------------------------------------ #
    # Reset bookkeeping when the env resets.
    # ------------------------------------------------------------------ #
    def reset(self, seed=None, options=None):
        self._loose_ball_steps = 0
        self._prev_owner = -1
        return super().reset(seed=seed, options=options)

    # ------------------------------------------------------------------ #
    # Add shaping rewards on top of v3's step.
    # ------------------------------------------------------------------ #
    def step(self, action):
        # Snapshot the owner BEFORE the v3 step runs so we can detect
        # the loose -> owned transition correctly afterwards.
        self._prev_owner = self.ball_owner
        was_loose_for = self._loose_ball_steps

        obs, reward, done, truncated, info = super().step(action)

        # 1. Approach shaping. Find the closest agent-team player to
        # the ball and award a tiny bonus proportional to how close
        # they are. This fixes the credit-assignment hole that lets
        # players ignore the ball.
        agent_range = (
            range(0, 11) if self.team_side == "home" else range(11, 22)
        )
        team_is_home = self.team_side == "home"
        own_team_owns = (self.ball_owner >= 0) and (
            (team_is_home and self.ball_owner < 11)
            or (not team_is_home and self.ball_owner >= 11)
        )

        # Distance from each agent player to the ball.
        own_pos = self.pos[list(agent_range)]
        d_to_ball = np.linalg.norm(own_pos - self.ball_pos, axis=1)
        # Skip sent-off players when picking the closest.
        sent_off_mask = self.sent_off[list(agent_range)]
        d_to_ball = np.where(sent_off_mask, _PITCH_DIAG, d_to_ball)
        closest_d = float(d_to_ball.min())
        approach_norm = max(0.0, 1.0 - closest_d / _PITCH_DIAG)

        # Only reward closing in when WE do not already own it. When we
        # own the ball, we want the rest of the team to spread out, not
        # all run at the carrier — so the bonus is gated on "not ours".
        if not own_team_owns:
            reward += _APPROACH_BONUS_MAX * approach_norm

        # 2. Inactivity penalty. If nobody has owned the ball in the
        # last `INACTIVITY_WINDOW` steps, charge the agent a small
        # cost. This breaks the Nash equilibrium where both teams
        # benefit from doing nothing.
        if self.ball_owner < 0:
            self._loose_ball_steps += 1
        else:
            self._loose_ball_steps = 0
        if self._loose_ball_steps > INACTIVITY_WINDOW:
            reward -= _INACTIVITY_PENALTY

        # 3. First-touch bonus. If the ball was loose for at least
        # half the inactivity window and now an agent-team player owns
        # it, give a one-shot bonus. Encourages "be the one who picks
        # it up" without rewarding every routine touch.
        if (
            self._prev_owner < 0
            and self.ball_owner >= 0
            and was_loose_for >= INACTIVITY_WINDOW // 2
        ):
            new_owner_is_us = (
                (team_is_home and self.ball_owner < 11)
                or (not team_is_home and self.ball_owner >= 11)
            )
            if new_owner_is_us:
                reward += _FIRST_TOUCH_BONUS

        return obs, reward, done, truncated, info
