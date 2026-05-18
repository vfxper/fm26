"""
Football 11v11 Environment v3 - Full tactics, roles, stamina, fouls, passing.
GPU-optimized for RTX 4060 Ti. Numpy vectorized physics.

Features:
- 15 formations (random per episode)
- 7 mentality levels affecting positioning
- 4 pressing levels
- 4 defensive line heights
- Stamina affects speed, accuracy, decisions
- Fouls with yellow/red cards
- Passing, shooting, tackling, dribbling
- Role-based reward shaping
- Self-play ready
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import math
from football_ai.formations import (
    get_formation, get_formation_mirrored, get_random_formation,
    FORMATIONS, FIELD_W, FIELD_H, ROLE_NAMES_BY_FORMATION
)

# Physics
GOAL_W = 7.32
BALL_R = 0.11
PLAYER_R = 0.4
MAX_SPEED = 9.5
MAX_BALL_SPEED = 35.0
FRICTION = 0.25
PLAYER_ACCEL = 6.0
DT = 1.0 / 30
FPS = 30

# Match
STEPS_PER_MIN = FPS * 2
MATCH_STEPS = 90 * STEPS_PER_MIN

# Stamina
STAM_MAX = 100.0
STAM_SPRINT = 0.12
STAM_JOG = 0.02
STAM_WALK = -0.015  # Recovery
STAM_STAND = -0.025

# Stamina effects
STAM_SPEED_CURVE = lambda s: 0.6 + 0.4 * (s / STAM_MAX)  # 60-100% speed
STAM_ACCURACY_CURVE = lambda s: 0.5 + 0.5 * (s / STAM_MAX)  # 50-100% accuracy
STAM_DECISION_PENALTY = lambda s: max(0, (60 - s) / 60 * 0.3)  # 0-30% error when tired

# Fouls
TACKLE_RANGE = 1.8
FOUL_THRESHOLD = 0.65
YELLOW_THRESHOLD = 0.8
RED_THRESHOLD = 0.93

# Mentality offsets (how much formation shifts forward, in meters)
MENTALITY_OFFSET = {
    0: -15,  # Very Defensive
    1: -10,  # Defensive
    2: -5,   # Cautious
    3: 0,    # Balanced
    4: 5,    # Positive
    5: 10,   # Attacking
    6: 15,   # Very Attacking
}

# Pressing intensity (how far from ball players will chase)
PRESSING_RANGE = {
    0: 8,    # Low
    1: 15,   # Medium
    2: 25,   # High
    3: 45,   # Extreme
}

# Defensive line height offset from base formation
DEF_LINE_OFFSET = {
    0: -8,   # Low (deep)
    1: 0,    # Standard
    2: 8,    # High
    3: 18,   # Very High
}


class TeamTactics:
    """Tactical settings for one team."""
    def __init__(self):
        self.formation_name = "4-4-2"
        self.mentality = 3        # 0-6 (Very Def to Very Att)
        self.pressing = 1         # 0-3 (Low to Extreme)
        self.def_line = 1         # 0-3 (Low to Very High)
        self.width = 1            # 0=narrow, 1=standard, 2=wide
        self.tempo = 1            # 0=slow, 1=normal, 2=fast
        self.pass_style = 1       # 0=short, 1=mixed, 2=direct, 3=long ball

    def get_mentality_offset(self):
        return MENTALITY_OFFSET[self.mentality]

    def get_pressing_range(self):
        return PRESSING_RANGE[self.pressing]

    def get_def_line_offset(self):
        return DEF_LINE_OFFSET[self.def_line]

    def get_width_factor(self):
        return [0.7, 1.0, 1.3][self.width]

    def get_tempo_factor(self):
        return [0.6, 1.0, 1.5][self.tempo]

    def get_pass_range(self):
        """Max preferred pass distance."""
        return [15, 30, 40, 60][self.pass_style]


class Football11v11Env(gym.Env):
    """Full 11v11 with tactics, roles, stamina, fouls."""
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": FPS}

    def __init__(self, render_mode=None, team_side='home'):
        super().__init__()
        self.render_mode = render_mode
        self.team_side = team_side

        # Actions: 11 players * 5 = 55
        # [move_x, move_y, action_type, action_power, action_param]
        self.action_space = spaces.Box(-1, 1, shape=(55,), dtype=np.float32)

        # Obs: 22*6 + 4 + 3 + 7 = 146
        # Per player: x, y, vx, vy, stamina, has_ball = 6*22 = 132
        # Ball: x, y, vx, vy = 4
        # Score home, away, time = 3
        # Tactics encoding: mentality, pressing, def_line, width, tempo, pass_style, formation_id = 7
        self.observation_space = spaces.Box(-2, 2, shape=(146,), dtype=np.float32)

        # State
        self.pos = np.zeros((22, 2), dtype=np.float32)
        self.vel = np.zeros((22, 2), dtype=np.float32)
        self.stamina = np.full(22, STAM_MAX, dtype=np.float32)
        self.ball_pos = np.zeros(2, dtype=np.float32)
        self.ball_vel = np.zeros(2, dtype=np.float32)
        self.ball_owner = -1
        self.last_touch = -1

        self.home_score = 0
        self.away_score = 0
        self.step_count = 0

        self.yellows = np.zeros(22, dtype=np.int32)
        self.reds = np.zeros(22, dtype=np.int32)
        self.sent_off = np.zeros(22, dtype=np.bool_)
        self.foul_cooldown = 0

        # Tactics
        self.home_tactics = TeamTactics()
        self.away_tactics = TeamTactics()

        # Formations
        self.formation_home = None
        self.formation_away = None
        self.home_roles = None
        self.away_roles = None

        self.screen = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        rng = np.random.default_rng(seed)

        # Random formations
        hf = get_random_formation(rng)
        af = get_random_formation(rng)
        self.home_tactics.formation_name = hf
        self.away_tactics.formation_name = af

        # Random tactics for variety in training
        self.home_tactics.mentality = rng.integers(2, 5)  # Cautious to Positive
        self.home_tactics.pressing = rng.integers(1, 3)
        self.home_tactics.def_line = rng.integers(1, 3)
        self.away_tactics.mentality = rng.integers(2, 5)
        self.away_tactics.pressing = rng.integers(1, 3)
        self.away_tactics.def_line = rng.integers(1, 3)

        self.formation_home = get_formation(hf)
        self.formation_away = get_formation_mirrored(af)
        self.home_roles = ROLE_NAMES_BY_FORMATION.get(hf, ['GK']+['DEF']*4+['MID']*3+['ATT']*3)
        self.away_roles = ROLE_NAMES_BY_FORMATION.get(af, ['GK']+['DEF']*4+['MID']*3+['ATT']*3)

        # Apply mentality offset to formations
        h_offset = self.home_tactics.get_mentality_offset()
        a_offset = -self.away_tactics.get_mentality_offset()  # Mirrored
        
        self.pos[:11] = self.formation_home.copy()
        self.pos[:11, 0] += h_offset  # Shift forward/back
        self.pos[11:] = self.formation_away.copy()
        self.pos[11:, 0] += a_offset

        # Clamp to field
        self.pos[:, 0] = np.clip(self.pos[:, 0], 2, FIELD_W - 2)
        self.pos[:, 1] = np.clip(self.pos[:, 1], 2, FIELD_H - 2)

        self.vel[:] = 0
        self.stamina[:] = STAM_MAX
        self.ball_pos[:] = [FIELD_W/2, FIELD_H/2]
        self.ball_vel[:] = 0
        self.ball_owner = -1
        self.last_touch = -1
        self.home_score = 0
        self.away_score = 0
        self.step_count = 0
        self.yellows[:] = 0
        self.reds[:] = 0
        self.sent_off[:] = False
        self.foul_cooldown = 0

        return self._get_obs(), {}

    def step(self, action):
        self.step_count += 1
        reward = 0.0

        # Agent team
        if self.team_side == 'home':
            agent_range = range(0, 11)
            opp_range = range(11, 22)
            attack_dir = 1.0
            opp_goal_x = FIELD_W
            own_goal_x = 0.0
            tactics = self.home_tactics
        else:
            agent_range = range(11, 22)
            opp_range = range(0, 11)
            attack_dir = -1.0
            opp_goal_x = 0.0
            own_goal_x = FIELD_W
            tactics = self.away_tactics

        # Process agent actions
        for i, gi in enumerate(agent_range):
            if self.sent_off[gi]:
                continue
            act = action[i*5:(i+1)*5]
            reward += self._do_action(gi, act, attack_dir, opp_goal_x, tactics)

        # Opponent scripted AI
        self._opponent_ai(opp_range, opp_goal_x)

        # Physics
        self._physics()
        self._update_ball_owner()
        self._update_stamina()

        # Goals
        g = self._check_goal()
        if g == 'home':
            self.home_score += 1
            reward += 15.0 if self.team_side == 'home' else -8.0
            self._reset_positions()
        elif g == 'away':
            self.away_score += 1
            reward += 15.0 if self.team_side == 'away' else -8.0
            self._reset_positions()

        self._check_bounds()

        # Role rewards
        reward += self._role_rewards(agent_range, attack_dir, tactics)

        # Possession
        if self.ball_owner >= 0:
            is_ours = (self.team_side == 'home' and self.ball_owner < 11) or \
                      (self.team_side == 'away' and self.ball_owner >= 11)
            reward += 0.008 if is_ours else -0.003

        if self.foul_cooldown > 0:
            self.foul_cooldown -= 1

        done = self.step_count >= MATCH_STEPS
        info = {"home_score": self.home_score, "away_score": self.away_score,
                "minute": self.step_count // STEPS_PER_MIN}
        return self._get_obs(), reward, done, False, info


    def _do_action(self, gi, act, attack_dir, opp_goal_x, tactics):
        """Process one player's 5 actions with stamina effects and role compatibility."""
        move_x, move_y, atype, apower, aparam = act
        reward = 0.0

        # Stamina affects everything
        stam = self.stamina[gi]
        spd_mult = STAM_SPEED_CURVE(stam)
        acc_mult = STAM_ACCURACY_CURVE(stam)
        decision_err = STAM_DECISION_PENALTY(stam)

        # Role compatibility penalty (simulated: players out of position perform worse)
        # In training, we assume all players are "natural" for simplicity
        # The actual game will use role_compatibility.py for real evaluation
        role_penalty = 0.0  # 0 = no penalty in training

        # Movement with stamina-limited speed
        max_spd = MAX_SPEED * spd_mult * (1.0 - role_penalty)
        force = PLAYER_ACCEL * DT
        self.vel[gi, 0] += np.clip(move_x * max_spd - self.vel[gi, 0], -force*max_spd, force*max_spd)
        self.vel[gi, 1] += np.clip(move_y * max_spd - self.vel[gi, 1], -force*max_spd, force*max_spd)

        speed = np.linalg.norm(self.vel[gi])
        if speed > max_spd:
            self.vel[gi] *= max_spd / speed

        # Action
        power = (apower + 1) / 2  # 0-1
        if power < 0.25:
            return reward  # No action

        dist_ball = np.linalg.norm(self.pos[gi] - self.ball_pos)

        if atype > 0.33:
            # SHOOT or TACKLE
            if dist_ball < PLAYER_R + BALL_R + 0.6 and (self.ball_owner == gi or self.ball_owner == -1):
                reward += self._shoot(gi, power, aparam, opp_goal_x, acc_mult)
            elif dist_ball < TACKLE_RANGE and self.ball_owner >= 0 and self.ball_owner != gi:
                # Only tackle opponents
                same_team = (gi < 11 and self.ball_owner < 11) or (gi >= 11 and self.ball_owner >= 11)
                if not same_team:
                    reward += self._tackle(gi, power, acc_mult)
        elif atype > -0.33:
            # PASS
            if dist_ball < PLAYER_R + BALL_R + 0.6 and (self.ball_owner == gi or self.ball_owner == -1):
                reward += self._pass(gi, power, aparam, attack_dir, acc_mult, tactics)
        else:
            # DRIBBLE (keep ball, move forward)
            if self.ball_owner == gi:
                reward += 0.002  # Small reward for maintaining possession

        return reward

    def _shoot(self, gi, power, direction, goal_x, accuracy):
        """Shoot with stamina-affected accuracy."""
        goal_y = FIELD_H/2 + direction * GOAL_W * 0.45
        dx = goal_x - self.ball_pos[0]
        dy = goal_y - self.ball_pos[1]
        dist = max(0.1, np.sqrt(dx*dx + dy*dy))

        # Accuracy error from stamina
        error = (1 - accuracy) * 0.15
        angle = np.arctan2(dy, dx) + np.random.uniform(-error, error)

        shot_speed = (15 + power * 20) * accuracy  # Tired = weaker shot
        self.ball_vel[0] = np.cos(angle) * shot_speed
        self.ball_vel[1] = np.sin(angle) * shot_speed
        self.ball_owner = -1
        self.last_touch = gi

        # Reward based on position
        dist_to_goal = abs(goal_x - self.pos[gi, 0])
        if dist_to_goal < 20:
            return 1.0
        elif dist_to_goal < 30:
            return 0.4
        return 0.1

    def _pass(self, gi, power, direction, attack_dir, accuracy, tactics):
        """Pass with tactics-aware target selection."""
        team_start = 0 if gi < 11 else 11
        team_end = 11 if gi < 11 else 22
        max_pass_dist = tactics.get_pass_range()

        # Find best target
        best = -1
        best_score = -999
        for t in range(team_start, team_end):
            if t == gi or self.sent_off[t]:
                continue
            d = np.linalg.norm(self.pos[t] - self.pos[gi])
            if d < 3 or d > max_pass_dist:
                continue

            forward = (self.pos[t, 0] - self.pos[gi, 0]) * attack_dir
            score = forward * 0.4 + (25 - d) * 0.1
            # Tempo: fast tempo prefers forward passes more
            score += forward * tactics.get_tempo_factor() * 0.1
            if score > best_score:
                best_score = score
                best = t

        if best < 0:
            return 0.0

        dx = self.pos[best, 0] - self.ball_pos[0]
        dy = self.pos[best, 1] - self.ball_pos[1]
        dist = max(0.1, np.sqrt(dx*dx + dy*dy))

        # Pass speed (enough to reach with friction)
        pass_speed = min(25, 4 + dist * 0.6) * accuracy

        # Accuracy error
        error = (1 - accuracy) * 0.12 + STAM_DECISION_PENALTY(self.stamina[gi]) * 0.1
        angle = np.arctan2(dy, dx) + np.random.uniform(-error, error)

        self.ball_vel[0] = np.cos(angle) * pass_speed
        self.ball_vel[1] = np.sin(angle) * pass_speed
        self.ball_owner = -1
        self.last_touch = gi

        forward = (self.pos[best, 0] - self.pos[gi, 0]) * attack_dir > 0
        return 0.35 if forward else 0.1

    def _tackle(self, gi, power, accuracy):
        """Tackle with foul risk. Stamina affects timing."""
        if self.foul_cooldown > 0:
            return 0.0
        target = self.ball_owner
        if target < 0:
            return 0.0

        dist = np.linalg.norm(self.pos[gi] - self.pos[target])
        if dist > TACKLE_RANGE:
            return 0.0

        # Success chance (affected by stamina via accuracy)
        success = 0.35 + power * 0.25 * accuracy
        foul_chance = power * 0.45 * (1 + STAM_DECISION_PENALTY(self.stamina[gi]))

        if np.random.random() < success:
            self.ball_owner = gi
            self.last_touch = gi
            return 0.6
        elif np.random.random() < foul_chance:
            self.foul_cooldown = FPS * 3
            self.ball_vel[:] = 0
            if power > RED_THRESHOLD:
                self.reds[gi] += 1
                self.sent_off[gi] = True
                return -4.0
            elif power > YELLOW_THRESHOLD:
                self.yellows[gi] += 1
                if self.yellows[gi] >= 2:
                    self.sent_off[gi] = True
                    return -3.0
                return -1.5
            return -0.5
        return -0.1


    def _physics(self):
        """Vectorized physics update."""
        # Move players
        self.pos += self.vel * DT
        self.pos[:, 0] = np.clip(self.pos[:, 0], 0.5, FIELD_W - 0.5)
        self.pos[:, 1] = np.clip(self.pos[:, 1], 0.5, FIELD_H - 0.5)

        # Ball
        if self.ball_owner >= 0 and not self.sent_off[self.ball_owner]:
            o = self.ball_owner
            spd = np.linalg.norm(self.vel[o])
            if spd > 0.1:
                facing = self.vel[o] / spd
            else:
                facing = np.array([1.0, 0.0])
            self.ball_pos = self.pos[o] + facing * 0.7
            self.ball_vel[:] = self.vel[o]
        else:
            self.ball_pos += self.ball_vel * DT
            spd = np.linalg.norm(self.ball_vel)
            if spd > 0.1:
                decel = FRICTION * 9.81 * DT
                new_spd = max(0, spd - decel)
                self.ball_vel *= new_spd / spd
            else:
                self.ball_vel[:] = 0
            if spd > MAX_BALL_SPEED:
                self.ball_vel *= MAX_BALL_SPEED / spd

    def _update_ball_owner(self):
        if self.ball_owner >= 0:
            if self.sent_off[self.ball_owner]:
                self.ball_owner = -1
                return
            d = np.linalg.norm(self.pos[self.ball_owner] - self.ball_pos)
            if d > 1.5:
                self.ball_owner = -1
            return

        dists = np.linalg.norm(self.pos - self.ball_pos, axis=1)
        dists[self.sent_off] = 999
        closest = np.argmin(dists)
        if dists[closest] < PLAYER_R + BALL_R + 0.4:
            self.ball_owner = closest
            self.last_touch = closest

    def _update_stamina(self):
        speeds = np.linalg.norm(self.vel, axis=1)
        sprint_mask = speeds > MAX_SPEED * 0.7
        jog_mask = (speeds > MAX_SPEED * 0.25) & ~sprint_mask
        walk_mask = (speeds > 0.5) & ~sprint_mask & ~jog_mask
        stand_mask = ~sprint_mask & ~jog_mask & ~walk_mask

        self.stamina[sprint_mask] -= STAM_SPRINT
        self.stamina[jog_mask] -= STAM_JOG
        self.stamina[walk_mask] -= STAM_WALK  # Slight recovery
        self.stamina[stand_mask] -= STAM_STAND  # Recovery

        self.stamina = np.clip(self.stamina, 0, STAM_MAX)

    def _check_goal(self):
        bx, by = self.ball_pos
        gt = FIELD_H/2 - GOAL_W/2
        gb = FIELD_H/2 + GOAL_W/2
        if bx <= 0 and gt <= by <= gb:
            return 'away'
        if bx >= FIELD_W and gt <= by <= gb:
            return 'home'
        return None

    def _check_bounds(self):
        if self.ball_pos[0] < 0:
            self.ball_pos[0] = 1
            self.ball_vel[0] = abs(self.ball_vel[0]) * 0.2
        elif self.ball_pos[0] > FIELD_W:
            self.ball_pos[0] = FIELD_W - 1
            self.ball_vel[0] = -abs(self.ball_vel[0]) * 0.2
        if self.ball_pos[1] < 0:
            self.ball_pos[1] = 1
            self.ball_vel[1] = abs(self.ball_vel[1]) * 0.2
        elif self.ball_pos[1] > FIELD_H:
            self.ball_pos[1] = FIELD_H - 1
            self.ball_vel[1] = -abs(self.ball_vel[1]) * 0.2

    def _reset_positions(self):
        h_off = self.home_tactics.get_mentality_offset()
        a_off = -self.away_tactics.get_mentality_offset()
        self.pos[:11] = self.formation_home.copy()
        self.pos[:11, 0] += h_off
        self.pos[11:] = self.formation_away.copy()
        self.pos[11:, 0] += a_off
        self.pos[:, 0] = np.clip(self.pos[:, 0], 2, FIELD_W-2)
        self.pos[:, 1] = np.clip(self.pos[:, 1], 2, FIELD_H-2)
        self.vel[:] = 0
        self.ball_pos[:] = [FIELD_W/2, FIELD_H/2]
        self.ball_vel[:] = 0
        self.ball_owner = -1

    def _role_rewards(self, agent_range, attack_dir, tactics):
        """Role-based positional rewards with tactics influence."""
        reward = 0.0
        start = list(agent_range)[0]
        formation = self.formation_home if start == 0 else self.formation_away
        roles = self.home_roles if start == 0 else self.away_roles

        ment_offset = tactics.get_mentality_offset()
        def_offset = tactics.get_def_line_offset()
        press_range = tactics.get_pressing_range()

        for i, gi in enumerate(agent_range):
            if self.sent_off[gi]:
                continue

            role = roles[i] if i < len(roles) else 'MID'
            ideal = formation[i].copy()
            
            # Shift ideal by tactics
            if 'GK' not in role:
                ideal[0] += ment_offset
                if role in ['CB', 'LB', 'RB', 'LWB', 'RWB']:
                    ideal[0] += def_offset

            # Ball attraction (compact play)
            ideal[0] += (self.ball_pos[0] - ideal[0]) * 0.15
            ideal[1] += (self.ball_pos[1] - ideal[1]) * 0.1

            ideal[0] = np.clip(ideal[0], 2, FIELD_W-2)
            ideal[1] = np.clip(ideal[1], 2, FIELD_H-2)

            dist = np.linalg.norm(self.pos[gi] - ideal)

            # Positional reward
            if dist < 8:
                reward += 0.002
            elif dist > 20:
                reward -= 0.002

            # GK: must stay near goal
            if role == 'GK':
                own_gx = 0 if start == 0 else FIELD_W
                gk_dist = abs(self.pos[gi, 0] - own_gx)
                if gk_dist < 8:
                    reward += 0.003
                elif gk_dist > 15:
                    reward -= 0.005

            # Strikers: reward near opponent goal
            if role in ['ST', 'CF']:
                opp_gx = FIELD_W if start == 0 else 0
                st_dist = abs(self.pos[gi, 0] - opp_gx)
                if st_dist < 25:
                    reward += 0.003

            # Pressing reward: if opponent has ball and player is close
            if self.ball_owner >= 0:
                opp_has = (start == 0 and self.ball_owner >= 11) or (start == 11 and self.ball_owner < 11)
                if opp_has:
                    d_to_ball = np.linalg.norm(self.pos[gi] - self.ball_pos)
                    if d_to_ball < press_range and role not in ['GK']:
                        reward += 0.001  # Reward for pressing

            # Stamina management: penalize sprinting when very tired
            if self.stamina[gi] < 20 and np.linalg.norm(self.vel[gi]) > MAX_SPEED * 0.7:
                reward -= 0.003

        return reward

    def _opponent_ai(self, opp_range, opp_goal_x):
        """Scripted opponent with tactical awareness."""
        start = list(opp_range)[0]
        tactics = self.away_tactics if start == 11 else self.home_tactics
        formation = self.formation_away if start == 11 else self.formation_home
        roles = self.away_roles if start == 11 else self.home_roles
        ball = self.ball_pos
        press_range = tactics.get_pressing_range()

        for i, gi in enumerate(opp_range):
            if self.sent_off[gi]:
                continue

            role = roles[i] if i < len(roles) else 'MID'
            base = formation[i].copy()
            base[0] += tactics.get_mentality_offset() * (-1 if start == 11 else 1)

            # Target position
            target = base.copy()
            target[0] += (ball[0] - base[0]) * 0.2
            target[1] += (ball[1] - base[1]) * 0.15

            # Chase ball if close enough (pressing)
            d_ball = np.linalg.norm(self.pos[gi] - ball)
            if d_ball < press_range and role != 'GK':
                target = ball.copy()

            # GK stays near goal
            if role == 'GK':
                gx = FIELD_W if start == 11 else 0
                target = np.array([gx + (5 if start == 0 else -5), FIELD_H/2])
                target[1] += (ball[1] - FIELD_H/2) * 0.3

            # Move toward target
            diff = target - self.pos[gi]
            dist = np.linalg.norm(diff)
            if dist > 1:
                stam_spd = STAM_SPEED_CURVE(self.stamina[gi])
                spd = min(MAX_SPEED * 0.75 * stam_spd, dist * 2)
                self.vel[gi] = diff / dist * spd * 0.4
            else:
                self.vel[gi] *= 0.9

            # Kick if has ball
            if self.ball_owner == gi:
                dist_goal = abs(self.pos[gi, 0] - opp_goal_x)
                if dist_goal < 22 and np.random.random() < 0.03:
                    # Shoot
                    dx = opp_goal_x - self.ball_pos[0]
                    dy = FIELD_H/2 + np.random.uniform(-3, 3) - self.ball_pos[1]
                    d = max(0.1, np.sqrt(dx*dx+dy*dy))
                    self.ball_vel[:] = [dx/d*22, dy/d*22]
                    self.ball_owner = -1
                    self.last_touch = gi
                elif np.random.random() < 0.015:
                    # Pass
                    teammates = [t for t in opp_range if t != gi and not self.sent_off[t]]
                    if teammates:
                        tgt = teammates[np.random.randint(len(teammates))]
                        dx = self.pos[tgt, 0] - self.ball_pos[0]
                        dy = self.pos[tgt, 1] - self.ball_pos[1]
                        d = max(0.1, np.sqrt(dx*dx+dy*dy))
                        spd = min(20, 5 + d*0.5)
                        self.ball_vel[:] = [dx/d*spd, dy/d*spd]
                        self.ball_owner = -1
                        self.last_touch = gi


    def _get_obs(self):
        obs = np.zeros(146, dtype=np.float32)
        # 22 players: x, y, vx, vy, stamina, has_ball
        for i in range(22):
            obs[i*6] = self.pos[i, 0] / FIELD_W * 2 - 1
            obs[i*6+1] = self.pos[i, 1] / FIELD_H * 2 - 1
            obs[i*6+2] = np.clip(self.vel[i, 0] / MAX_SPEED, -1, 1)
            obs[i*6+3] = np.clip(self.vel[i, 1] / MAX_SPEED, -1, 1)
            obs[i*6+4] = self.stamina[i] / STAM_MAX
            obs[i*6+5] = 1.0 if self.ball_owner == i else 0.0
        # Ball
        obs[132] = self.ball_pos[0] / FIELD_W * 2 - 1
        obs[133] = self.ball_pos[1] / FIELD_H * 2 - 1
        obs[134] = np.clip(self.ball_vel[0] / MAX_BALL_SPEED, -1, 1)
        obs[135] = np.clip(self.ball_vel[1] / MAX_BALL_SPEED, -1, 1)
        # Score + time
        obs[136] = self.home_score / 5.0
        obs[137] = self.away_score / 5.0
        obs[138] = 1.0 - self.step_count / MATCH_STEPS
        # Tactics encoding (agent's tactics)
        t = self.home_tactics if self.team_side == 'home' else self.away_tactics
        obs[139] = t.mentality / 6.0
        obs[140] = t.pressing / 3.0
        obs[141] = t.def_line / 3.0
        obs[142] = t.width / 2.0
        obs[143] = t.tempo / 2.0
        obs[144] = t.pass_style / 3.0
        # Formation ID (normalized)
        all_forms = list(FORMATIONS.keys())
        fid = all_forms.index(t.formation_name) if t.formation_name in all_forms else 0
        obs[145] = fid / len(all_forms)
        return obs

    def render(self):
        if self.render_mode != "human":
            return
        try:
            import pygame
        except ImportError:
            import pygame_ce as pygame

        SCALE = 10
        W, H = int(FIELD_W*SCALE), int(FIELD_H*SCALE)

        if self.screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption("Football 11v11 - Tactics + Roles + Stamina")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont(None, 18)

        self.screen.fill((30, 130, 30))
        pygame.draw.rect(self.screen, (255,255,255), (0,0,W,H), 2)
        pygame.draw.line(self.screen, (255,255,255), (W//2,0), (W//2,H), 1)
        pygame.draw.circle(self.screen, (255,255,255), (W//2,H//2), int(9.15*SCALE), 1)
        gt = int((FIELD_H/2-GOAL_W/2)*SCALE)
        pygame.draw.rect(self.screen, (220,220,220), (0, gt, 4, int(GOAL_W*SCALE)), 0)
        pygame.draw.rect(self.screen, (220,220,220), (W-4, gt, 4, int(GOAL_W*SCALE)), 0)

        for i in range(22):
            if self.sent_off[i]:
                continue
            px, py = int(self.pos[i,0]*SCALE), int(self.pos[i,1]*SCALE)
            color = (60,120,255) if i < 11 else (255,60,60)
            r = int(PLAYER_R*SCALE*1.8)

            # Stamina tint
            s = self.stamina[i] / STAM_MAX
            if i < 11:
                color = (int(60*(1-s)), int(120*s+80), 255)
            else:
                color = (255, int(60*s+60), int(60*s))

            pygame.draw.circle(self.screen, color, (px,py), r)
            pygame.draw.circle(self.screen, (255,255,255), (px,py), r, 1)

            # Ball indicator
            if self.ball_owner == i:
                pygame.draw.circle(self.screen, (255,255,0), (px,py), r+2, 2)

            # Number
            n = self.font.render(str(i%11+1), True, (255,255,255))
            self.screen.blit(n, (px-4, py-5))

            # Stamina bar
            bw = 12
            pygame.draw.rect(self.screen, (40,40,40), (px-bw//2, py+r+1, bw, 3))
            pygame.draw.rect(self.screen, (0,int(255*s),0), (px-bw//2, py+r+1, int(bw*s), 3))

            # Yellow/Red card indicator
            if self.reds[i] > 0:
                pygame.draw.rect(self.screen, (255,0,0), (px+r, py-r, 4, 6))
            elif self.yellows[i] > 0:
                pygame.draw.rect(self.screen, (255,255,0), (px+r, py-r, 4, 6))

        # Ball
        bx, by = int(self.ball_pos[0]*SCALE), int(self.ball_pos[1]*SCALE)
        pygame.draw.circle(self.screen, (255,255,255), (bx,by), 5)
        pygame.draw.circle(self.screen, (0,0,0), (bx,by), 5, 1)

        # HUD
        minute = self.step_count // STEPS_PER_MIN
        hud = self.font.render(
            f"Blue {self.home_score}-{self.away_score} Red | {minute}' | "
            f"{self.home_tactics.formation_name} vs {self.away_tactics.formation_name}", 
            True, (255,255,255))
        self.screen.blit(hud, (10, 5))

        # Tactics info
        t = self.home_tactics
        ment_names = ['VDef','Def','Caut','Bal','Pos','Att','VAtt']
        tinfo = self.font.render(
            f"Ment:{ment_names[t.mentality]} Press:{t.pressing} Line:{t.def_line}",
            True, (200,200,255))
        self.screen.blit(tinfo, (10, 20))

        pygame.display.flip()
        self.clock.tick(FPS)

    def close(self):
        if self.screen:
            try:
                import pygame
            except ImportError:
                import pygame_ce as pygame
            pygame.quit()
            self.screen = None
