"""
Unit tests for match-time injury simulation in MatchSimulator.

Covers Task 14.1 (Implement injury simulation during matches) and the
relevant Acceptance Criteria from Requirement 11:

    11.1 — Risk depends on player attributes (bravery, stamina, strength),
           match intensity, and pitch condition.
    11.2 — Three severity buckets (Minor 1-2 / Moderate 3-8 / Severe 9+).
    11.3 — Injured player is removed from the match and a recovery
           timeline is set (recovery_weeks).
"""

import random
from collections import Counter
from typing import List, Dict, Any

import pytest

from app.services.match_simulator import (
    MatchSimulator,
    MatchResult,
    MatchEvent,
    InjuryEvent,
)


def _player(
    name: str,
    *,
    ca: int = 120,
    position: str = "M C",
    bravery: int = 10,
    stamina: int = 10,
    strength: int = 10,
    player_id: int = None,
    squad_player_id: int = None,
    is_injury_prone: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "ca": ca,
        "position": position,
        "bravery": bravery,
        "stamina": stamina,
        "strength": strength,
        "player_id": player_id,
        "squad_player_id": squad_player_id,
        "is_injury_prone": is_injury_prone,
    }


def _squad(prefix: str, *, ca: int = 120, **attrs) -> List[Dict[str, Any]]:
    """Build a 22-man squad with 1 GK + 21 outfield players."""
    squad = [
        _player(f"{prefix}_GK", position="GK", ca=ca, player_id=hash(prefix + "_GK") & 0xFFFF, **attrs)
    ]
    positions = ["D C", "D C", "D L", "D R", "M C", "M C",
                 "M L", "M R", "AM C", "ST C", "ST C"]
    # 11 starters
    for i, pos in enumerate(positions):
        squad.append(_player(
            f"{prefix}_{i}",
            position=pos, ca=ca,
            player_id=(hash(prefix + str(i)) & 0xFFFF) + 1,
            **attrs,
        ))
    # 10 bench players
    for i in range(10):
        squad.append(_player(
            f"{prefix}_B{i}",
            position="M C", ca=max(50, ca - 10),
            player_id=(hash(prefix + "B" + str(i)) & 0xFFFF) + 100,
            **attrs,
        ))
    return squad


def _run(simulator: MatchSimulator, **overrides) -> MatchResult:
    home = overrides.pop("home_players", _squad("Home"))
    away = overrides.pop("away_players", _squad("Away"))
    return simulator.simulate(
        home_club=overrides.pop("home_club", "Home FC"),
        away_club=overrides.pop("away_club", "Away FC"),
        home_avg_ca=overrides.pop("home_avg_ca", 120),
        away_avg_ca=overrides.pop("away_avg_ca", 120),
        home_players=home,
        away_players=away,
        **overrides,
    )


