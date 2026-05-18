"""
Train Football 11v11 v3 — curriculum + self-play + own-goal-fixed reward.

What's new vs v2:
- Env is `Football11v11EnvV3` (own-goal aware reward, opponent_policy hook).
- Curriculum (vs old version): first SELF_PLAY_START_STEP env-steps the
  agent plays vs the legacy SCRIPTED opponent (no snapshot is published).
  Only after that the snapshot publisher kicks in and the opponent
  becomes a frozen copy of the current policy, refreshed every 500k
  steps. Subproc envs reload it lazily on reset.
- Default total steps bumped to 1B (200M was a guess and the policy
  was clearly not converged).

Usage:
    python football_ai/train_11v11_v3.py
    python football_ai/train_11v11_v3.py --steps 1_000_000_000
    python football_ai/train_11v11_v3.py --resume                      # warm-start from v2 checkpoint
    python football_ai/train_11v11_v3.py --warmstart-from football_ai/models_11v11_v2/best_model.zip

Estimated time on RTX 4060 Ti: ~12-18h per 100M steps (slightly slower
than v2 because each step also runs the opponent policy forward pass).
"""
from __future__ import annotations

import os
import sys
import argparse
import time
import shutil

import torch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.callbacks import (
    CheckpointCallback,
    EvalCallback,
    BaseCallback,
)
from stable_baselines3.common.monitor import Monitor

from football_ai.football_env_11v11_v3 import Football11v11EnvV3


# ----------------------------------------------------------------------#
# Paths
# ----------------------------------------------------------------------#
HERE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(HERE, "models_11v11_v3")
LOG_DIR = os.path.join(HERE, "logs_11v11_v3")
SNAPSHOT_FILE = os.path.join(MODEL_DIR, "opponent_snapshot.zip")
SNAPSHOT_FLAG = os.path.join(MODEL_DIR, "opponent_snapshot.version")

# Curriculum: first N env-steps train against the scripted bot
# (own-goal-fixed reward already applies). After that, the snapshot
# publisher writes the opponent file and self-play kicks in.
SELF_PLAY_START_STEP = 50_000_000


# ----------------------------------------------------------------------#
# Self-play env wrapper
# ----------------------------------------------------------------------#
class SelfPlayEnv(Football11v11EnvV3):
    """
    On every reset, check if the opponent snapshot file changed; if
    yes, reload it. The opponent policy then drives the away team via
    `_opponent_via_policy` inherited from v3.

    Until the snapshot file exists, fall back to the scripted opponent
    (same behaviour as v2). This gives the agent a warm-up period.
    """

    def __init__(self, render_mode=None, team_side="home"):
        super().__init__(render_mode=render_mode, team_side=team_side,
                         opponent_policy=None)
        self._snapshot_version_seen = -1

    def _maybe_reload_opponent(self):
        if not os.path.exists(SNAPSHOT_FLAG):
            return
        try:
            with open(SNAPSHOT_FLAG, "r") as f:
                v = int(f.read().strip() or "0")
        except Exception:
            return
        if v == self._snapshot_version_seen:
            return
        # Try to load — file might be mid-write, wrap in try/except.
        try:
            policy = PPO.load(SNAPSHOT_FILE, device="cpu")
            self.set_opponent_policy(policy)
            self._snapshot_version_seen = v
        except Exception:
            # Stay on whatever we had.
            pass

    def reset(self, seed=None, options=None):
        self._maybe_reload_opponent()
        return super().reset(seed=seed, options=options)


def make_env(rank):
    def _init():
        env = SelfPlayEnv(render_mode=None, team_side="home")
        return Monitor(env)

    return _init


# ----------------------------------------------------------------------#
# Callbacks
# ----------------------------------------------------------------------#
class SnapshotPublisherCallback(BaseCallback):
    """
    Every `freq` env-steps, dump the current model to
    SNAPSHOT_FILE so subproc envs can pick it up as the new opponent.
    """

    def __init__(self, freq=500_000, verbose=0):
        super().__init__(verbose)
        self.freq = freq
        self._last = 0

    def _on_step(self):
        # Curriculum gate: do NOT publish any opponent snapshot until
        # the agent has had time to learn a baseline policy against
        # the scripted bot. Until then, every env keeps using the
        # scripted opponent (because no snapshot file exists).
        if self.num_timesteps < SELF_PLAY_START_STEP:
            if self.verbose and self.num_timesteps - self._last >= self.freq:
                self._last = self.num_timesteps
                remaining = SELF_PLAY_START_STEP - self.num_timesteps
                print(
                    f"  [curriculum] vs scripted bot, "
                    f"{self.num_timesteps:,}/{SELF_PLAY_START_STEP:,} "
                    f"({remaining:,} steps until self-play)"
                )
            return True
        if self.num_timesteps - self._last < self.freq:
            return True
        self._last = self.num_timesteps
        try:
            tmp = SNAPSHOT_FILE + ".tmp"
            self.model.save(tmp)
            # atomic-ish replace
            shutil.move(tmp, SNAPSHOT_FILE)
            with open(SNAPSHOT_FLAG, "w") as f:
                f.write(str(self.num_timesteps))
            if self.verbose:
                print(f"  [self-play] published snapshot @ {self.num_timesteps:,} steps")
        except Exception as e:
            if self.verbose:
                print(f"  [self-play] snapshot publish failed: {e}")
        return True


