"""
Watch v3 model play AGAINST ITSELF (or against another v3 checkpoint).

The v3 env (`Football11v11EnvV3`) has an `opponent_policy` hook: if you
pass a frozen PPO model, it drives the away (red) team via the mirrored
observation. So this script loads a model for `home`, optionally a
DIFFERENT model for `away`, and runs a render loop.

Usage:
    # Same model both sides (true mirror match)
    py -3.12 football_ai/watch_11v11_v3.py

    # Pick a specific home model
    py -3.12 football_ai/watch_11v11_v3.py --home football_ai/models_11v11_v3/best_model.zip

    # Two different checkpoints (e.g. latest vs 50M)
    py -3.12 football_ai/watch_11v11_v3.py \
        --home football_ai/models_11v11_v3/best_model.zip \
        --away football_ai/models_11v11_v3/football_v3_50000040_steps.zip

    # Speed up to 4x
    py -3.12 football_ai/watch_11v11_v3.py --speed 4
"""

import os
import sys
import argparse
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from football_ai.football_env_11v11_v3 import Football11v11EnvV3


HERE = os.path.dirname(__file__)
MODEL_DIR_V3 = os.path.join(HERE, "models_11v11_v3")
MODEL_DIR_V2 = os.path.join(HERE, "models_11v11_v2")


def _auto_pick_model():
    """Prefer v3 best, then newest v3 checkpoint, then v2 best."""
    candidates = [
        os.path.join(MODEL_DIR_V3, "best_model.zip"),
        os.path.join(MODEL_DIR_V3, "football_v3_latest.zip"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # newest checkpoint by mtime
    ckpts = glob.glob(os.path.join(MODEL_DIR_V3, "football_v3_*_steps.zip"))
    if ckpts:
        return max(ckpts, key=os.path.getmtime)
    # fall back to v2
    p = os.path.join(MODEL_DIR_V2, "best_model.zip")
    if os.path.exists(p):
        return p
    return None


def watch(home_path=None, away_path=None, speed=1):
    home_path = home_path or _auto_pick_model()
    if not home_path or not os.path.exists(home_path):
        print("No home model found. Train first or pass --home <path>.")
        return
    away_path = away_path or home_path  # default: mirror match

    print(f"  Home (blue) : {home_path}")
    print(f"  Away (red)  : {away_path}")
    print(f"  Speed       : {speed}x")

    home_model = PPO.load(home_path, device="cpu")
    away_model = (
        home_model if away_path == home_path else PPO.load(away_path, device="cpu")
    )

    env = Football11v11EnvV3(
        render_mode="human", team_side="home", opponent_policy=away_model
    )
    obs, _ = env.reset()

    try:
        import pygame
    except ImportError:
        import pygame_ce as pygame

    print("\n  Blue (left)  = home model")
    print("  Red  (right) = away model (driven via env.opponent_policy)")
    print("  ESC or close window to exit.\n")

    done = False
    info = {}
    total_reward = 0.0
    while not done:
        for _ in range(speed):
            action, _ = home_model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
            if done:
                break

        env.render()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                done = True

    print(
        f"\nFinal: Blue {info.get('home_score', 0)} - "
        f"{info.get('away_score', 0)} Red"
    )
    print(f"Minute: {info.get('minute', 0)}'")
    print(f"Total reward (home POV): {total_reward:.1f}")
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=str, default=None)
    parser.add_argument("--away", type=str, default=None)
    parser.add_argument("--speed", type=int, default=1)
    args = parser.parse_args()
    watch(args.home, args.away, args.speed)
