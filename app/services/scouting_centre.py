"""
Scouting Centre - Full scouting system (FM26-level depth)

Features:
- Scout assignments (region/country/competition/player)
- Knowledge map (per-country knowledge 0-100%)
- Scout reports with generated text
- Report accuracy based on scout skill + region knowledge
- Scouting budget management
- Shortlist management
- Progressive attribute revelation
"""

import random
import json
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# === DATA CLASSES ===

@dataclass
class ScoutProfile:
    """A scout working for the club."""
    id: int
    name: str
    judging_ability: int = 12      # 1-20: how accurate reports are
    judging_potential: int = 12    # 1-20: how well they judge PA
    tactical_knowledge: int = 10   # 1-20
    adaptability: int = 12         # 1-20: how fast they learn new regions
    determination: int = 14        # 1-20: affects report speed
    wage: int = 5000               # weekly wage
    region_knowledge: Dict[str, int] = field(default_factory=dict)  # country -> 0-100
    current_assignment: Optional[Dict] = None
    status: str = "idle"           # idle, assigned, traveling, reporting

    def get_knowledge(self, country: str) -> int:
        return self.region_knowledge.get(country, 0)

    def add_knowledge(self, country: str, amount: int):
        current = self.region_knowledge.get(country, 0)
        self.region_knowledge[country] = min(100, current + amount)


@dataclass
class ScoutAssignment:
    """An active scouting assignment."""
    id: int
    scout_id: int
    assignment_type: str  # 'player', 'region', 'competition'
    target: str           # player_id, country name, or competition name
    position_filter: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    max_price: Optional[int] = None
    duration_weeks: int = 4
    priority: str = "normal"  # low, normal, high, urgent
    weeks_elapsed: int = 0
    status: str = "active"    # active, completed, cancelled
    reports_generated: int = 0
    started_at: Optional[str] = None


@dataclass
class ScoutReport:
    """A completed scouting report on a player."""
    id: int
    player_id: int
    player_name: str
    scout_id: int
    scout_name: str
    assignment_id: int
    
    # Ratings (stars, 0.5 increments)
    current_ability_stars: float = 3.0   # 0.5 - 5.0
    potential_stars: float = 3.5
    recommendation: str = "B"            # A+, A, B+, B, C+, C, D
    
    # Report text
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    summary_text: str = ""
    
    # Accuracy (how close to real values)
    accuracy_pct: int = 70  # 0-100
    
    # Revealed attributes (only these are shown to player)
    revealed_attributes: Dict[str, int] = field(default_factory=dict)
    
    # Status
    status: str = "new"  # new, shortlisted, negotiating, rejected
    created_at: Optional[str] = None


# === REPORT GENERATION ===

STRENGTH_TEMPLATES = {
    "pace": [
        "Обладает выдающейся скоростью, способен убежать от любого защитника",
        "Очень быстрый игрок, его скорость — главное оружие",
    ],
    "dribbling": [
        "Великолепный дриблёр, обыгрывает один в один с лёгкостью",
        "Техничный игрок с отличным дриблингом на скорости",
    ],
    "passing": [
        "Отличный пасующий, видит поле и раздаёт передачи на любую дистанцию",
        "Точные передачи — его визитная карточка",
    ],
    "finishing": [
        "Хладнокровный завершитель, редко промахивается из выгодных позиций",
        "Отличное завершение атак, опасен в штрафной",
    ],
    "tackling": [
        "Жёсткий и точный в отборе, выигрывает большинство единоборств",
        "Надёжный защитник с отличным таймингом подкатов",
    ],
    "heading": [
        "Доминирует в воздухе, опасен при стандартах",
        "Отличная игра головой, выигрывает верховые дуэли",
    ],
    "vision": [
        "Видит поле как никто другой, создаёт моменты из ничего",
        "Отличное видение поля, находит партнёров в любой ситуации",
    ],
    "strength": [
        "Физически мощный, его сложно сдвинуть с мяча",
        "Силовой игрок, доминирует в контактной борьбе",
    ],
    "composure": [
        "Хладнокровен под давлением, не теряет голову в решающие моменты",
        "Спокоен и уверен в себе даже в стрессовых ситуациях",
    ],
}