class LogCallback(BaseCallback):
    def __init__(self, log_freq=100_000):
        super().__init__()
        self.log_freq = log_freq

    def _on_step(self):
        if self.num_timesteps % self.log_freq == 0:
            infos = self.locals.get("infos", [])
            scores = [
                (i.get("home_score", 0), i.get("away_score", 0))
                for i in infos
                if "home_score" in i
            ]
            if scores:
                ah = sum(s[0] for s in scores) / len(scores)
                aa = sum(s[1] for s in scores) / len(scores)
                print(
                    f"  Step {self.num_timesteps:>10,} | "
                    f"Avg Score: {ah:.2f}-{aa:.2f}"
                )
        return True


def linear_schedule(initial_value):
    def func(progress_remaining):
        return progress_remaining * initial_value

    return func


# ----------------------------------------------------------------------#
# Train
# ----------------------------------------------------------------------#
def train(total_steps=1_000_000_000, resume=False, warmstart_from=None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        print("  WARNING: training on CPU will be slow.")

    print(
        f"""
{'='*60}
  FOOTBALL 11v11 AI — V3 TRAINING (curriculum + self-play)
{'='*60}
  Device: {device}
  Steps: {total_steps:,}
  Self-play starts at: {SELF_PLAY_START_STEP:,}

  Curriculum:
   • Steps 0..{SELF_PLAY_START_STEP:,}: vs SCRIPTED opponent
     (own-goal-fixed reward; lets the policy learn a baseline).
   • Steps {SELF_PLAY_START_STEP:,}..{total_steps:,}: SELF-PLAY
     (opponent = frozen snapshot of THIS policy, refreshed every
     500k steps).

  Reward fixes (vs v2):
   • Own goals give +3 (not +15) to the receiving side.
   • Defenders putting it in their own net cost their team -10.
{'='*60}
"""
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # Wipe any stale snapshot so the FIRST 500k steps train against the
    # scripted opponent (warm-up). After that the publisher will create
    # the snapshot file and self-play kicks in.
    for path in (SNAPSHOT_FILE, SNAPSHOT_FLAG):
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    num_envs = 12
    print(f"  Creating {num_envs} parallel environments...")
    try:
        env = SubprocVecEnv([make_env(i) for i in range(num_envs)])
    except Exception:
        print("  SubprocVecEnv failed, using DummyVecEnv...")
        env = DummyVecEnv([make_env(i) for i in range(num_envs)])

    eval_env = DummyVecEnv([make_env(99)])

    # Callbacks
    checkpoint_cb = CheckpointCallback(
        save_freq=500_000 // num_envs,
        save_path=MODEL_DIR,
        name_prefix="football_v3",
    )
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=MODEL_DIR,
        log_path=LOG_DIR,
        eval_freq=200_000 // num_envs,
        n_eval_episodes=5,
        deterministic=True,
    )
    log_cb = LogCallback(log_freq=100_000)
    snapshot_cb = SnapshotPublisherCallback(freq=500_000, verbose=1)

    # Choose where to start from
    latest_ckpt = os.path.join(MODEL_DIR, "football_v3_latest.zip")
    if resume and os.path.exists(latest_ckpt):
        print(f"  Resuming from: {latest_ckpt}")
        model = PPO.load(latest_ckpt, env=env, device=device)
    elif warmstart_from and os.path.exists(warmstart_from):
        # Warm-start from a v2 checkpoint. PPO.load + env replacement.
        print(f"  Warm-starting from: {warmstart_from}")
        model = PPO.load(warmstart_from, env=env, device=device)
    else:
        print("  Creating new PPO model (v3)...")
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            device=device,
            learning_rate=linear_schedule(3e-5),
            n_steps=2048,
            batch_size=256,
            n_epochs=5,
            gamma=0.995,
            gae_lambda=0.95,
            clip_range=0.1,
            clip_range_vf=0.1,
            ent_coef=0.001,
            vf_coef=0.5,
            max_grad_norm=0.5,
            target_kl=0.015,
            tensorboard_log=None,
            policy_kwargs=dict(
                net_arch=dict(
                    pi=[512, 256, 128],
                    vf=[512, 256, 128],
                ),
                activation_fn=torch.nn.Tanh,
                log_std_init=-1.0,
            ),
        )

    print(f"\n  Training for {total_steps:,} steps...")
    print(f"  Self-play snapshot every 500k steps to {SNAPSHOT_FILE}")
    print(f"  Press Ctrl+C to stop (auto-saves).\n")

    try:
        model.learn(
            total_timesteps=total_steps,
            callback=[checkpoint_cb, eval_cb, log_cb, snapshot_cb],
            progress_bar=False,
        )
    except KeyboardInterrupt:
        print("\n\n  Training interrupted! Saving...")

    model.save(latest_ckpt)
    model.save(os.path.join(MODEL_DIR, f"football_v3_{total_steps // 1_000_000}M"))
    print(f"\n  Model saved to: {MODEL_DIR}/")

    env.close()
    eval_env.close()
    print("  Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--steps", type=int, default=1_000_000_000,
        help="Total training steps (default 1B).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from football_v3_latest.zip if present.",
    )
    parser.add_argument(
        "--warmstart-from", type=str, default=None,
        help="Path to a v2 checkpoint to initialise weights from.",
    )
    args = parser.parse_args()
    train(args.steps, args.resume, args.warmstart_from)
