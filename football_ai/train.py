"""
Train football AI v2 with roles, passing, stamina.

Usage:
    python football_ai/train.py              # Train from scratch (1M steps, ~45 min)
    python football_ai/train.py --steps 5000000  # Longer training (5M steps, ~3 hours)
    python football_ai/train.py --selfplay   # Enable self-play after initial training
"""

import os
import sys
import argparse
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.monitor import Monitor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from football_ai.football_env import FootballEnv


def make_env():
    def _init():
        return Monitor(FootballEnv(render_mode=None))
    return _init


def train(total_steps=1_000_000, selfplay=False):
    print("=" * 60)
    print("  FOOTBALL AI v2 - ROLES + PASSING + STAMINA")
    print("=" * 60)
    print(f"\n  Steps: {total_steps:,}")
    print(f"  Self-play: {'ON' if selfplay else 'OFF (scripted red AI)'}")
    print(f"  Roles: Defender | Midfielder | Forward")
    print(f"  Actions: Move X/Y + Kick Power + Kick Direction + Pass")
    print()

    model_dir = os.path.join(os.path.dirname(__file__), "models")
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # 4 parallel environments
    num_envs = 4
    env = DummyVecEnv([make_env() for _ in range(num_envs)])
    eval_env = DummyVecEnv([make_env()])

    checkpoint_cb = CheckpointCallback(save_freq=50000, save_path=model_dir, name_prefix="football_v2")
    eval_cb = EvalCallback(eval_env, best_model_save_path=model_dir, log_path=log_dir,
                           eval_freq=25000, n_eval_episodes=5, deterministic=True)

    # Check if we can resume
    resume_path = os.path.join(model_dir, "football_v2_final.zip")
    if os.path.exists(resume_path) and not selfplay:
        print(f"Resuming from {resume_path}")
        model = PPO.load(resume_path, env=env)
    else:
        model = PPO(
            "MlpPolicy", env, verbose=1,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=256,
            n_epochs=10,
            gamma=0.995,       # Higher gamma for long-term planning
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.02,     # More exploration for complex actions
            vf_coef=0.5,
            max_grad_norm=0.5,
            tensorboard_log=None,  # Set to log_dir if tensorboard is installed
            policy_kwargs=dict(
                net_arch=dict(pi=[512, 256, 128], vf=[512, 256, 128])
            ),
        )

    print(f"\nTraining for {total_steps:,} steps...\n")
    model.learn(total_timesteps=total_steps, callback=[checkpoint_cb, eval_cb], progress_bar=False)

    final_path = os.path.join(model_dir, "football_v2_final")
    model.save(final_path)
    print(f"\nModel saved: {final_path}.zip")

    # --- SELF-PLAY PHASE ---
    if selfplay:
        print("\n" + "=" * 60)
        print("  PHASE 2: SELF-PLAY TRAINING")
        print("=" * 60)
        print("  Red team now uses the trained model as opponent.")
        print(f"  Training for {total_steps:,} more steps...\n")

        # Load trained model as red opponent
        red_model = PPO.load(final_path)

        # Create self-play environment
        def make_selfplay_env():
            def _init():
                return Monitor(FootballEnv(render_mode=None, red_model=red_model))
            return _init

        sp_env = DummyVecEnv([make_selfplay_env() for _ in range(num_envs)])

        # Continue training against itself
        model.set_env(sp_env)
        model.learn(total_timesteps=total_steps, callback=[checkpoint_cb], progress_bar=False)

        sp_final = os.path.join(model_dir, "football_v2_selfplay")
        model.save(sp_final)
        print(f"\nSelf-play model saved: {sp_final}.zip")
        sp_env.close()

    env.close()
    eval_env.close()
    print("\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=1_000_000)
    parser.add_argument("--selfplay", action="store_true")
    args = parser.parse_args()
    train(args.steps, args.selfplay)
