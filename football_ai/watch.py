"""
Watch trained model play. Shows roles, stamina bars, passing.

Usage:
    python football_ai/watch.py
    python football_ai/watch.py --model football_ai/models/football_v2_selfplay.zip
    python football_ai/watch.py --speed 2   # 2x speed
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from football_ai.football_env import FootballEnv


def watch(model_path=None, speed=1):
    if model_path is None:
        model_dir = os.path.join(os.path.dirname(__file__), "models")
        for name in ["football_v2_selfplay.zip", "best_model.zip", "football_v2_final.zip"]:
            p = os.path.join(model_dir, name)
            if os.path.exists(p):
                model_path = p
                break

    if not model_path or not os.path.exists(model_path):
        print("No trained model found! Run 'python football_ai/train.py' first.")
        return

    print(f"Loading: {model_path}")
    model = PPO.load(model_path)

    env = FootballEnv(render_mode="human")
    obs, _ = env.reset()

    print("\n  Blue (left) = Trained AI")
    print("  Red (right) = Scripted AI")
    print("  Roles: DEF | MID | FWD")
    print("  Green bars = Stamina")
    print(f"  Speed: {speed}x")
    print("\n  Close window to exit.\n")

    import pygame
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
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    done = True

    print(f"\nFinal: Blue {info['blue_score']} - {info['red_score']} Red")
    print(f"Total reward: {total_reward:.1f}")
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--speed", type=int, default=1)
    args = parser.parse_args()
    watch(args.model, args.speed)
