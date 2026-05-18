"""
Train 11v11 Football AI on GPU - V2 (FIXED parameters).
Fixes: learning rate, entropy, KL target, clip range.

Usage:
    python football_ai/train_11v11_v2.py
    python football_ai/train_11v11_v2.py --steps 100000000

Estimated time on RTX 4060 Ti: ~12-15 hours for 100M steps.
"""

import os
import sys
import argparse
import torch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback
from stable_baselines3.common.monitor import Monitor
from football_ai.football_env_11v11 import Football11v11Env


class LogCallback(BaseCallback):
    """Print progress every N steps."""
    def __init__(self, log_freq=50000):
        super().__init__()
        self.log_freq = log_freq
    
    def _on_step(self):
        if self.num_timesteps % self.log_freq == 0:
            infos = self.locals.get("infos", [])
            scores = [(i.get("home_score", 0), i.get("away_score", 0)) for i in infos if "home_score" in i]
            if scores:
                avg_home = sum(s[0] for s in scores) / len(scores)
                avg_away = sum(s[1] for s in scores) / len(scores)
                print(f"  Step {self.num_timesteps:>10,} | Avg Score: {avg_home:.1f}-{avg_away:.1f}")
        return True


class KLDivergenceCallback(BaseCallback):
    """Stop training epoch early if KL divergence is too high."""
    def __init__(self, target_kl=0.02):
        super().__init__()
        self.target_kl = target_kl
    
    def _on_step(self):
        # Check if approx_kl is available in logger
        if hasattr(self.model, 'logger') and self.model.logger is not None:
            logs = self.logger.name_to_value
            kl = logs.get("train/approx_kl", 0)
            if kl > self.target_kl * 4:  # Emergency brake
                print(f"  ⚠️  KL={kl:.3f} too high! Reducing lr temporarily.")
        return True


def linear_schedule(initial_value):
    """Linear learning rate decay."""
    def func(progress_remaining):
        return progress_remaining * initial_value
    return func


def make_env(rank):
    def _init():
        env = Football11v11Env(render_mode=None, team_side='home')
        return Monitor(env)
    return _init


def train(total_steps=100_000_000, resume=False):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        print("  WARNING: No GPU! Training will be slow.")
        resp = input("  Continue on CPU? (y/n): ")
        if resp.lower() != 'y':
            return

    print(f"""
{'='*60}
  FOOTBALL 11v11 AI - V2 TRAINING (FIXED PARAMS)
{'='*60}
  Device: {device}
  Steps: {total_steps:,}
  
  KEY FIXES vs V1:
  - Learning rate: 0.0002 -> 0.00003 (with linear decay)
  - Entropy coef: 0.005 -> 0.001 (prevents std explosion)
  - Clip range: 0.2 -> 0.1 (smaller policy updates)
  - target_kl: 0.015 (auto-stops if diverging)
  - n_epochs: 10 -> 5 (less overfitting per batch)
  - batch_size: 512 -> 256 (more gradient updates)
  
  Expected: stable training, std stays < 5, real football behavior
{'='*60}
""")

    model_dir = os.path.join(os.path.dirname(__file__), "models_11v11_v2")
    log_dir = os.path.join(os.path.dirname(__file__), "logs_11v11_v2")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # 12 parallel envs (slightly less than before for stability)
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
        save_path=model_dir,
        name_prefix="football_v2"
    )
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=model_dir,
        log_path=log_dir,
        eval_freq=200_000 // num_envs,
        n_eval_episodes=5,
        deterministic=True,
    )
    log_cb = LogCallback(log_freq=100_000)
    kl_cb = KLDivergenceCallback(target_kl=0.015)

    # Model with FIXED parameters
    model_path = os.path.join(model_dir, "football_v2_latest.zip")
    
    if resume and os.path.exists(model_path):
        print(f"  Resuming from: {model_path}")
        model = PPO.load(model_path, env=env, device=device)
    else:
        print("  Creating new PPO model (V2 - fixed params)...")
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            device=device,
            # === CRITICAL FIXES ===
            learning_rate=linear_schedule(3e-5),  # Start at 0.00003, decay to 0
            n_steps=2048,           # Shorter rollouts = more frequent updates
            batch_size=256,         # Smaller batches = more gradient steps
            n_epochs=5,             # Less epochs = less overfitting
            gamma=0.995,            # Slightly shorter horizon
            gae_lambda=0.95,
            clip_range=0.1,         # SMALLER clip = more stable updates
            clip_range_vf=0.1,      # Also clip value function
            ent_coef=0.001,         # LOW entropy = std won't explode
            vf_coef=0.5,
            max_grad_norm=0.5,
            target_kl=0.015,        # AUTO-STOP if KL too high (KEY FIX)
            tensorboard_log=None,   # No tensorboard needed
            policy_kwargs=dict(
                net_arch=dict(
                    pi=[512, 256, 128],   # Slightly smaller network (faster, less overfit)
                    vf=[512, 256, 128]
                ),
                activation_fn=torch.nn.Tanh,  # Tanh is more stable than ReLU for PPO
                log_std_init=-1.0,            # Start with LOW std (less random actions)
            ),
        )

    print(f"\n  Training for {total_steps:,} steps...")
    print(f"  Watch for: std should stay between 0.3-3.0")
    print(f"  Watch for: approx_kl should stay < 0.05")
    print(f"  Watch for: clip_fraction should be 0.05-0.15")
    print(f"  Checkpoints: {model_dir}/")
    print(f"  Press Ctrl+C to stop (auto-saves).\n")

    try:
        model.learn(
            total_timesteps=total_steps,
            callback=[checkpoint_cb, eval_cb, log_cb, kl_cb],
            progress_bar=False,
        )
    except KeyboardInterrupt:
        print("\n\n  Training interrupted! Saving...")
    
    model.save(os.path.join(model_dir, "football_v2_latest"))
    model.save(os.path.join(model_dir, f"football_v2_{total_steps//1_000_000}M"))
    print(f"\n  Model saved to: {model_dir}/")
    
    env.close()
    eval_env.close()
    print("  Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=100_000_000,
                       help="Total training steps (default 100M, ~12-15h on 4060 Ti)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from last checkpoint")
    args = parser.parse_args()
    train(args.steps, args.resume)