WEAKNESS_TEMPLATES = {
    "pace": [
        "Не хватает скорости, уязвим против быстрых нападающих",
        "Медлителен, может проигрывать забеги за спину",
    ],
    "heading": [
        "Слабая игра головой, не выигрывает верховые дуэли",
        "Проблемы в воздухе — не его стихия",
    ],
    "stamina": [
        "Проблемы с выносливостью, сдаёт к концу матча",
        "Быстро устаёт, нуждается в замене после 70-й минуты",
    ],
    "concentration": [
        "Иногда теряет концентрацию, допускает глупые ошибки",
        "Нестабилен — может провалить матч из-за потери фокуса",
    ],
    "decisions": [
        "Принимает неверные решения под давлением",
        "Слабое принятие решений, часто выбирает неоптимальный вариант",
    ],
    "work_rate": [
        "Не отрабатывает в обороне, ленив без мяча",
        "Низкая работоспособность — не помогает команде в обороне",
    ],
    "marking": [
        "Проблемы с опекой, теряет игроков при стандартах",
        "Слабая персональная опека — нападающие легко от него уходят",
    ],
}

RECOMMENDATION_THRESHOLDS = {
    "A+": 170,  # CA threshold
    "A": 155,
    "B+": 140,
    "B": 125,
    "C+": 110,
    "C": 95,
    "D": 0,
}


