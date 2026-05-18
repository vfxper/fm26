"""
Watch trained 11v11 model play.

Usage:
    python football_ai/watch_11v11.py
    python football_ai/watch_11v11.py --speed 2
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from football_ai.football_env_11v11 import Football11v11Env


def watch(model_path=None, speed=1):
    if model_path is None:
        # Try v2 first (better training), then v1
        search_dirs = [
            os.path.join(os.path.dirname(__file__), "models_11v11_v2"),
            os.path.join(os.path.dirname(__file__), "models_11v11"),
        ]
        for model_dir in search_dirs:
            for name in ["best_model.zip", "football_v2_latest.zip", "football_11v11_latest.zip"]:
                p = os.path.join(model_dir, name)
                if os.path.exists(p):
                    model_path = p
                    break
            if model_path:
                break

    if not model_path or not os.path.exists(model_path):
        print("No trained model found!")
        print("Run: python football_ai/train_11v11_gpu.py")
        return

    print(f"Loading: {model_path}")
    model = PPO.load(model_path)

    env = Football11v11Env(render_mode="human", team_side='home')
    obs, _ = env.reset()

    print("\n  Blue (left) = Trained AI (11 players)")
    print("  Red (right) = Scripted AI")
    print(f"  Speed: {speed}x")
    print("  ESC or close window to exit.\n")

    try:
        import pygame
    except ImportError:
        import pygame_ce as pygame

    done = False
    total_reward = 0

    while not done:
        for _ in range(speed):
            action, _ = model.predict(obs, deterministic=True)
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

    print(f"\nFinal: Blue {info['home_score']} - {info['away_score']} Red")
    print(f"Minute: {info['minute']}'")
    print(f"Total reward: {total_reward:.1f}")
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--speed", type=int, default=1)
    args = parser.parse_args()
    watch(args.model, args.speed)
