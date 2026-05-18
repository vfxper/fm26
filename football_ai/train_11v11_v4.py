"""
Train Football 11v11 v4 — fine-tune from v3 snapshot with the four
fixes for the "circle the ball, never touch it" failure mode.

Diagnosis of the v3 run (111M steps, eval reward 50-89, std=2.09):
1. Both teams converged to a Nash stand-off. Without dense reward
   for approaching the ball, doing nothing is locally as good as
   trying to play.
2. clip_range=0.1 was too permissive in late-stage fine-tuning. PPO
   kept making large policy updates that flipped strategies between
   evals, hence the 89 → 50 → 89 oscillation.
3. The opponent pool was just "frozen self". Self-play without weak
   opponents removes the gradient signal — both sides reach the
   stand-off and stay there.
4. Learning rate 2.67e-05 is fine for fresh training but too high
   when the policy is already mostly correct and we want fine
   adjustments only.

The four v4 fixes:
1. **Dense ball-distance shaping** (env v4): closest agent player
   gets a tiny per-step reward proportional to (1 - d/D_max), plus
   inactivity penalty after 60 loose steps, plus a one-shot first-
   touch bonus. See `football_env_11v11_v4.py`.
2. **Smaller clip_range**: 0.1 → 0.05 for fine-tuning.
3. **Mixed opponent pool**: each env reset, 50% chance of using the
   self-play snapshot, 25% scripted, 25% policy with action noise.
   The scripted/noisy opponents are easier to beat, providing real
   gradient signal so the policy learns to score.
4. **Lower learning rate**: 2.67e-05 → 5e-06 for the final fine-tune.

Usage:
    py -3.12 football_ai\\train_11v11_v4.py --warmstart-from football_ai\\models_11v11_v3\\best_model.zip
    py -3.12 football_ai\\train_11v11_v4.py --resume
    py -3.12 football_ai\\train_11v11_v4.py --steps 100_000_000

Estimated time on RTX 4060 Ti: ~14-20h per 100M steps.
"""
from __future__ import annotations

import os
import sys
import argparse
import shutil
import random

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

from football_ai.football_env_11v11_v4 import Football11v11EnvV4


# ----------------------------------------------------------------------#
# Paths
# ----------------------------------------------------------------------#
HERE = os.path.dirname(__file__)
MODEL_DIR = os.path.join(HERE, "models_11v11_v4")
LOG_DIR = os.path.join(HERE, "logs_11v11_v4")
SNAPSHOT_FILE = os.path.join(MODEL_DIR, "opponent_snapshot.zip")
SNAPSHOT_FLAG = os.path.join(MODEL_DIR, "opponent_snapshot.version")

# Default v3 best snapshot path. Used by --warmstart-from default.
V3_BEST = os.path.join(HERE, "models_11v11_v3", "best_model.zip")

# Fine-tune is shorter than v3's billion-step plan: we already have a
# baseline policy, we just need it to escape the stand-off.
SELF_PLAY_START_STEP = 5_000_000  # short warm-up vs scripted to refresh signal


# ----------------------------------------------------------------------#
# Mixed-opponent self-play env
# ----------------------------------------------------------------------#
class _NoisyPolicyWrapper:
    """Wraps a PPO policy and injects gaussian noise into the action.

    Used to create a "weak" opponent in the pool: same snapshot, but
    its actions are perturbed so it plays sloppier than the live agent.
    Provides easier gradient signal than pure self-play.
    """

    def __init__(self, policy, noise_std=0.35):
        self.policy = policy
        self.noise_std = float(noise_std)

    def predict(self, obs, deterministic=False):
        action, state = self.policy.predict(obs, deterministic=False)
        action = np.asarray(action, dtype=np.float32)
        action = action + np.random.normal(
            0.0, self.noise_std, size=action.shape
        ).astype(np.float32)
        # Most envs clip to [-1, 1] internally, but be safe.
        action = np.clip(action, -1.0, 1.0)
        return action, state


class MixedOpponentEnv(Football11v11EnvV4):
    """
    Each reset, randomly pick one of:
      - frozen snapshot (50%)
      - noisy snapshot (25%) — same weights but stochastic actions
      - scripted bot (25%) — `opponent_policy=None` falls back to
        `_opponent_ai` from the base env.

    During the warm-up phase (before SNAPSHOT_FLAG exists) every reset
    uses the scripted opponent regardless. This guarantees a real
    learning signal from step 0.
    """

    def __init__(self, render_mode=None, team_side="home"):
        super().__init__(
            render_mode=render_mode,
            team_side=team_side,
            opponent_policy=None,
        )
        self._snapshot_version_seen = -1
        self._cached_policy = None

    def _maybe_reload_snapshot(self):
        if not os.path.exists(SNAPSHOT_FLAG):
            return
        try:
            with open(SNAPSHOT_FLAG, "r") as f:
                v = int(f.read().strip() or "0")
        except Exception:
            return
        if v == self._snapshot_version_seen:
            return
        try:
            self._cached_policy = PPO.load(SNAPSHOT_FILE, device="cpu")
            self._snapshot_version_seen = v
        except Exception:
            pass

    def _pick_opponent(self):
        self._maybe_reload_snapshot()
        if self._cached_policy is None:
            return None  # forces base-class scripted opponent
        roll = random.random()
        if roll < 0.50:
            return self._cached_policy
        if roll < 0.75:
            return _NoisyPolicyWrapper(self._cached_policy, noise_std=0.35)
        return None  # scripted

    def reset(self, seed=None, options=None):
        self.set_opponent_policy(self._pick_opponent())
        return super().reset(seed=seed, options=options)