class TestInjurySimulation:
    """Direct unit tests on the injury logic."""

    def test_injuries_field_present_on_match_result(self):
        """MatchResult exposes an `injuries` list (empty by default)."""
        sim = MatchSimulator()
        result = _run(sim)
        assert hasattr(result, "injuries")
        assert isinstance(result.injuries, list)

    def test_injury_event_fields(self):
        """An injury event carries severity, recovery_weeks, minute, and team."""
        sim = MatchSimulator()
        # Run many matches with high-risk inputs so at least one match
        # produces an injury — guards against random seeds that happen
        # to roll zero on a single match.
        random.seed(7)
        weak_squad = _squad("Weak", ca=80, bravery=18, stamina=4, strength=4)
        strong_squad = _squad("Strong", ca=80, bravery=18, stamina=4, strength=4)
        all_injuries: List[InjuryEvent] = []
        for _ in range(20):
            result = _run(
                sim,
                home_players=weak_squad,
                away_players=strong_squad,
                home_avg_ca=80, away_avg_ca=80,
                pitch_condition="waterlogged",
                match_intensity=1.5,
            )
            all_injuries.extend(result.injuries)
        assert len(all_injuries) >= 1, "expected at least one injury across 20 high-risk matches"
        inj = all_injuries[0]
        assert inj.player_name
        assert inj.severity in {"minor", "moderate", "severe"}
        assert inj.recovery_weeks >= 1
        assert 1 <= inj.match_minute <= 95
        assert inj.team in {"home", "away"}
        assert inj.injury_type

    def test_severity_recovery_weeks_match_buckets(self):
        """Severity buckets map to documented recovery week ranges (Req 11.2)."""
        sim = MatchSimulator()
        random.seed(0)
        seen = {"minor": [], "moderate": [], "severe": []}
        for _ in range(2000):
            sev, weeks = sim._roll_injury_severity()
            seen[sev].append(weeks)
        assert seen["minor"], "expected to see minor injuries in 2000 rolls"
        assert seen["moderate"], "expected to see moderate injuries"
        assert seen["severe"], "expected to see severe injuries"
        assert all(1 <= w <= 2 for w in seen["minor"])
        assert all(3 <= w <= 8 for w in seen["moderate"])
        assert all(w >= 9 for w in seen["severe"])

    def test_severity_distribution_matches_design(self):
        """Roughly 60/30/10 over many rolls (within tolerance)."""
        random.seed(123)
        sim = MatchSimulator()
        counts = Counter()
        N = 4000
        for _ in range(N):
            sev, _ = sim._roll_injury_severity()
            counts[sev] += 1
        # Wide tolerance — these are random rolls.
        assert 0.50 * N <= counts["minor"] <= 0.70 * N
        assert 0.20 * N <= counts["moderate"] <= 0.40 * N
        assert 0.05 * N <= counts["severe"] <= 0.15 * N

    def test_pitch_condition_increases_risk(self):
        """Waterlogged pitch raises risk vs a good pitch (Req 11.1)."""
        sim = MatchSimulator()
        p = _player("X", stamina=10, strength=10, bravery=10)
        good = sim._compute_injury_probability(p, 1.0, "good")
        soft = sim._compute_injury_probability(p, 1.0, "soft")
        heavy = sim._compute_injury_probability(p, 1.0, "heavy")
        wet = sim._compute_injury_probability(p, 1.0, "waterlogged")
        assert good < soft < heavy < wet

    def test_intensity_increases_risk(self):
        sim = MatchSimulator()
        p = _player("X")
        low = sim._compute_injury_probability(p, 0.8, "good")
        normal = sim._compute_injury_probability(p, 1.0, "good")
        derby = sim._compute_injury_probability(p, 1.4, "good")
        assert low < normal < derby

    def test_better_physicals_lower_risk(self):
        """Higher stamina / strength produce lower injury probability."""
        sim = MatchSimulator()
        weak = _player("Weak", stamina=4, strength=4, bravery=10, ca=120)
        strong = _player("Strong", stamina=18, strength=18, bravery=10, ca=120)
        assert sim._compute_injury_probability(weak, 1.0, "good") > \
               sim._compute_injury_probability(strong, 1.0, "good")

    def test_higher_bravery_slightly_raises_risk(self):
        """Bravery raises risk slightly (more 50/50 challenges)."""
        sim = MatchSimulator()
        cautious = _player("Cautious", bravery=4, stamina=10, strength=10)
        brave = _player("Brave", bravery=18, stamina=10, strength=10)
        assert sim._compute_injury_probability(brave, 1.0, "good") > \
               sim._compute_injury_probability(cautious, 1.0, "good")

    def test_injury_prone_flag_increases_risk(self):
        """Injury-prone flag adds a 15% risk multiplier (Req 11.9 setup)."""
        sim = MatchSimulator()
        normal = _player("N")
        prone = _player("P", is_injury_prone=True)
        rn = sim._compute_injury_probability(normal, 1.0, "good")
        rp = sim._compute_injury_probability(prone, 1.0, "good")
        assert rp > rn
        # Within float rounding the multiplier is exactly 1.15.
        assert abs(rp / rn - 1.15) < 1e-6

    def test_injured_player_removed_from_subsequent_events(self):
        """An injured player must not appear in later cards or substitutions."""
        random.seed(42)
        sim = MatchSimulator()
        # High-risk squads to make injuries likely.
        home = _squad("HomeWk", ca=80, bravery=18, stamina=4, strength=4)
        away = _squad("AwayWk", ca=80, bravery=18, stamina=4, strength=4)
        runs_with_injury = 0
        for _ in range(20):
            result = _run(
                sim, home_players=home, away_players=away,
                home_avg_ca=80, away_avg_ca=80,
                pitch_condition="waterlogged", match_intensity=1.5,
            )
            if not result.injuries:
                continue
            runs_with_injury += 1
            for inj in result.injuries:
                for ev in result.events:
                    # Skip events at-or-before the injury minute and the
                    # injury event itself.
                    if ev.minute < inj.match_minute:
                        continue
                    if ev.event_type == "injury" and ev.player_name == inj.player_name:
                        continue
                    if ev.event_type in ("yellow_card", "red_card"):
                        assert ev.player_name != inj.player_name, (
                            f"{inj.player_name} got a card after their injury"
                        )
                    if ev.event_type == "substitution":
                        parts = (ev.player_name or "").split(" → ")
                        assert all(p != inj.player_name for p in parts), (
                            f"{inj.player_name} appears in substitution: {ev.player_name}"
                        )
        assert runs_with_injury >= 1, "no injuries occurred across 20 high-risk runs"

    def test_injury_event_is_added_to_timeline(self):
        random.seed(99)
        sim = MatchSimulator()
        home = _squad("Hi", bravery=18, stamina=4, strength=4)
        away = _squad("Ai", bravery=18, stamina=4, strength=4)
        seen_any = False
        for _ in range(20):
            result = _run(
                sim, home_players=home, away_players=away,
                pitch_condition="waterlogged", match_intensity=1.5,
            )
            if not result.injuries:
                continue
            seen_any = True
            injury_events = [e for e in result.events if e.event_type == "injury"]
            assert len(injury_events) == len(result.injuries)
            for ev in injury_events:
                # Description mentions the injury type and severity in Russian.
                assert "Травма" in ev.description
        assert seen_any, "no injuries to inspect across 20 runs"

    def test_to_dict_includes_injuries(self):
        random.seed(101)
        sim = MatchSimulator()
        result = _run(sim)
        d = sim.to_dict(result)
        assert "injuries" in d
        assert isinstance(d["injuries"], list)
        # Even when empty, it's serialisable.
        assert len(d["injuries"]) == len(result.injuries)
        for entry in d["injuries"]:
            assert {"player_name", "severity", "recovery_weeks",
                    "match_minute", "team", "injury_type"} <= set(entry)

    def test_persistence_fields_propagate_through_simulator(self):
        """player_id and squad_player_id flow from input dicts to InjuryEvent."""
        random.seed(31)
        sim = MatchSimulator()
        # Heightened risk squads with explicit ids on the home side so
        # we can verify they're carried into the InjuryEvent.
        home = []
        for i in range(22):
            home.append(_player(
                f"H{i}",
                ca=80, bravery=18, stamina=4, strength=4,
                player_id=900 + i,
                squad_player_id=8000 + i,
            ))
        away = _squad("Aw", ca=80, bravery=18, stamina=4, strength=4)

        seen_home_injuries: List[InjuryEvent] = []
        for _ in range(20):
            result = _run(
                sim, home_players=home, away_players=away,
                home_avg_ca=80, away_avg_ca=80,
                pitch_condition="waterlogged", match_intensity=1.5,
            )
            seen_home_injuries.extend(
                [i for i in result.injuries if i.team == "home"]
            )
        assert seen_home_injuries, "no home-side injuries in 20 runs"
        for inj in seen_home_injuries:
            assert inj.player_id is not None
            assert inj.squad_player_id is not None
            assert 900 <= inj.player_id < 922
            assert 8000 <= inj.squad_player_id < 8022

    def test_no_injuries_when_attributes_extreme_low_risk(self):
        """With strong attributes + good pitch + low intensity, runs of
        matches should produce significantly fewer injuries than runs
        with the inverse setup (sanity check, not zero)."""
        random.seed(2024)
        sim = MatchSimulator()
        safe_home = _squad("SafeH", ca=170, bravery=4, stamina=20, strength=20)
        safe_away = _squad("SafeA", ca=170, bravery=4, stamina=20, strength=20)
        risky_home = _squad("RiskyH", ca=70, bravery=18, stamina=4, strength=4)
        risky_away = _squad("RiskyA", ca=70, bravery=18, stamina=4, strength=4)

        safe_total = 0
        risky_total = 0
        for _ in range(50):
            r = _run(
                sim, home_players=safe_home, away_players=safe_away,
                home_avg_ca=170, away_avg_ca=170,
                pitch_condition="good", match_intensity=0.8,
            )
            safe_total += len(r.injuries)
            r = _run(
                sim, home_players=risky_home, away_players=risky_away,
                home_avg_ca=70, away_avg_ca=70,
                pitch_condition="waterlogged", match_intensity=1.5,
            )
            risky_total += len(r.injuries)
        assert risky_total > safe_total, (
            f"risky setup ({risky_total}) should produce more injuries "
            f"than safe setup ({safe_total})"
        )


class TestInjurySimulatorIntegration:
    """End-to-end checks that the simulator's contract matches what
    callers (match_persistence.save_match_result) expect."""

    def test_simulate_returns_match_result_with_required_attrs(self):
        sim = MatchSimulator()
        result = _run(sim)
        # Existing fields must still be present (back-compat).
        assert isinstance(result.home_score, int)
        assert isinstance(result.away_score, int)
        assert isinstance(result.events, list)
        # New field
        assert isinstance(result.injuries, list)

    def test_injury_event_dataclass_has_persistence_fields(self):
        """InjuryEvent carries the fields required by save_match_result."""
        ev = InjuryEvent(
            player_name="John",
            injury_type="Hamstring Strain",
            severity="moderate",
            recovery_weeks=4,
            match_minute=65,
            team="home",
        )
        # Fields used inside match_persistence.save_match_result.
        for field in (
            "player_id", "squad_player_id", "injury_type",
            "injury_description", "severity", "recovery_weeks",
            "match_minute",
        ):
            assert hasattr(ev, field), f"missing {field}"
