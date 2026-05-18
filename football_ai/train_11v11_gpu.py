"""
Train 11v11 Football AI on GPU (RTX 4060 Ti 16GB).
200M steps with curriculum learning and self-play.

Usage:
    python football_ai/train_11v11_gpu.py
    python football_ai/train_11v11_gpu.py --steps 200000000
    python football_ai/train_11v11_gpu.py --resume

Estimated time on RTX 4060 Ti: ~18-24 hours for 200M steps.
"""

import os
import sys
import argparse
import torch

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
            # Get recent episode info
            infos = self.locals.get("infos", [])
            scores = [(i.get("home_score", 0), i.get("away_score", 0)) for i in infos if "home_score" in i]
            if scores:
                avg_home = sum(s[0] for s in scores) / len(scores)
                avg_away = sum(s[1] for s in scores) / len(scores)
                print(f"  Step {self.num_timesteps:>10,} | Avg Score: {avg_home:.1f}-{avg_away:.1f}")
        return True


def make_env(rank):
    def _init():
        env = Football11v11Env(render_mode=None, team_side='home')
        return Monitor(env)
    return _init


def train(total_steps=200_000_000, resume=False):
    # Check GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        print("  WARNING: No GPU detected! Training will be VERY slow on CPU.")
        print("  Install CUDA toolkit + pytorch with CUDA support:")
        print("  python -m pip install torch --index-url https://download.pytorch.org/whl/cu121")
        resp = input("  Continue on CPU? (y/n): ")
        if resp.lower() != 'y':
            return

    print(f"""
{'='*60}
  FOOTBALL 11v11 AI - GPU TRAINING
{'='*60}
  Device: {device}
  Steps: {total_steps:,}
  Players: 11 vs 11
  Features: Roles, Passing, Shooting, Tackling, Fouls, Stamina
  Estimated time: {total_steps / 10_000_000:.0f}-{total_steps / 8_000_000:.0f} hours
{'='*60}
""")

    model_dir = os.path.join(os.path.dirname(__file__), "models_11v11")
    log_dir = os.path.join(os.path.dirname(__file__), "logs_11v11")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # Parallel environments (more = faster but more RAM)
    # RTX 4060 Ti 16GB can handle 16 parallel envs easily
    num_envs = 16
    print(f"  Creating {num_envs} parallel environments...")
    
    try:
        env = SubprocVecEnv([make_env(i) for i in range(num_envs)])
    except Exception:
        print("  SubprocVecEnv failed, falling back to DummyVecEnv...")
        env = DummyVecEnv([make_env(i) for i in range(num_envs)])

    eval_env = DummyVecEnv([make_env(99)])

    # Callbacks
    checkpoint_cb = CheckpointCallback(
        save_freq=500_000 // num_envs,  # Save every 500K steps
        save_path=model_dir,
        name_prefix="football_11v11"
    )
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=model_dir,
        log_path=log_dir,
        eval_freq=200_000 // num_envs,
        n_eval_episodes=3,
        deterministic=True,
    )
    log_cb = LogCallback(log_freq=100_000)

    # Model
    model_path = os.path.join(model_dir, "football_11v11_latest.zip")
    
    if resume and os.path.exists(model_path):
        print(f"  Resuming from: {model_path}")
        model = PPO.load(model_path, env=env, device=device)
    else:
        print("  Creating new PPO model...")
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            device=device,
            learning_rate=2e-4,
            n_steps=4096,          # More steps per update (better for complex envs)
            batch_size=512,        # Larger batch for GPU
            n_epochs=10,
            gamma=0.997,           # Very long-term planning
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.005,        # Less exploration (11v11 is complex)
            vf_coef=0.5,
            max_grad_norm=0.5,
            tensorboard_log=None,
            policy_kwargs=dict(
                net_arch=dict(
                    pi=[1024, 512, 256],  # Larger network for 11v11
                    vf=[1024, 512, 256]
                ),
                activation_fn=torch.nn.ReLU,
            ),
        )

    print(f"\n  Training for {total_steps:,} steps...")
    print(f"  Progress logged every 100K steps.")
    print(f"  Checkpoints saved every 500K steps to: {model_dir}/")
    print(f"  Press Ctrl+C to stop (model auto-saves).\n")

    try:
        model.learn(
            total_timesteps=total_steps,
            callback=[checkpoint_cb, eval_cb, log_cb],
            progress_bar=False,
        )
    except KeyboardInterrupt:
        print("\n\n  Training interrupted! Saving model...")
    
    # Save final
    model.save(os.path.join(model_dir, "football_11v11_latest"))
    model.save(os.path.join(model_dir, f"football_11v11_{total_steps//1_000_000}M"))
    print(f"\n  Model saved to: {model_dir}/football_11v11_latest.zip")
    
    env.close()
    eval_env.close()
    print("  Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=200_000_000)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    train(args.steps, args.resume)
