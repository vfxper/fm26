"""
Simple Match Simulator for calendar-based match simulation.

Generates match results based on team CA averages with:
- Final score (Poisson-like distribution based on CA difference)
- Match timeline (goals, cards, substitutions)
- Basic stats (possession, shots)
"""

import random
from typing import List, Dict, Any


class SimpleMatchSimulator:
    """Simple match simulator that generates results based on team CA averages."""

    def simulate_match(
        self,
        home_team_name: str,
        away_team_name: str,
        home_team_ca: int,
        away_team_ca: int,
        home_players: List[Dict[str, Any]],
        away_players: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Simulate a match and return result.

        Args:
            home_team_name: Name of home team
            away_team_name: Name of away team
            home_team_ca: Average CA of home team players
            away_team_ca: Average CA of away team players
            home_players: List of dicts with 'name' and 'ca' keys
            away_players: List of dicts with 'name' and 'ca' keys

        Returns:
            Dict with home_score, away_score, timeline, possession, shots
        """
        # Calculate expected goals based on CA difference
        avg_ca = (home_team_ca + away_team_ca) / 2 if (home_team_ca + away_team_ca) > 0 else 140
        base_xg = 1.5

        # Home advantage: +5% boost
        home_xg = base_xg * (home_team_ca / avg_ca) * 1.05
        away_xg = base_xg * (away_team_ca / avg_ca) * 0.95

        # Clamp expected goals
        home_xg = max(0.3, min(4.0, home_xg))
        away_xg = max(0.3, min(4.0, away_xg))

        # Generate goals using simple Poisson-like approach
        home_score = self._poisson_goals(home_xg)
        away_score = self._poisson_goals(away_xg)

        # Generate timeline
        timeline = []

        # Goals
        home_attackers = [p for p in home_players if p.get("name")] or [{"name": "Player"}]
        away_attackers = [p for p in away_players if p.get("name")] or [{"name": "Player"}]

        goal_minutes = sorted(random.sample(range(1, 91), min(home_score + away_score, 15)))

        home_goals_placed = 0
        away_goals_placed = 0
        for minute in goal_minutes:
            if home_goals_placed < home_score:
                scorer = random.choice(home_attackers)
                timeline.append({
                    "minute": minute,
                    "type": "goal",
                    "team": "home",
                    "player": scorer["name"],
                    "team_name": home_team_name,
                })
                home_goals_placed += 1
            elif away_goals_placed < away_score:
                scorer = random.choice(away_attackers)
                timeline.append({
                    "minute": minute,
                    "type": "goal",
                    "team": "away",
                    "player": scorer["name"],
                    "team_name": away_team_name,
                })
                away_goals_placed += 1

        # Yellow cards (2-4 per match)
        num_yellows = random.randint(2, 4)
        for _ in range(num_yellows):
            team = random.choice(["home", "away"])
            players_pool = home_players if team == "home" else away_players
            team_name = home_team_name if team == "home" else away_team_name
            if players_pool:
                player = random.choice(players_pool)
                timeline.append({
                    "minute": random.randint(1, 90),
                    "type": "yellow_card",
                    "team": team,
                    "player": player["name"],
                    "team_name": team_name,
                })

        # Red cards (5% chance per team)
        for team in ["home", "away"]:
            if random.random() < 0.05:
                players_pool = home_players if team == "home" else away_players
                team_name = home_team_name if team == "home" else away_team_name
                if players_pool:
                    player = random.choice(players_pool)
                    timeline.append({
                        "minute": random.randint(30, 85),
                        "type": "red_card",
                        "team": team,
                        "player": player["name"],
                        "team_name": team_name,
                    })

        # Substitutions (3 per team, minutes 55-85)
        for team in ["home", "away"]:
            players_pool = home_players if team == "home" else away_players
            team_name = home_team_name if team == "home" else away_team_name
            if len(players_pool) >= 6:
                sub_minutes = sorted(random.sample(range(55, 86), 3))
                subs_out = random.sample(players_pool, min(3, len(players_pool)))
                subs_in = [p for p in players_pool if p not in subs_out][:3]
                for i in range(min(3, len(subs_out), len(subs_in))):
                    timeline.append({
                        "minute": sub_minutes[i],
                        "type": "substitution",
                        "team": team,
                        "player_out": subs_out[i]["name"],
                        "player_in": subs_in[i]["name"],
                        "team_name": team_name,
                    })

        # Sort timeline by minute
        timeline.sort(key=lambda e: e["minute"])

        # Calculate possession based on CA ratio
        total_ca = home_team_ca + away_team_ca if (home_team_ca + away_team_ca) > 0 else 280
        possession_home = int(50 * (home_team_ca / (total_ca / 2)) + random.randint(-5, 5))
        possession_home = max(30, min(70, possession_home))
        possession_away = 100 - possession_home

        # Shots based on goals and CA
        shots_home = home_score + random.randint(3, 8)
        shots_away = away_score + random.randint(3, 8)

        return {
            "home_team": home_team_name,
            "away_team": away_team_name,
            "home_score": home_score,
            "away_score": away_score,
            "timeline": timeline,
            "possession_home": possession_home,
            "possession_away": possession_away,
            "shots_home": shots_home,
            "shots_away": shots_away,
            "shots_on_target_home": home_score + random.randint(1, 3),
            "shots_on_target_away": away_score + random.randint(1, 3),
        }

    def _poisson_goals(self, expected: float) -> int:
        """Simple Poisson-like goal generation."""
        # Use inverse transform sampling approximation
        goals = 0
        p = random.random()
        cumulative = 0.0
        import math
        for k in range(8):  # Max 7 goals
            prob = (expected ** k) * math.exp(-expected) / math.factorial(k)
            cumulative += prob
            if p <= cumulative:
                goals = k
                break
        else:
            goals = 7
        return goals