def make_env(rank):
    def _init():
        env = MixedOpponentEnv(render_mode=None, team_side="home")
        return Monitor(env)
    return _init


# ----------------------------------------------------------------------#
# Snapshot publisher (same idea as v3 but writes to v4 paths)
# ----------------------------------------------------------------------#
class SnapshotPublisherCallback(BaseCallback):
    def __init__(self, freq=500_000, verbose=0):
        super().__init__(verbose)
        self.freq = freq
        self._last = 0

    def _on_step(self):
        if self.num_timesteps < SELF_PLAY_START_STEP:
            if (
                self.verbose
                and self.num_timesteps - self._last >= self.freq
            ):
                self._last = self.num_timesteps
                remaining = SELF_PLAY_START_STEP - self.num_timesteps
                print(
                    f"  [curriculum] vs scripted opponent, "
                    f"{self.num_timesteps:,}/{SELF_PLAY_START_STEP:,} "
                    f"({remaining:,} until self-play)"
                )
            return True
        if self.num_timesteps - self._last < self.freq:
            return True
        self._last = self.num_timesteps
        try:
            tmp = SNAPSHOT_FILE + ".tmp"
            self.model.save(tmp)
            shutil.move(tmp, SNAPSHOT_FILE)
            with open(SNAPSHOT_FLAG, "w") as f:
                f.write(str(self.num_timesteps))
            if self.verbose:
                print(
                    f"  [self-play] published snapshot @ "
                    f"{self.num_timesteps:,} steps"
                )
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


# ----------------------------------------------------------------------#
# Train
# ----------------------------------------------------------------------#
def train(total_steps, resume, warmstart_from):
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
  FOOTBALL 11v11 AI — V4 FINE-TUNE
{'='*60}
  Device: {device}
  Steps: {total_steps:,}
  Self-play starts at: {SELF_PLAY_START_STEP:,}

  Fixes vs v3:
   1. Dense ball-distance shaping (env v4)
   2. clip_range 0.1 -> 0.05
   3. Mixed opponent pool (50% snapshot / 25% noisy / 25% scripted)
   4. learning_rate 2.67e-5 -> 5e-6

  Output: {MODEL_DIR}/
{'='*60}
"""
    )

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # Wipe stale snapshot so warm-up phase always starts vs scripted.
    if not resume:
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

    checkpoint_cb = CheckpointCallback(
        save_freq=500_000 // num_envs,
        save_path=MODEL_DIR,
        name_prefix="football_v4",
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

    latest_ckpt = os.path.join(MODEL_DIR, "football_v4_latest.zip")
    if resume and os.path.exists(latest_ckpt):
        print(f"  Resuming from: {latest_ckpt}")
        model = PPO.load(latest_ckpt, env=env, device=device)
        # Apply v4 hyperparam adjustments to the resumed model.
        model.clip_range = lambda _progress: 0.05
        model.clip_range_vf = lambda _progress: 0.05
        model.learning_rate = 5e-6
        # Force the learning_rate schedule to a constant so SB3 doesn't
        # interpolate from a stale linear schedule.
        model.lr_schedule = lambda _progress: 5e-6
    elif warmstart_from and os.path.exists(warmstart_from):
        print(f"  Warm-starting from: {warmstart_from}")
        model = PPO.load(warmstart_from, env=env, device=device)
        # Same hyperparam swap.
        model.clip_range = lambda _progress: 0.05
        model.clip_range_vf = lambda _progress: 0.05
        model.learning_rate = 5e-6
        model.lr_schedule = lambda _progress: 5e-6
    else:
        # No warm-start: build fresh PPO with v4 hyperparams.
        print("  No warm-start: creating new PPO (v4 hyperparams)...")
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            device=device,
            learning_rate=5e-6,
            n_steps=2048,
            batch_size=256,
            n_epochs=5,
            gamma=0.995,
            gae_lambda=0.95,
            clip_range=0.05,
            clip_range_vf=0.05,
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
    print(f"  Checkpoints -> {MODEL_DIR}")
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
    print(f"\n  Final model saved to: {latest_ckpt}")
    env.close()
    eval_env.close()
    print("  Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--steps", type=int, default=1_000_000_000,
        help="Total fine-tune steps (default 1B).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from football_v4_latest.zip if present.",
    )
    parser.add_argument(
        "--warmstart-from", type=str, default=V3_BEST,
        help=f"V3 snapshot to fine-tune. Default: {V3_BEST}",
    )
    args = parser.parse_args()
    train(args.steps, args.resume, args.warmstart_from)
