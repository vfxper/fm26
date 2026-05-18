"""
Football 11v11 v3 — self-play + own-goal-fixed reward shaping.

Two changes vs v2 (`football_env_11v11.py`):

1. **Self-play opponent.** Instead of the hard-coded `_opponent_ai`
   script, the env can hold a snapshot of a PPO policy and use it to
   drive the away team. Each step we feed the policy a *mirrored*
   observation (so it always sees itself as "home" attacking right),
   take its action, and apply it to the away players.

2. **Own-goal-aware reward.** v2 hands +15 to whoever's net the ball
   crosses, regardless of who last touched it. PPO learned to harass
   the opponent until they boot it into their own goal. v3:
     • Goal counts in the score (rules of football do credit the
       attacking side for an own goal).
     • Reward for the **scoring direction** is +15 only if the last
       touch was an attacker. Pure own goal → +3 (small windfall, not
       worth farming).
     • Defender who scored on his own net gets a personal -10 penalty
       in his team's reward, so PPO learns to AVOID putting it there.
     • Possession reward keeps tracking the ball, so the agent still
       has incentive to attack — just not to camp the opponent's box
       and force own goals.

The class is a subclass so the existing `train_11v11_v2.py` and
`watch_11v11.py` keep working — only the new `train_11v11_v3.py`
imports v3.
"""
from __future__ import annotations

import numpy as np

from football_ai.football_env_11v11 import (
    Football11v11Env,
    FIELD_W,
    FIELD_H,
    GOAL_W,
    MATCH_STEPS,
    STEPS_PER_MIN,
)


