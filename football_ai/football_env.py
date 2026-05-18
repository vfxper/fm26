"""
Football Environment v2 - With roles, passing, stamina, self-play ready.

Roles:
  - Player 0: Defender (stays back, rewards for interceptions)
  - Player 1: Midfielder (links play, rewards for passes)
  - Player 2: Forward (attacks, rewards for shots/goals)

Actions per player: accel_x, accel_y, kick_power, kick_direction, pass_flag
Total: 3 players * 5 actions = 15 continuous actions

Self-play: red team can also be controlled by a model.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pymunk
import math

# Field dimensions (pixels, 10px = 1 meter)
FIELD_W = 1050
FIELD_H = 680
GOAL_W = 73
BALL_R = 8
PLAYER_R = 15
BALL_MASS = 0.43
PLAYER_MASS = 75
MAX_SPEED = 80
MAX_KICK = 5000
FPS = 60
MATCH_LEN = 90 * FPS  # 90 "minutes" (seconds)

# Role zones (x ranges as fraction of field)
DEFENDER_ZONE = (0.05, 0.45)
MIDFIELDER_ZONE = (0.2, 0.7)
FORWARD_ZONE = (0.4, 0.95)

# Stamina
STAMINA_MAX = 100.0
STAMINA_SPRINT_DRAIN = 0.03   # per step when sprinting
STAMINA_JOG_DRAIN = 0.005    # per step when jogging
STAMINA_RECOVERY = 0.01      # per step when slow/still
STAMINA_SPEED_PENALTY = 0.4  # max speed reduction at 0 stamina


class FootballEnv(gym.Env):
    """
    3v3 Football with roles, passing, stamina.
    Blue = agent team (left, attacks right).
    Red = opponent (scripted or self-play model).
    """
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": FPS}

    def __init__(self, render_mode=None, red_model=None):
        super().__init__()
        self.render_mode = render_mode
        self.red_model = red_model  # If None, scripted AI. If model, self-play.

        # Actions: 3 players * 5 = 15
        # Per player: [accel_x, accel_y, kick_power, kick_angle, pass_flag]
        # All in [-1, 1], interpreted:
        #   accel_x/y: direction of movement force
        #   kick_power: 0=no kick, 1=full power (mapped from [-1,1] to [0,1])
        #   kick_angle: direction of kick relative to goal (-1=left post, 0=center, 1=right post)
        #   pass_flag: >0 = attempt pass to nearest teammate, <=0 = shoot/dribble
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(15,), dtype=np.float32)

        # Observations: 43 values
        # Per player (6 players): x, y, vx, vy, stamina = 5 * 6 = 30
        # Ball: x, y, vx, vy = 4
        # Score: blue, red = 2
        # Time remaining = 1
        # Ball owner flag (who has it): 6 one-hot = 6
        # Total = 43
        self.observation_space = spaces.Box(low=-1.0, high=1.5, shape=(43,), dtype=np.float32)

        self.space = None
        self.blue_players = []
        self.red_players = []
        self.ball_body = None
        self.ball_shape = None
        self.blue_score = 0
        self.red_score = 0
        self.step_count = 0
        self.stamina = np.ones(6) * STAMINA_MAX  # [blue0, blue1, blue2, red0, red1, red2]
        self.ball_owner_idx = -1  # -1=nobody, 0-2=blue, 3-5=red
        self.last_touch_team = None
        self.screen = None
        self.clock = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.space = pymunk.Space()
        self.space.gravity = (0, 0)
        self.space.damping = 0.92

        self._create_walls()
        self.blue_players = []
        self.red_players = []

        # Blue: defender, midfielder, forward
        blue_pos = [
            (FIELD_W * 0.15, FIELD_H * 0.5),   # Defender (center back)
            (FIELD_W * 0.35, FIELD_H * 0.35),   # Midfielder
            (FIELD_W * 0.45, FIELD_H * 0.65),   # Forward
        ]
        for pos in blue_pos:
            self.blue_players.append(self._create_player(pos, 1))

        # Red: defender, midfielder, forward
        red_pos = [
            (FIELD_W * 0.85, FIELD_H * 0.5),
            (FIELD_W * 0.65, FIELD_H * 0.65),
            (FIELD_W * 0.55, FIELD_H * 0.35),
        ]
        for pos in red_pos:
            self.red_players.append(self._create_player(pos, 2))

        self.ball_body, self.ball_shape = self._create_ball()
        self.blue_score = 0
        self.red_score = 0
        self.step_count = 0
        self.stamina = np.ones(6) * STAMINA_MAX
        self.ball_owner_idx = -1
        self.last_touch_team = None

        return self._get_obs(), {}

    def step(self, action):
        self.step_count += 1
        reward = 0.0

        # --- BLUE TEAM (agent) ---
        for i in range(3):
            reward += self._process_player_action(i, action[i*5:(i+1)*5], is_blue=True)

        # --- RED TEAM ---
        if self.red_model is not None:
            # Self-play: get red actions from model
            red_obs = self._get_obs_red()
            red_action, _ = self.red_model.predict(red_obs, deterministic=False)
            for i in range(3):
                self._process_player_action(i, red_action[i*5:(i+1)*5], is_blue=False)
        else:
            self._scripted_red_ai()

        # Physics step
        self.space.step(1.0 / FPS)

        # Clamp ball
        bs = self.ball_body.velocity.length
        if bs > 350:
            self.ball_body.velocity = self.ball_body.velocity.normalized() * 350

        # Update ball ownership
        self._update_ball_owner()

        # Update stamina
        self._update_stamina()

        # Check goals
        goal = self._check_goals()
        if goal == 'blue':
            reward += 10.0
            self._reset_after_goal()
        elif goal == 'red':
            reward -= 5.0
            self._reset_after_goal()

        # Role-based rewards
        reward += self._role_rewards()

        # Possession
        if self.ball_owner_idx >= 0 and self.ball_owner_idx < 3:
            reward += 0.01
        elif self.ball_owner_idx >= 3:
            reward -= 0.005

        terminated = self.step_count >= MATCH_LEN
        return self._get_obs(), reward, terminated, False, {
            "blue_score": self.blue_score, "red_score": self.red_score
        }

    def _process_player_action(self, idx, act, is_blue=True):
        """Process 5 actions for one player. Returns immediate reward."""
        players = self.blue_players if is_blue else self.red_players
        body = players[idx][0]
        global_idx = idx if is_blue else idx + 3
        reward = 0.0

        ax, ay, kick_pow, kick_dir, pass_flag = act

        # Stamina affects max speed
        stam = self.stamina[global_idx]
        speed_mult = 1.0 - STAMINA_SPEED_PENALTY * (1.0 - stam / STAMINA_MAX)

        # Apply movement force
        force_mag = 600 * PLAYER_MASS
        body.apply_force_at_local_point((ax * force_mag, ay * force_mag))

        # Clamp speed
        max_spd = MAX_SPEED * speed_mult
        if body.velocity.length > max_spd:
            body.velocity = body.velocity.normalized() * max_spd

        # Kick/Pass logic
        kick_power = (kick_pow + 1) / 2  # Map to 0-1
        is_pass = pass_flag > 0

        if kick_power > 0.3:
            dist_to_ball = self._dist(body.position, self.ball_body.position)
            if dist_to_ball < PLAYER_R + BALL_R + 8:
                if is_pass:
                    # PASS: find nearest teammate and kick toward them
                    reward += self._execute_pass(idx, kick_power, is_blue)
                else:
                    # SHOOT: kick toward opponent goal
                    reward += self._execute_shot(body, kick_power, kick_dir, is_blue)

        return reward

    def _execute_pass(self, player_idx, power, is_blue):
        """Pass to nearest teammate."""
        players = self.blue_players if is_blue else self.red_players
        passer = players[player_idx][0]

        # Find nearest teammate
        best_dist = float('inf')
        best_target = None
        for i, (body, _) in enumerate(players):
            if i == player_idx:
                continue
            d = self._dist(passer.position, body.position)
            if d < best_dist:
                best_dist = d
                best_target = body

        if best_target is None:
            return 0.0

        # Direction to teammate
        dx = best_target.position.x - self.ball_body.position.x
        dy = best_target.position.y - self.ball_body.position.y
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1:
            return 0.0

        # Pass force (weaker than shot, more accurate)
        force = power * MAX_KICK * 0.6
        self.ball_body.apply_impulse_at_local_point((dx/length * force, dy/length * force))
        self.last_touch_team = 'blue' if is_blue else 'red'

        # Reward for passing (midfielder gets more)
        if is_blue:
            if player_idx == 1:  # Midfielder
                return 0.3
            return 0.15
        return 0.0

    def _execute_shot(self, body, power, direction, is_blue):
        """Shoot toward opponent goal."""
        # Goal position
        if is_blue:
            goal_x = FIELD_W
        else:
            goal_x = 0
        goal_y = FIELD_H / 2 + direction * GOAL_W * 0.4  # Aim within goal

        dx = goal_x - self.ball_body.position.x
        dy = goal_y - self.ball_body.position.y
        length = math.sqrt(dx*dx + dy*dy)
        if length < 1:
            return 0.0

        force = power * MAX_KICK
        self.ball_body.apply_impulse_at_local_point((dx/length * force, dy/length * force))
        self.last_touch_team = 'blue' if is_blue else 'red'

        # Reward for shooting (forward gets more)
        if is_blue:
            dist_to_goal = abs(FIELD_W - body.position.x)
            if dist_to_goal < FIELD_W * 0.4:  # In attacking third
                if 2 == self._get_role_idx_for_reward(body.position.x):  # Forward
                    return 0.5
                return 0.3
        return 0.0

    def _role_rewards(self):
        """Role-specific positional rewards."""
        reward = 0.0

        for i, (body, _) in enumerate(self.blue_players):
            x_frac = body.position.x / FIELD_W

            if i == 0:  # DEFENDER
                # Reward for staying in defensive zone
                if DEFENDER_ZONE[0] <= x_frac <= DEFENDER_ZONE[1]:
                    reward += 0.002
                else:
                    reward -= 0.005  # Penalty for being out of position
                # Reward for being between ball and own goal
                if self.ball_body.position.x > body.position.x:
                    reward += 0.001

            elif i == 1:  # MIDFIELDER
                # Reward for being in midfield zone
                if MIDFIELDER_ZONE[0] <= x_frac <= MIDFIELDER_ZONE[1]:
                    reward += 0.002
                # Reward for being near ball (link play)
                dist = self._dist(body.position, self.ball_body.position)
                if dist < 150:
                    reward += 0.001

            elif i == 2:  # FORWARD
                # Reward for being in attacking zone
                if FORWARD_ZONE[0] <= x_frac <= FORWARD_ZONE[1]:
                    reward += 0.002
                # Reward for being close to opponent goal
                dist_to_goal = abs(FIELD_W - body.position.x)
                if dist_to_goal < FIELD_W * 0.3:
                    reward += 0.002

        return reward

    def _get_role_idx_for_reward(self, x):
        """Determine role based on x position."""
        frac = x / FIELD_W
        if frac < 0.35:
            return 0  # Defender zone
        elif frac < 0.6:
            return 1  # Midfielder
        else:
            return 2  # Forward

    def _update_ball_owner(self):
        """Determine who is closest to ball (owns it)."""
        ball_pos = self.ball_body.position
        min_dist = float('inf')
        owner = -1

        all_players = self.blue_players + self.red_players
        for i, (body, _) in enumerate(all_players):
            d = self._dist(body.position, ball_pos)
            if d < PLAYER_R + BALL_R + 5 and d < min_dist:
                min_dist = d
                owner = i

        self.ball_owner_idx = owner

    def _update_stamina(self):
        """Update stamina based on movement speed."""
        all_players = self.blue_players + self.red_players
        for i, (body, _) in enumerate(all_players):
            speed = body.velocity.length
            if speed > MAX_SPEED * 0.7:
                self.stamina[i] -= STAMINA_SPRINT_DRAIN
            elif speed > MAX_SPEED * 0.3:
                self.stamina[i] -= STAMINA_JOG_DRAIN
            else:
                self.stamina[i] += STAMINA_RECOVERY

            self.stamina[i] = np.clip(self.stamina[i], 0, STAMINA_MAX)

    def _scripted_red_ai(self):
        """Improved scripted AI with roles."""
        ball_pos = self.ball_body.position

        for i, (body, _) in enumerate(self.red_players):
            if i == 0:
                # Red defender: stay back, only chase if ball is close
                target_x = FIELD_W * 0.8
                target_y = FIELD_H * 0.5
                if ball_pos.x > FIELD_W * 0.6:
                    target_x = ball_pos.x
                    target_y = ball_pos.y
            elif i == 1:
                # Red midfielder: chase ball
                target_x = ball_pos.x
                target_y = ball_pos.y
            else:
                # Red forward: push toward blue goal
                target_x = ball_pos.x - 50
                target_y = ball_pos.y

            dx = target_x - body.position.x
            dy = target_y - body.position.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 5:
                force = 400 * PLAYER_MASS
                body.apply_force_at_local_point((dx/dist * force, dy/dist * force))

            # Speed limit (slightly slower than blue)
            stam = self.stamina[i + 3]
            max_spd = MAX_SPEED * 0.75 * (1.0 - STAMINA_SPEED_PENALTY * (1.0 - stam / STAMINA_MAX))
            if body.velocity.length > max_spd:
                body.velocity = body.velocity.normalized() * max_spd

            # Kick if close to ball
            if self._dist(body.position, ball_pos) < PLAYER_R + BALL_R + 8:
                # Kick toward blue goal
                kdx = 0 - ball_pos.x
                kdy = FIELD_H / 2 - ball_pos.y
                klen = math.sqrt(kdx*kdx + kdy*kdy)
                if klen > 0:
                    self.ball_body.apply_impulse_at_local_point(
                        (kdx/klen * MAX_KICK * 0.5, kdy/klen * MAX_KICK * 0.5)
                    )
                    self.last_touch_team = 'red'


    def _get_obs(self):
        """Observation for blue team agent."""
        obs = []
        # Blue players: x, y, vx, vy, stamina
        for i, (body, _) in enumerate(self.blue_players):
            obs.append(body.position.x / FIELD_W * 2 - 1)
            obs.append(body.position.y / FIELD_H * 2 - 1)
            obs.append(np.clip(body.velocity.x / MAX_SPEED, -1, 1))
            obs.append(np.clip(body.velocity.y / MAX_SPEED, -1, 1))
            obs.append(self.stamina[i] / STAMINA_MAX)
        # Red players
        for i, (body, _) in enumerate(self.red_players):
            obs.append(body.position.x / FIELD_W * 2 - 1)
            obs.append(body.position.y / FIELD_H * 2 - 1)
            obs.append(np.clip(body.velocity.x / MAX_SPEED, -1, 1))
            obs.append(np.clip(body.velocity.y / MAX_SPEED, -1, 1))
            obs.append(self.stamina[i + 3] / STAMINA_MAX)
        # Ball
        obs.append(self.ball_body.position.x / FIELD_W * 2 - 1)
        obs.append(self.ball_body.position.y / FIELD_H * 2 - 1)
        obs.append(np.clip(self.ball_body.velocity.x / 300, -1, 1))
        obs.append(np.clip(self.ball_body.velocity.y / 300, -1, 1))
        # Score
        obs.append(np.clip(self.blue_score / 5, 0, 1))
        obs.append(np.clip(self.red_score / 5, 0, 1))
        # Time
        obs.append(1.0 - self.step_count / MATCH_LEN)
        # Ball owner one-hot (6 values)
        owner_hot = [0.0] * 6
        if 0 <= self.ball_owner_idx < 6:
            owner_hot[self.ball_owner_idx] = 1.0
        obs.extend(owner_hot)

        return np.array(obs, dtype=np.float32)

    def _get_obs_red(self):
        """Mirror observation for red team (self-play). Flip x-axis."""
        obs = []
        # Red players first (from their perspective they are "blue")
        for i, (body, _) in enumerate(self.red_players):
            obs.append((FIELD_W - body.position.x) / FIELD_W * 2 - 1)  # Flip X
            obs.append(body.position.y / FIELD_H * 2 - 1)
            obs.append(np.clip(-body.velocity.x / MAX_SPEED, -1, 1))  # Flip VX
            obs.append(np.clip(body.velocity.y / MAX_SPEED, -1, 1))
            obs.append(self.stamina[i + 3] / STAMINA_MAX)
        # Blue players (opponents from red's perspective)
        for i, (body, _) in enumerate(self.blue_players):
            obs.append((FIELD_W - body.position.x) / FIELD_W * 2 - 1)
            obs.append(body.position.y / FIELD_H * 2 - 1)
            obs.append(np.clip(-body.velocity.x / MAX_SPEED, -1, 1))
            obs.append(np.clip(body.velocity.y / MAX_SPEED, -1, 1))
            obs.append(self.stamina[i] / STAMINA_MAX)
        # Ball (flipped)
        obs.append((FIELD_W - self.ball_body.position.x) / FIELD_W * 2 - 1)
        obs.append(self.ball_body.position.y / FIELD_H * 2 - 1)
        obs.append(np.clip(-self.ball_body.velocity.x / 300, -1, 1))
        obs.append(np.clip(self.ball_body.velocity.y / 300, -1, 1))
        # Score (from red perspective)
        obs.append(np.clip(self.red_score / 5, 0, 1))
        obs.append(np.clip(self.blue_score / 5, 0, 1))
        obs.append(1.0 - self.step_count / MATCH_LEN)
        # Ball owner (remapped: red 0-2 become 0-2, blue 0-2 become 3-5)
        owner_hot = [0.0] * 6
        if self.ball_owner_idx >= 3:
            owner_hot[self.ball_owner_idx - 3] = 1.0
        elif self.ball_owner_idx >= 0:
            owner_hot[self.ball_owner_idx + 3] = 1.0
        obs.extend(owner_hot)

        return np.array(obs, dtype=np.float32)

    def _check_goals(self):
        bx = self.ball_body.position.x
        by = self.ball_body.position.y
        gt = FIELD_H / 2 - GOAL_W / 2
        gb = FIELD_H / 2 + GOAL_W / 2
        if bx <= 0 and gt <= by <= gb:
            self.red_score += 1
            return 'red'
        elif bx >= FIELD_W and gt <= by <= gb:
            self.blue_score += 1
            return 'blue'
        return None

    def _reset_after_goal(self):
        bp = [(FIELD_W*0.15, FIELD_H*0.5), (FIELD_W*0.35, FIELD_H*0.35), (FIELD_W*0.45, FIELD_H*0.65)]
        rp = [(FIELD_W*0.85, FIELD_H*0.5), (FIELD_W*0.65, FIELD_H*0.65), (FIELD_W*0.55, FIELD_H*0.35)]
        for i, (body, _) in enumerate(self.blue_players):
            body.position = bp[i]
            body.velocity = (0, 0)
        for i, (body, _) in enumerate(self.red_players):
            body.position = rp[i]
            body.velocity = (0, 0)
        self.ball_body.position = (FIELD_W / 2, FIELD_H / 2)
        self.ball_body.velocity = (0, 0)

    def _create_player(self, pos, ctype):
        body = pymunk.Body(PLAYER_MASS, pymunk.moment_for_circle(PLAYER_MASS, 0, PLAYER_R))
        body.position = pos
        shape = pymunk.Circle(body, PLAYER_R)
        shape.elasticity = 0.3
        shape.friction = 0.8
        shape.collision_type = ctype
        self.space.add(body, shape)
        return body, shape

    def _create_ball(self):
        body = pymunk.Body(BALL_MASS, pymunk.moment_for_circle(BALL_MASS, 0, BALL_R))
        body.position = (FIELD_W / 2, FIELD_H / 2)
        shape = pymunk.Circle(body, BALL_R)
        shape.elasticity = 0.7
        shape.friction = 0.5
        shape.collision_type = 3
        self.space.add(body, shape)
        return body, shape

    def _create_walls(self):
        walls = [
            [(0, 0), (FIELD_W, 0)],
            [(0, FIELD_H), (FIELD_W, FIELD_H)],
            [(0, 0), (0, FIELD_H/2 - GOAL_W/2)],
            [(0, FIELD_H/2 + GOAL_W/2), (0, FIELD_H)],
            [(FIELD_W, 0), (FIELD_W, FIELD_H/2 - GOAL_W/2)],
            [(FIELD_W, FIELD_H/2 + GOAL_W/2), (FIELD_W, FIELD_H)],
        ]
        for p1, p2 in walls:
            seg = pymunk.Segment(self.space.static_body, p1, p2, 3)
            seg.elasticity = 0.8
            seg.friction = 0.5
            self.space.add(seg)

    def _dist(self, p1, p2):
        return math.sqrt((p1.x-p2.x)**2 + (p1.y-p2.y)**2)

    def render(self):
        if self.render_mode != "human":
            return
        import pygame
        if self.screen is None:
            pygame.init()
            self.screen = pygame.display.set_mode((FIELD_W, FIELD_H))
            pygame.display.set_caption("Football AI v2 - Roles + Stamina + Pass")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont(None, 28)

        self.screen.fill((34, 139, 34))
        # Markings
        pygame.draw.rect(self.screen, (255,255,255), (0,0,FIELD_W,FIELD_H), 3)
        pygame.draw.line(self.screen, (255,255,255), (FIELD_W//2,0), (FIELD_W//2,FIELD_H), 2)
        pygame.draw.circle(self.screen, (255,255,255), (FIELD_W//2,FIELD_H//2), 60, 2)
        gt = int(FIELD_H/2 - GOAL_W/2)
        pygame.draw.rect(self.screen, (255,255,255), (0, gt, 5, GOAL_W), 3)
        pygame.draw.rect(self.screen, (255,255,255), (FIELD_W-5, gt, 5, GOAL_W), 3)

        # Role labels
        role_labels = ['DEF', 'MID', 'FWD']

        # Blue
        for i, (body, _) in enumerate(self.blue_players):
            pos = (int(body.position.x), int(body.position.y))
            # Stamina color: green=full, red=empty
            stam_ratio = self.stamina[i] / STAMINA_MAX
            color = (int(50*(1-stam_ratio)), int(100*stam_ratio + 100), 255)
            pygame.draw.circle(self.screen, color, pos, PLAYER_R)
            pygame.draw.circle(self.screen, (255,255,255), pos, PLAYER_R, 2)
            # Role label
            lbl = self.font.render(role_labels[i], True, (255,255,255))
            self.screen.blit(lbl, (pos[0]-12, pos[1]-25))
            # Stamina bar
            bar_w = 24
            pygame.draw.rect(self.screen, (60,60,60), (pos[0]-bar_w//2, pos[1]+PLAYER_R+2, bar_w, 4))
            pygame.draw.rect(self.screen, (0,255,0), (pos[0]-bar_w//2, pos[1]+PLAYER_R+2, int(bar_w*stam_ratio), 4))

        # Red
        for i, (body, _) in enumerate(self.red_players):
            pos = (int(body.position.x), int(body.position.y))
            stam_ratio = self.stamina[i+3] / STAMINA_MAX
            color = (255, int(60*stam_ratio + 60), int(60*stam_ratio))
            pygame.draw.circle(self.screen, color, pos, PLAYER_R)
            pygame.draw.circle(self.screen, (255,255,255), pos, PLAYER_R, 2)
            lbl = self.font.render(role_labels[i], True, (255,255,255))
            self.screen.blit(lbl, (pos[0]-12, pos[1]-25))
            bar_w = 24
            pygame.draw.rect(self.screen, (60,60,60), (pos[0]-bar_w//2, pos[1]+PLAYER_R+2, bar_w, 4))
            pygame.draw.rect(self.screen, (0,255,0), (pos[0]-bar_w//2, pos[1]+PLAYER_R+2, int(bar_w*stam_ratio), 4))

        # Ball
        bp = (int(self.ball_body.position.x), int(self.ball_body.position.y))
        pygame.draw.circle(self.screen, (255,255,255), bp, BALL_R)
        pygame.draw.circle(self.screen, (0,0,0), bp, BALL_R, 1)

        # HUD
        score_txt = self.font.render(f"Blue {self.blue_score} - {self.red_score} Red", True, (255,255,255))
        self.screen.blit(score_txt, (FIELD_W//2 - 70, 10))
        time_txt = self.font.render(f"{self.step_count // FPS}'", True, (200,255,200))
        self.screen.blit(time_txt, (FIELD_W//2 - 10, 35))

        pygame.display.flip()
        self.clock.tick(FPS)

    def close(self):
        if self.screen:
            import pygame
            pygame.quit()
            self.screen = None