class ScoutingCentre:
    """Main scouting system manager."""

    def __init__(self):
        self.scouts: List[ScoutProfile] = []
        self.assignments: List[ScoutAssignment] = []
        self.reports: List[ScoutReport] = []
        self.shortlist: List[int] = []  # player_ids
        self.scouting_budget: float = 5000000.0  # €5M per season (realistic for top club)
        self.budget_spent: float = 0.0
        self._next_id = 1

    def _gen_id(self) -> int:
        self._next_id += 1
        return self._next_id - 1

    # === SCOUT MANAGEMENT ===

    def hire_scout(self, name: str, judging: int = 12, potential: int = 12, 
                   regions: Dict[str, int] = None, wage: int = 5000) -> ScoutProfile:
        """Hire a new scout."""
        scout = ScoutProfile(
            id=self._gen_id(),
            name=name,
            judging_ability=judging,
            judging_potential=potential,
            wage=wage,
            region_knowledge=regions or {},
        )
        self.scouts.append(scout)
        return scout

    def fire_scout(self, scout_id: int) -> bool:
        """Fire a scout. Cancels their active assignments."""
        self.scouts = [s for s in self.scouts if s.id != scout_id]
        for a in self.assignments:
            if a.scout_id == scout_id and a.status == "active":
                a.status = "cancelled"
        return True

    # === ASSIGNMENTS ===

    def create_assignment(
        self,
        scout_id: int,
        assignment_type: str,
        target: str,
        position_filter: str = None,
        age_min: int = None,
        age_max: int = None,
        max_price: int = None,
        duration_weeks: int = 4,
        priority: str = "normal",
    ) -> Optional[ScoutAssignment]:
        """Create a new scouting assignment."""
        scout = next((s for s in self.scouts if s.id == scout_id), None)
        if not scout:
            return None
        
        # Force scout to idle if they have no active assignment
        active_assignments = [a for a in self.assignments if a.scout_id == scout_id and a.status == "active"]
        if not active_assignments:
            scout.status = "idle"
        
        if scout.status != "idle":
            return None

        # Calculate cost
        cost = self._calculate_assignment_cost(duration_weeks, priority, target)
        if self.budget_spent + cost > self.scouting_budget:
            return None  # Over budget

        assignment = ScoutAssignment(
            id=self._gen_id(),
            scout_id=scout_id,
            assignment_type=assignment_type,
            target=target,
            position_filter=position_filter,
            age_min=age_min,
            age_max=age_max,
            max_price=max_price,
            duration_weeks=duration_weeks,
            priority=priority,
            started_at=datetime.now().isoformat(),
        )
        self.assignments.append(assignment)
        scout.status = "assigned"
        scout.current_assignment = {"id": assignment.id, "target": target}
        self.budget_spent += cost

        return assignment

    def _calculate_assignment_cost(self, weeks: int, priority: str, target: str) -> float:
        """Calculate cost based on region, duration, and priority."""
        elite = ["Western Europe", "Central Europe", "South Europe", "South America South", "UK Ireland"]
        prospect = ["Northern Europe", "South America North", "North Africa", "Western Africa", 
                    "Eastern Europe", "North Eastern Europe", "East Asia", "North America", "Oceania"]
        
        if target in elite:
            base_per_week = 50000
        elif target in prospect:
            base_per_week = 80000
        else:
            base_per_week = 120000
        
        cost = base_per_week * weeks
        priority_mult = {"low": 0.7, "normal": 1.0, "high": 1.5, "urgent": 2.5}
        return cost * priority_mult.get(priority, 1.0)

    # === WEEKLY PROCESSING ===

    def process_week(self, all_players: List[Dict]) -> List[ScoutReport]:
        """Process one week of scouting. Called during advance_week."""
        new_reports = []

        for assignment in self.assignments:
            if assignment.status != "active":
                continue

            assignment.weeks_elapsed += 1
            scout = next((s for s in self.scouts if s.id == assignment.scout_id), None)
            if not scout:
                continue

            # Increase region knowledge
            if assignment.assignment_type == "region":
                knowledge_gain = 2 + scout.adaptability // 5
                scout.add_knowledge(assignment.target, knowledge_gain)

            # Generate reports based on progress
            report_chance = self._get_report_chance(scout, assignment)
            if random.random() < report_chance:
                # Find matching players
                candidates = self._find_candidates(assignment, all_players)
                if candidates:
                    player = random.choice(candidates)
                    report = self._generate_report(scout, assignment, player)
                    self.reports.append(report)
                    new_reports.append(report)
                    assignment.reports_generated += 1

            # Check if assignment is complete
            if assignment.weeks_elapsed >= assignment.duration_weeks:
                assignment.status = "completed"
                scout.status = "idle"
                scout.current_assignment = None

        return new_reports

    def _get_report_chance(self, scout: ScoutProfile, assignment: ScoutAssignment) -> float:
        """Probability of generating a report this week."""
        base = 0.3
        # Better scouts find players faster
        base += scout.determination / 100
        # Priority affects speed
        priority_bonus = {"low": -0.1, "normal": 0, "high": 0.1, "urgent": 0.2}
        base += priority_bonus.get(assignment.priority, 0)
        # Region knowledge helps
        if assignment.assignment_type == "region":
            knowledge = scout.get_knowledge(assignment.target)
            base += knowledge / 500  # Up to +0.2
        return min(0.8, max(0.1, base))

    def _find_candidates(self, assignment: ScoutAssignment, all_players: List[Dict]) -> List[Dict]:
        """Find players matching assignment criteria."""
        candidates = []
        for p in all_players:
            # Type filter
            if assignment.assignment_type == "region":
                if p.get("nationality", "").lower() != assignment.target.lower():
                    continue
            elif assignment.assignment_type == "player":
                if str(p.get("id")) != str(assignment.target):
                    continue

            # Position filter
            if assignment.position_filter:
                if assignment.position_filter.lower() not in p.get("position", "").lower():
                    continue

            # Age filter
            age = p.get("age", 25)
            if assignment.age_min and age < assignment.age_min:
                continue
            if assignment.age_max and age > assignment.age_max:
                continue

            candidates.append(p)

        return candidates[:50]  # Limit to prevent huge lists

    # === REPORT GENERATION ===

    def _generate_report(self, scout: ScoutProfile, assignment: ScoutAssignment, player: Dict) -> ScoutReport:
        """Generate a detailed scout report for a player."""
        ca = player.get("ca", 100)
        pa = player.get("pa", 100)

        # Accuracy based on scout skill and region knowledge
        country = player.get("nationality", "Unknown")
        knowledge = scout.get_knowledge(country)
        accuracy = min(95, 40 + scout.judging_ability * 2 + knowledge // 5)

        # Star ratings (with inaccuracy)
        ca_stars = self._ca_to_stars(ca, accuracy)
        pa_stars = self._pa_to_stars(pa, scout.judging_potential, accuracy)

        # Recommendation (age-aware)
        age = player.get("age", 0) or 0
        recommendation = self._get_recommendation(ca, pa, age)

        # Find strengths and weaknesses
        strengths = self._find_strengths(player, accuracy)
        weaknesses = self._find_weaknesses(player, accuracy)

        # Generate summary text
        summary = self._generate_summary_text(player, strengths, weaknesses, recommendation)

        # Reveal attributes (more revealed with higher accuracy)
        revealed = self._reveal_attributes(player, accuracy)

        report = ScoutReport(
            id=self._gen_id(),
            player_id=player.get("id", 0),
            player_name=player.get("name", "Unknown"),
            scout_id=scout.id,
            scout_name=scout.name,
            assignment_id=assignment.id,
            current_ability_stars=ca_stars,
            potential_stars=pa_stars,
            recommendation=recommendation,
            strengths=strengths,
            weaknesses=weaknesses,
            summary_text=summary,
            accuracy_pct=accuracy,
            revealed_attributes=revealed,
            created_at=datetime.now().isoformat(),
        )
        return report

    def _ca_to_stars(self, ca: int, accuracy: int) -> float:
        """Convert CA to star rating with inaccuracy."""
        base_stars = min(5.0, max(0.5, ca / 40))
        # Add noise based on accuracy
        noise = (100 - accuracy) / 100 * random.uniform(-0.5, 0.5)
        return round(min(5.0, max(0.5, base_stars + noise)) * 2) / 2  # Round to 0.5

    def _pa_to_stars(self, pa: int, judging_potential: int, accuracy: int) -> float:
        """Convert PA to star rating."""
        if pa < 0:
            pa = abs(pa)  # Negative PA means "at least this"
        base_stars = min(5.0, max(0.5, pa / 40))
        noise = (20 - judging_potential) / 20 * random.uniform(-1.0, 1.0)
        return round(min(5.0, max(0.5, base_stars + noise)) * 2) / 2

    def _get_recommendation(self, ca: int, pa: int, age: int = 0) -> str:
        """Get letter recommendation based on CA, PA and age.

        Age caps the rating because PA is irrelevant for old players —
        a 40-year-old won't grow into his potential.
        """
        score = ca * 0.6 + abs(pa) * 0.4
        base = "D"
        for grade, threshold in sorted(RECOMMENDATION_THRESHOLDS.items(), key=lambda x: -x[1]):
            if score >= threshold:
                base = grade
                break

        # Order from worst to best
        order = ["D", "C", "C+", "B", "B+", "A", "A+"]
        if age >= 37:
            cap = "C"
        elif age >= 35:
            cap = "B"
        elif age >= 33:
            cap = "B+"
        elif age >= 30:
            cap = "A"
        else:
            cap = "A+"
        try:
            if order.index(base) > order.index(cap):
                return cap
        except ValueError:
            pass
        return base

    def _find_strengths(self, player: Dict, accuracy: int) -> List[str]:
        """Find player's top attributes and generate strength descriptions."""
        attrs = {
            "pace": player.get("pace", 10),
            "dribbling": player.get("dribbling", 10),
            "passing": player.get("passing", 10),
            "finishing": player.get("finishing", 10),
            "tackling": player.get("tackling", 10),
            "heading": player.get("heading", 10),
            "vision": player.get("vision", 10),
            "strength": player.get("strength", 10),
            "composure": player.get("composure", 10),
        }

        # Sort by value, take top 2-3
        sorted_attrs = sorted(attrs.items(), key=lambda x: -x[1])
        strengths = []
        for attr_name, value in sorted_attrs[:3]:
            if value >= 14:
                templates = STRENGTH_TEMPLATES.get(attr_name, [f"Хороший {attr_name}"])
                strengths.append(random.choice(templates))

        return strengths if strengths else ["Сбалансированный игрок без ярко выраженных сильных сторон"]

    def _find_weaknesses(self, player: Dict, accuracy: int) -> List[str]:
        """Find player's weak attributes."""
        attrs = {
            "pace": player.get("pace", 10),
            "heading": player.get("heading", 10),
            "stamina": player.get("stamina", 10),
            "concentration": player.get("concentration", 10),
            "decisions": player.get("decisions", 10),
            "work_rate": player.get("work_rate", 10),
            "marking": player.get("marking", 10),
        }

        sorted_attrs = sorted(attrs.items(), key=lambda x: x[1])
        weaknesses = []
        for attr_name, value in sorted_attrs[:2]:
            if value <= 10:
                templates = WEAKNESS_TEMPLATES.get(attr_name, [f"Слабый {attr_name}"])
                weaknesses.append(random.choice(templates))

        return weaknesses if weaknesses else ["Нет явных слабостей"]

    def _generate_summary_text(self, player: Dict, strengths: List[str], weaknesses: List[str], rec: str) -> str:
        """Generate human-readable summary."""
        name = player.get("name", "Игрок")
        age = player.get("age", 25)
        pos = player.get("position", "")
        club = player.get("club", "")

        text = f"{name}, {age} лет, {pos}"
        if club:
            text += f" ({club})"
        text += ".\n\n"

        text += "Сильные стороны:\n"
        for s in strengths:
            text += f"• {s}\n"

        text += "\nСлабые стороны:\n"
        for w in weaknesses:
            text += f"• {w}\n"

        text += f"\nРекомендация: {rec}"
        return text

    def _reveal_attributes(self, player: Dict, accuracy: int) -> Dict[str, int]:
        """Reveal attributes based on accuracy. Higher accuracy = more revealed."""
        all_attrs = [
            "pace", "acceleration", "stamina", "strength", "agility",
            "passing", "crossing", "dribbling", "finishing", "first_touch",
            "heading", "long_shots", "tackling", "technique", "marking",
            "vision", "composure", "decisions", "anticipation", "positioning",
            "work_rate", "teamwork", "flair", "bravery", "determination",
        ]

        # Number of attributes revealed depends on accuracy
        num_revealed = max(5, accuracy * len(all_attrs) // 100)
        revealed_names = random.sample(all_attrs, min(num_revealed, len(all_attrs)))

        revealed = {}
        # Always reveal CA and wage
        revealed["ca"] = player.get("ca", 100)
        revealed["wage"] = player.get("wage", 0) or 0
        
        for attr in revealed_names:
            real_value = player.get(attr, 10)
            # Add noise based on accuracy
            noise = int((100 - accuracy) / 20 * random.uniform(-2, 2))
            shown_value = max(1, min(20, real_value + noise))
            revealed[attr] = shown_value

        return revealed

    # === SHORTLIST ===

    def add_to_shortlist(self, player_id: int) -> bool:
        if len(self.shortlist) >= 50:
            return False
        if player_id not in self.shortlist:
            self.shortlist.append(player_id)
        return True

    def remove_from_shortlist(self, player_id: int):
        self.shortlist = [p for p in self.shortlist if p != player_id]

    # === BUDGET ===

    def get_budget_status(self) -> Dict[str, Any]:
        return {
            "total_budget": self.scouting_budget,
            "spent": self.budget_spent,
            "remaining": self.scouting_budget - self.budget_spent,
            "scout_wages_weekly": sum(s.wage for s in self.scouts),
            "active_assignments": len([a for a in self.assignments if a.status == "active"]),
        }

    def request_budget_increase(self, amount: float, board_confidence: int) -> Dict[str, Any]:
        """Request budget increase from board."""
        # Higher confidence = more likely to approve
        approval_chance = board_confidence / 100 * 0.7
        if random.random() < approval_chance:
            granted = amount * random.uniform(0.5, 1.0)
            self.scouting_budget += granted
            return {"approved": True, "granted": granted}
        return {"approved": False, "reason": "Board rejected the request"}

    # === KNOWLEDGE MAP ===

    def get_knowledge_map(self) -> Dict[str, int]:
        """Get combined knowledge of all scouts per country."""
        combined = {}
        for scout in self.scouts:
            for country, knowledge in scout.region_knowledge.items():
                combined[country] = max(combined.get(country, 0), knowledge)
        return combined

    # === SERIALIZATION ===

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scouts": [vars(s) for s in self.scouts],
            "assignments": [vars(a) for a in self.assignments],
            "reports": [
                {
                    "id": r.id, "player_id": r.player_id, "player_name": r.player_name,
                    "scout_name": r.scout_name, "current_ability_stars": r.current_ability_stars,
                    "potential_stars": r.potential_stars, "recommendation": r.recommendation,
                    "strengths": r.strengths, "weaknesses": r.weaknesses,
                    "summary_text": r.summary_text, "accuracy_pct": r.accuracy_pct,
                    "revealed_attributes": r.revealed_attributes, "status": r.status,
                    "created_at": r.created_at,
                }
                for r in self.reports
            ],
            "shortlist": self.shortlist,
            "budget": self.scouting_budget,
            "budget_spent": self.budget_spent,
        }