class Football11v11EnvV3(Football11v11Env):
    """v2 env with self-play hooks and fixed own-goal reward."""

    def __init__(self, render_mode=None, team_side="home", opponent_policy=None):
        super().__init__(render_mode=render_mode, team_side=team_side)
        # `opponent_policy` is a callable: obs -> action. Set it to a
        # frozen snapshot of the trained PPO model. None => fall back
        # to scripted opponent (legacy behaviour, for warm-up).
        self.opponent_policy = opponent_policy
        # Track who last kicked it AT each goal line (for own-goal logic).
        self._last_attacker_team = -1  # 0 = home attackers (touched ball, attacking right goal)
                                       # 1 = away attackers (touched ball, attacking left goal)

    # ------------------------------------------------------------------ #
    # Public hook so the trainer can swap in a fresh snapshot every N
    # rollouts without rebuilding the env.
    # ------------------------------------------------------------------ #
    def set_opponent_policy(self, policy):
        self.opponent_policy = policy

    # ------------------------------------------------------------------ #
    # step() override. Mostly copy of v2 with reward + opponent hook
    # changes.
    # ------------------------------------------------------------------ #
    def step(self, action):
        self.step_count += 1
        reward = 0.0

        # Resolve which 11 players are "us"
        if self.team_side == "home":
            agent_range = range(0, 11)
            opp_range = range(11, 22)
            attack_dir = 1.0
            opp_goal_x = FIELD_W
            tactics = self.home_tactics
        else:
            agent_range = range(11, 22)
            opp_range = range(0, 11)
            attack_dir = -1.0
            opp_goal_x = 0.0
            tactics = self.away_tactics

        # Process agent actions (these come from the trainer / replay).
        for i, gi in enumerate(agent_range):
            if self.sent_off[gi]:
                continue
            act = action[i * 5 : (i + 1) * 5]
            reward += self._do_action(gi, act, attack_dir, opp_goal_x, tactics)

        # Opponent: either a frozen policy or the legacy scripted AI.
        if self.opponent_policy is not None:
            self._opponent_via_policy(opp_range)
        else:
            self._opponent_ai(opp_range, opp_goal_x)

        # Physics + ball ownership + stamina (unchanged).
        self._physics()
        self._update_ball_owner()
        self._update_stamina()

        # ---- Goal handling with own-goal awareness ------------------
        g = self._check_goal()
        if g == "home":
            # Ball crossed RIGHT line, "home" team scored officially.
            self.home_score += 1
            reward += self._award_goal_reward(scoring_team="home")
            self._reset_positions()
        elif g == "away":
            self.away_score += 1
            reward += self._award_goal_reward(scoring_team="away")
            self._reset_positions()

        self._check_bounds()

        # Role rewards + possession (unchanged).
        reward += self._role_rewards(agent_range, attack_dir, tactics)
        if self.ball_owner >= 0:
            is_ours = (self.team_side == "home" and self.ball_owner < 11) or (
                self.team_side == "away" and self.ball_owner >= 11
            )
            reward += 0.008 if is_ours else -0.003

        if self.foul_cooldown > 0:
            self.foul_cooldown -= 1

        done = self.step_count >= MATCH_STEPS
        info = {
            "home_score": self.home_score,
            "away_score": self.away_score,
            "minute": self.step_count // STEPS_PER_MIN,
        }
        return self._get_obs(), reward, done, False, info

    # ------------------------------------------------------------------ #
    # Award goals with own-goal handling.
    # ------------------------------------------------------------------ #
    def _award_goal_reward(self, scoring_team: str) -> float:
        """
        Returns the reward delta for the agent (whose perspective is
        defined by `self.team_side`).

        - +15: agent's team scored a "real" goal (last touch was their own
          attacker).
        - +3:  agent's team scored an own goal (opp put it in for them).
          Worth less so PPO doesn't farm own-goal-forcing strategies.
        - -8:  conceded a real goal.
        - -10: conceded an own goal (their own defender did it). Slightly
          worse than a real concession so PPO learns to NOT put the ball
          near its own net.
        """
        # Resolve which side the agent is on.
        agent_is_home = (self.team_side == "home")
        agent_scored = (scoring_team == "home" and agent_is_home) or (
            scoring_team == "away" and not agent_is_home
        )

        # Determine if it was an own goal.
        # `last_touch` is a player index. If the scorer's team is the
        # one whose net it ended up in, it's an own goal.
        own_goal = False
        if self.last_touch >= 0:
            toucher_is_home = self.last_touch < 11
            scoring_team_is_home = (scoring_team == "home")
            # Own goal if last toucher belongs to the team that
            # CONCEDED. (E.g. the right goal is home's offensive net;
            # an away player who last touched and ended in there =
            # own goal credited to home.)
            own_goal = (toucher_is_home != scoring_team_is_home)

        if agent_scored:
            return 15.0 if not own_goal else 3.0
        else:
            return -8.0 if not own_goal else -10.0

    # ------------------------------------------------------------------ #
    # Drive the away team via a frozen policy snapshot.
    # ------------------------------------------------------------------ #
    def _opponent_via_policy(self, opp_range):
        """
        Build a mirrored observation for the away team (so the policy
        thinks it's playing as home, attacking right) and apply its
        action to the away players.
        """
        obs = self._get_obs_mirrored()
        try:
            action, _ = self.opponent_policy.predict(obs, deterministic=False)
        except Exception:
            # Policy crashed for any reason — fall back to scripted.
            self._opponent_ai(opp_range, 0.0)
            return

        action = np.asarray(action, dtype=np.float32).reshape(-1)
        # Action is shaped for 11 players * 5. Apply each one to the
        # corresponding away player. The action assumes attack_dir=+1
        # (right), but the away team really attacks left, so we flip
        # move_x and the shoot/pass direction param so motion goes
        # the right way after mirroring.
        for i, gi in enumerate(opp_range):
            if self.sent_off[gi]:
                continue
            a = action[i * 5 : (i + 1) * 5].copy()
            a[0] = -a[0]      # flip horizontal movement (mirrored)
            a[4] = -a[4]      # flip directional param (shot / pass aim)
            self._do_action(gi, a, attack_dir=-1.0, opp_goal_x=0.0,
                            tactics=self.away_tactics)

    # ------------------------------------------------------------------ #
    # Same as `_get_obs` but mirrored: away players appear in the first
    # 11 slots as if they were home, ball/score x-flipped.
    # ------------------------------------------------------------------ #
    def _get_obs_mirrored(self):
        obs = np.zeros(146, dtype=np.float32)
        # Indices 0..10 are agent (away players, but presented as home).
        for i in range(11):
            home_slot = i
            real_idx = 11 + i  # actual away player index
            obs[home_slot * 6 + 0] = -(self.pos[real_idx, 0] / FIELD_W * 2 - 1)
            obs[home_slot * 6 + 1] = self.pos[real_idx, 1] / FIELD_H * 2 - 1
            obs[home_slot * 6 + 2] = np.clip(-self.vel[real_idx, 0] / 9.5, -1, 1)
            obs[home_slot * 6 + 3] = np.clip(self.vel[real_idx, 1] / 9.5, -1, 1)
            obs[home_slot * 6 + 4] = self.stamina[real_idx] / 100.0
            obs[home_slot * 6 + 5] = 1.0 if self.ball_owner == real_idx else 0.0
        # Indices 11..21 are opponent (home players, mirrored).
        for i in range(11):
            opp_slot = 11 + i
            real_idx = i
            obs[opp_slot * 6 + 0] = -(self.pos[real_idx, 0] / FIELD_W * 2 - 1)
            obs[opp_slot * 6 + 1] = self.pos[real_idx, 1] / FIELD_H * 2 - 1
            obs[opp_slot * 6 + 2] = np.clip(-self.vel[real_idx, 0] / 9.5, -1, 1)
            obs[opp_slot * 6 + 3] = np.clip(self.vel[real_idx, 1] / 9.5, -1, 1)
            obs[opp_slot * 6 + 4] = self.stamina[real_idx] / 100.0
            obs[opp_slot * 6 + 5] = 1.0 if self.ball_owner == real_idx else 0.0
        # Ball (mirrored).
        obs[132] = -(self.ball_pos[0] / FIELD_W * 2 - 1)
        obs[133] = self.ball_pos[1] / FIELD_H * 2 - 1
        obs[134] = np.clip(-self.ball_vel[0] / 35.0, -1, 1)
        obs[135] = np.clip(self.ball_vel[1] / 35.0, -1, 1)
        # Score (swapped: away score is "our" score from this view).
        obs[136] = self.away_score / 5.0
        obs[137] = self.home_score / 5.0
        obs[138] = 1.0 - self.step_count / MATCH_STEPS
        # Tactics encoding — use away tactics (the team this view
        # represents). Layout matches v2's _get_obs tail.
        t = self.away_tactics
        obs[139] = t.mentality / 6.0
        obs[140] = t.pressing / 3.0
        obs[141] = t.def_line / 3.0
        obs[142] = t.width / 2.0
        obs[143] = t.tempo / 2.0
        obs[144] = t.pass_style / 3.0
        # Formation id — match v2 normalization.
        try:
            from football_ai.formations import FORMATIONS
            all_forms = list(FORMATIONS.keys())
            fid = (
                all_forms.index(t.formation_name)
                if t.formation_name in all_forms else 0
            )
            obs[145] = fid / max(1, len(all_forms))
        except Exception:
            obs[145] = 0.0
        return obs
