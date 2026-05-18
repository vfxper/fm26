"""
Tactics Service - Tactic Editor Implementation

This module provides comprehensive tactical management for the football manager game.
It handles formations, player roles, team instructions, tactic presets, match modifiers,
pitch diagram data, player positioning, position compatibility, and in-match adjustments.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


# ============================================================================
# Enums (re-exported from ai_manager for consistency)
# ============================================================================


class TacticMentality(Enum):
    """Team mentality levels - 6 levels"""
    VERY_DEFENSIVE = "Very Defensive"
    DEFENSIVE = "Defensive"
    CAUTIOUS = "Cautious"
    BALANCED = "Balanced"
    ATTACKING = "Attacking"
    VERY_ATTACKING = "Very Attacking"


class PressingIntensity(Enum):
    """Pressing intensity levels - 4 levels"""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    EXTREME = "Extreme"


class DefensiveLineHeight(Enum):
    """Defensive line height - 4 levels"""
    DEEP = "Deep"
    STANDARD = "Standard"
    HIGH = "High"
    VERY_HIGH = "Very High"


class TeamWidth(Enum):
    """Team width configuration - 3 levels"""
    NARROW = "Narrow"
    NORMAL = "Normal"
    WIDE = "Wide"


class TeamTempo(Enum):
    """Team tempo configuration - 3 levels"""
    SLOW = "Slow"
    NORMAL = "Normal"
    FAST = "Fast"


class PositionType(Enum):
    """Position types on the pitch"""
    GK = "GK"
    CB = "CB"
    LB = "LB"
    RB = "RB"
    LWB = "LWB"
    RWB = "RWB"
    DM = "DM"
    CM = "CM"
    LM = "LM"
    RM = "RM"
    AM = "AM"
    LW = "LW"
    RW = "RW"
    ST = "ST"
    CF = "CF"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PositionCoordinate:
    """A position on the pitch with x,y coordinates (0-100 scale)"""
    x: float  # 0=left, 100=right
    y: float  # 0=own goal line, 100=opponent goal line
    position_type: PositionType

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "position_type": self.position_type.value}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionCoordinate":
        return cls(
            x=data["x"],
            y=data["y"],
            position_type=PositionType(data["position_type"]),
        )


@dataclass
class Formation:
    """A formation definition with 11 positions"""
    name: str
    positions: List[PositionCoordinate]  # Exactly 11 positions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "positions": [p.to_dict() for p in self.positions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Formation":
        return cls(
            name=data["name"],
            positions=[PositionCoordinate.from_dict(p) for p in data["positions"]],
        )


@dataclass
class PlayerRole:
    """A role that can be assigned to a position"""
    name: str
    position_type: PositionType
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "position_type": self.position_type.value,
            "description": self.description,
        }


@dataclass
class PlayerPositionAssignment:
    """Assignment of a player to a position in a tactic"""
    player_id: int
    position_index: int  # Index in the formation positions list (0-10)
    role: str  # Role name
    custom_x: Optional[float] = None  # Custom x override
    custom_y: Optional[float] = None  # Custom y override

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "position_index": self.position_index,
            "role": self.role,
            "custom_x": self.custom_x,
            "custom_y": self.custom_y,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerPositionAssignment":
        return cls(
            player_id=data["player_id"],
            position_index=data["position_index"],
            role=data["role"],
            custom_x=data.get("custom_x"),
            custom_y=data.get("custom_y"),
        )


@dataclass
class TacticPreset:
    """Complete tactic preset with all settings"""
    name: str
    formation_name: str
    mentality: TacticMentality = TacticMentality.BALANCED
    pressing: PressingIntensity = PressingIntensity.MEDIUM
    defensive_line: DefensiveLineHeight = DefensiveLineHeight.STANDARD
    width: TeamWidth = TeamWidth.NORMAL
    tempo: TeamTempo = TeamTempo.NORMAL
    player_assignments: List[PlayerPositionAssignment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "formation_name": self.formation_name,
            "mentality": self.mentality.value,
            "pressing": self.pressing.value,
            "defensive_line": self.defensive_line.value,
            "width": self.width.value,
            "tempo": self.tempo.value,
            "player_assignments": [a.to_dict() for a in self.player_assignments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TacticPreset":
        return cls(
            name=data["name"],
            formation_name=data["formation_name"],
            mentality=TacticMentality(data["mentality"]),
            pressing=PressingIntensity(data["pressing"]),
            defensive_line=DefensiveLineHeight(data["defensive_line"]),
            width=TeamWidth(data["width"]),
            tempo=TeamTempo(data["tempo"]),
            player_assignments=[
                PlayerPositionAssignment.from_dict(a)
                for a in data.get("player_assignments", [])
            ],
        )


@dataclass
class MatchModifiers:
    """Modifiers that a tactic applies to match simulation"""
    possession_bonus: float = 0.0  # -0.15 to +0.15
    shot_frequency: float = 1.0  # multiplier 0.7 to 1.4
    defensive_strength: float = 1.0  # multiplier 0.7 to 1.3
    pressing_effectiveness: float = 1.0  # multiplier 0.6 to 1.5
    counter_attack_bonus: float = 0.0  # 0.0 to 0.2
    crossing_frequency: float = 1.0  # multiplier 0.7 to 1.3
    stamina_drain_rate: float = 1.0  # multiplier 0.8 to 1.4
    passing_risk: float = 1.0  # multiplier 0.8 to 1.3
    offside_trap_chance: float = 0.0  # 0.0 to 0.3
    space_behind_defense: float = 0.0  # 0.0 to 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "possession_bonus": self.possession_bonus,
            "shot_frequency": self.shot_frequency,
            "defensive_strength": self.defensive_strength,
            "pressing_effectiveness": self.pressing_effectiveness,
            "counter_attack_bonus": self.counter_attack_bonus,
            "crossing_frequency": self.crossing_frequency,
            "stamina_drain_rate": self.stamina_drain_rate,
            "passing_risk": self.passing_risk,
            "offside_trap_chance": self.offside_trap_chance,
            "space_behind_defense": self.space_behind_defense,
        }


@dataclass
class TacticalAdjustment:
    """An in-match tactical adjustment"""
    adjustment_type: str  # "formation_change", "mentality_shift", "substitution", "pressing_change"
    params: Dict[str, Any] = field(default_factory=dict)
    minute: int = 0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adjustment_type": self.adjustment_type,
            "params": self.params,
            "minute": self.minute,
            "reason": self.reason,
        }


@dataclass
class PositionCompatibility:
    """Result of position compatibility check"""
    is_compatible: bool
    compatibility_score: float  # 0.0 to 1.0
    natural_positions: List[str]
    assigned_position: str
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_compatible": self.is_compatible,
            "compatibility_score": self.compatibility_score,
            "natural_positions": self.natural_positions,
            "assigned_position": self.assigned_position,
            "message": self.message,
        }


# ============================================================================
# Task 18.1: 15 Standard Formations
# ============================================================================

STANDARD_FORMATIONS: Dict[str, Formation] = {
    "4-4-2": Formation(
        name="4-4-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(20, 50, PositionType.LM),
            PositionCoordinate(40, 45, PositionType.CM),
            PositionCoordinate(60, 45, PositionType.CM),
            PositionCoordinate(80, 50, PositionType.RM),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
    "4-3-3": Formation(
        name="4-3-3",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(30, 45, PositionType.CM),
            PositionCoordinate(50, 42, PositionType.CM),
            PositionCoordinate(70, 45, PositionType.CM),
            PositionCoordinate(15, 75, PositionType.LW),
            PositionCoordinate(50, 82, PositionType.ST),
            PositionCoordinate(85, 75, PositionType.RW),
        ],
    ),
    "3-5-2": Formation(
        name="3-5-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(30, 18, PositionType.CB),
            PositionCoordinate(50, 16, PositionType.CB),
            PositionCoordinate(70, 18, PositionType.CB),
            PositionCoordinate(10, 45, PositionType.LWB),
            PositionCoordinate(35, 42, PositionType.CM),
            PositionCoordinate(50, 40, PositionType.CM),
            PositionCoordinate(65, 42, PositionType.CM),
            PositionCoordinate(90, 45, PositionType.RWB),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
    "4-2-3-1": Formation(
        name="4-2-3-1",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(38, 38, PositionType.DM),
            PositionCoordinate(62, 38, PositionType.DM),
            PositionCoordinate(20, 60, PositionType.LW),
            PositionCoordinate(50, 62, PositionType.AM),
            PositionCoordinate(80, 60, PositionType.RW),
            PositionCoordinate(50, 82, PositionType.ST),
        ],
    ),
    "5-3-2": Formation(
        name="5-3-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(10, 25, PositionType.LWB),
            PositionCoordinate(30, 18, PositionType.CB),
            PositionCoordinate(50, 16, PositionType.CB),
            PositionCoordinate(70, 18, PositionType.CB),
            PositionCoordinate(90, 25, PositionType.RWB),
            PositionCoordinate(30, 45, PositionType.CM),
            PositionCoordinate(50, 42, PositionType.CM),
            PositionCoordinate(70, 45, PositionType.CM),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
    "4-1-4-1": Formation(
        name="4-1-4-1",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(50, 35, PositionType.DM),
            PositionCoordinate(15, 55, PositionType.LM),
            PositionCoordinate(38, 52, PositionType.CM),
            PositionCoordinate(62, 52, PositionType.CM),
            PositionCoordinate(85, 55, PositionType.RM),
            PositionCoordinate(50, 82, PositionType.ST),
        ],
    ),
    "4-5-1": Formation(
        name="4-5-1",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(15, 50, PositionType.LM),
            PositionCoordinate(35, 45, PositionType.CM),
            PositionCoordinate(50, 43, PositionType.CM),
            PositionCoordinate(65, 45, PositionType.CM),
            PositionCoordinate(85, 50, PositionType.RM),
            PositionCoordinate(50, 82, PositionType.ST),
        ],
    ),
    "3-4-3": Formation(
        name="3-4-3",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(30, 18, PositionType.CB),
            PositionCoordinate(50, 16, PositionType.CB),
            PositionCoordinate(70, 18, PositionType.CB),
            PositionCoordinate(15, 45, PositionType.LM),
            PositionCoordinate(38, 42, PositionType.CM),
            PositionCoordinate(62, 42, PositionType.CM),
            PositionCoordinate(85, 45, PositionType.RM),
            PositionCoordinate(20, 78, PositionType.LW),
            PositionCoordinate(50, 82, PositionType.ST),
            PositionCoordinate(80, 78, PositionType.RW),
        ],
    ),
    "4-4-1-1": Formation(
        name="4-4-1-1",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(15, 48, PositionType.LM),
            PositionCoordinate(38, 44, PositionType.CM),
            PositionCoordinate(62, 44, PositionType.CM),
            PositionCoordinate(85, 48, PositionType.RM),
            PositionCoordinate(50, 65, PositionType.AM),
            PositionCoordinate(50, 82, PositionType.ST),
        ],
    ),
    "4-3-2-1": Formation(
        name="4-3-2-1",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(30, 40, PositionType.CM),
            PositionCoordinate(50, 38, PositionType.CM),
            PositionCoordinate(70, 40, PositionType.CM),
            PositionCoordinate(35, 62, PositionType.AM),
            PositionCoordinate(65, 62, PositionType.AM),
            PositionCoordinate(50, 82, PositionType.ST),
        ],
    ),
    "5-4-1": Formation(
        name="5-4-1",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(10, 25, PositionType.LWB),
            PositionCoordinate(30, 18, PositionType.CB),
            PositionCoordinate(50, 16, PositionType.CB),
            PositionCoordinate(70, 18, PositionType.CB),
            PositionCoordinate(90, 25, PositionType.RWB),
            PositionCoordinate(20, 48, PositionType.LM),
            PositionCoordinate(40, 45, PositionType.CM),
            PositionCoordinate(60, 45, PositionType.CM),
            PositionCoordinate(80, 48, PositionType.RM),
            PositionCoordinate(50, 82, PositionType.ST),
        ],
    ),
    "4-2-2-2": Formation(
        name="4-2-2-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(38, 38, PositionType.DM),
            PositionCoordinate(62, 38, PositionType.DM),
            PositionCoordinate(35, 58, PositionType.AM),
            PositionCoordinate(65, 58, PositionType.AM),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
    "3-4-1-2": Formation(
        name="3-4-1-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(30, 18, PositionType.CB),
            PositionCoordinate(50, 16, PositionType.CB),
            PositionCoordinate(70, 18, PositionType.CB),
            PositionCoordinate(10, 45, PositionType.LWB),
            PositionCoordinate(38, 42, PositionType.CM),
            PositionCoordinate(62, 42, PositionType.CM),
            PositionCoordinate(90, 45, PositionType.RWB),
            PositionCoordinate(50, 62, PositionType.AM),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
    "4-1-2-1-2": Formation(
        name="4-1-2-1-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(50, 33, PositionType.DM),
            PositionCoordinate(30, 48, PositionType.CM),
            PositionCoordinate(70, 48, PositionType.CM),
            PositionCoordinate(50, 62, PositionType.AM),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
    "4-3-1-2": Formation(
        name="4-3-1-2",
        positions=[
            PositionCoordinate(50, 3, PositionType.GK),
            PositionCoordinate(20, 20, PositionType.LB),
            PositionCoordinate(40, 18, PositionType.CB),
            PositionCoordinate(60, 18, PositionType.CB),
            PositionCoordinate(80, 20, PositionType.RB),
            PositionCoordinate(30, 40, PositionType.CM),
            PositionCoordinate(50, 38, PositionType.CM),
            PositionCoordinate(70, 40, PositionType.CM),
            PositionCoordinate(50, 60, PositionType.AM),
            PositionCoordinate(35, 80, PositionType.ST),
            PositionCoordinate(65, 80, PositionType.ST),
        ],
    ),
}


# ============================================================================
# Task 18.2: Player Role Assignment System
# ============================================================================

# Roles available per position type
POSITION_ROLES: Dict[PositionType, List[PlayerRole]] = {
    PositionType.GK: [
        PlayerRole("Goalkeeper", PositionType.GK, "Standard shot-stopper"),
        PlayerRole("Sweeper Keeper", PositionType.GK, "Comes off the line to sweep up"),
        PlayerRole("Ball-Playing Goalkeeper", PositionType.GK, "Distributes with feet"),
    ],
    PositionType.CB: [
        PlayerRole("Central Defender", PositionType.CB, "Standard centre-back"),
        PlayerRole("Ball-Playing Defender", PositionType.CB, "Builds from the back"),
        PlayerRole("Stopper", PositionType.CB, "Aggressive, steps up to challenge"),
        PlayerRole("Cover", PositionType.CB, "Drops deep to cover space"),
    ],
    PositionType.LB: [
        PlayerRole("Full-Back", PositionType.LB, "Standard defensive full-back"),
        PlayerRole("Wing-Back", PositionType.LB, "Attacks down the flank"),
        PlayerRole("Inverted Full-Back", PositionType.LB, "Tucks inside into midfield"),
    ],
    PositionType.RB: [
        PlayerRole("Full-Back", PositionType.RB, "Standard defensive full-back"),
        PlayerRole("Wing-Back", PositionType.RB, "Attacks down the flank"),
        PlayerRole("Inverted Full-Back", PositionType.RB, "Tucks inside into midfield"),
    ],
    PositionType.LWB: [
        PlayerRole("Wing-Back", PositionType.LWB, "Attacks and defends the flank"),
        PlayerRole("Complete Wing-Back", PositionType.LWB, "All-round flank player"),
    ],
    PositionType.RWB: [
        PlayerRole("Wing-Back", PositionType.RWB, "Attacks and defends the flank"),
        PlayerRole("Complete Wing-Back", PositionType.RWB, "All-round flank player"),
    ],
    PositionType.DM: [
        PlayerRole("Defensive Midfielder", PositionType.DM, "Shields the back line"),
        PlayerRole("Deep-Lying Playmaker", PositionType.DM, "Dictates play from deep"),
        PlayerRole("Anchor Man", PositionType.DM, "Stays in position, breaks up play"),
        PlayerRole("Half-Back", PositionType.DM, "Drops between centre-backs"),
    ],
    PositionType.CM: [
        PlayerRole("Central Midfielder", PositionType.CM, "Balanced box-to-box role"),
        PlayerRole("Box-to-Box Midfielder", PositionType.CM, "Covers full pitch"),
        PlayerRole("Advanced Playmaker", PositionType.CM, "Creates from central areas"),
        PlayerRole("Mezzala", PositionType.CM, "Drifts into half-spaces"),
        PlayerRole("Carrilero", PositionType.CM, "Shuttles between flanks"),
    ],
    PositionType.LM: [
        PlayerRole("Wide Midfielder", PositionType.LM, "Standard wide player"),
        PlayerRole("Winger", PositionType.LM, "Hugs the touchline"),
        PlayerRole("Inside Forward", PositionType.LM, "Cuts inside to shoot"),
    ],
    PositionType.RM: [
        PlayerRole("Wide Midfielder", PositionType.RM, "Standard wide player"),
        PlayerRole("Winger", PositionType.RM, "Hugs the touchline"),
        PlayerRole("Inside Forward", PositionType.RM, "Cuts inside to shoot"),
    ],
    PositionType.AM: [
        PlayerRole("Attacking Midfielder", PositionType.AM, "Creates chances centrally"),
        PlayerRole("Trequartista", PositionType.AM, "Free-roaming playmaker"),
        PlayerRole("Shadow Striker", PositionType.AM, "Lurks behind the striker"),
        PlayerRole("Enganche", PositionType.AM, "Classic number 10"),
    ],
    PositionType.LW: [
        PlayerRole("Winger", PositionType.LW, "Stretches play wide"),
        PlayerRole("Inside Forward", PositionType.LW, "Cuts inside to shoot"),
        PlayerRole("Inverted Winger", PositionType.LW, "Moves centrally with the ball"),
        PlayerRole("Raumdeuter", PositionType.LW, "Exploits space in the box"),
    ],
    PositionType.RW: [
        PlayerRole("Winger", PositionType.RW, "Stretches play wide"),
        PlayerRole("Inside Forward", PositionType.RW, "Cuts inside to shoot"),
        PlayerRole("Inverted Winger", PositionType.RW, "Moves centrally with the ball"),
        PlayerRole("Raumdeuter", PositionType.RW, "Exploits space in the box"),
    ],
    PositionType.ST: [
        PlayerRole("Poacher", PositionType.ST, "Stays central, finishes chances"),
        PlayerRole("Target Man", PositionType.ST, "Holds up play, wins headers"),
        PlayerRole("Complete Forward", PositionType.ST, "Does everything in attack"),
        PlayerRole("Advanced Forward", PositionType.ST, "Presses and runs in behind"),
        PlayerRole("Deep-Lying Forward", PositionType.ST, "Drops deep to link play"),
        PlayerRole("Pressing Forward", PositionType.ST, "Leads the press from the front"),
    ],
    PositionType.CF: [
        PlayerRole("False Nine", PositionType.CF, "Drops deep to create overloads"),
        PlayerRole("Complete Forward", PositionType.CF, "All-round attacking threat"),
        PlayerRole("Trequartista", PositionType.CF, "Free-roaming creator"),
    ],
}


# ============================================================================
# Task 18.12: Position Compatibility Mapping
# ============================================================================

# Maps position strings from Player_DB to compatible PositionTypes
# Player positions in the DB look like "AM/ST RL", "D C", "GK", "M RC", etc.
POSITION_COMPATIBILITY_MAP: Dict[str, List[PositionType]] = {
    "GK": [PositionType.GK],
    "D C": [PositionType.CB],
    "D L": [PositionType.LB, PositionType.LWB],
    "D R": [PositionType.RB, PositionType.RWB],
    "D LC": [PositionType.CB, PositionType.LB],
    "D RC": [PositionType.CB, PositionType.RB],
    "D RLC": [PositionType.CB, PositionType.LB, PositionType.RB],
    "DM C": [PositionType.DM, PositionType.CM],
    "DM L": [PositionType.DM, PositionType.LM],
    "DM R": [PositionType.DM, PositionType.RM],
    "M C": [PositionType.CM, PositionType.DM],
    "M L": [PositionType.LM, PositionType.LW],
    "M R": [PositionType.RM, PositionType.RW],
    "M LC": [PositionType.CM, PositionType.LM],
    "M RC": [PositionType.CM, PositionType.RM],
    "M RL": [PositionType.LM, PositionType.RM, PositionType.LW, PositionType.RW],
    "M RLC": [PositionType.CM, PositionType.LM, PositionType.RM],
    "AM C": [PositionType.AM, PositionType.CM, PositionType.CF],
    "AM L": [PositionType.LW, PositionType.LM, PositionType.AM],
    "AM R": [PositionType.RW, PositionType.RM, PositionType.AM],
    "AM RL": [PositionType.LW, PositionType.RW, PositionType.AM],
    "AM RLC": [PositionType.AM, PositionType.LW, PositionType.RW, PositionType.CM],
    "AM LC": [PositionType.AM, PositionType.LW, PositionType.CM],
    "AM RC": [PositionType.AM, PositionType.RW, PositionType.CM],
    "ST C": [PositionType.ST, PositionType.CF],
    "ST": [PositionType.ST, PositionType.CF],
}

# Adjacency for partial compatibility (can play but not natural)
POSITION_ADJACENCY: Dict[PositionType, List[PositionType]] = {
    PositionType.GK: [],
    PositionType.CB: [PositionType.DM],
    PositionType.LB: [PositionType.LWB, PositionType.LM],
    PositionType.RB: [PositionType.RWB, PositionType.RM],
    PositionType.LWB: [PositionType.LB, PositionType.LM],
    PositionType.RWB: [PositionType.RB, PositionType.RM],
    PositionType.DM: [PositionType.CM, PositionType.CB],
    PositionType.CM: [PositionType.DM, PositionType.AM],
    PositionType.LM: [PositionType.LW, PositionType.LB, PositionType.LWB],
    PositionType.RM: [PositionType.RW, PositionType.RB, PositionType.RWB],
    PositionType.AM: [PositionType.CM, PositionType.CF, PositionType.ST],
    PositionType.LW: [PositionType.LM, PositionType.AM, PositionType.ST],
    PositionType.RW: [PositionType.RM, PositionType.AM, PositionType.ST],
    PositionType.ST: [PositionType.CF, PositionType.AM],
    PositionType.CF: [PositionType.ST, PositionType.AM],
}


# ============================================================================
# TacticsService Class
# ============================================================================


class TacticsService:
    """
    Comprehensive tactics management service.

    Handles formations, player roles, team instructions, tactic presets,
    match modifiers, pitch diagram data, player positioning, position
    compatibility validation, and in-match tactical adjustments.
    """

    MAX_PRESETS_PER_CAREER = 5

    def __init__(self) -> None:
        self._formations = STANDARD_FORMATIONS
        self._position_roles = POSITION_ROLES

    # ========================================================================
    # Task 18.1: Formation Management
    # ========================================================================

    def get_all_formations(self) -> List[Formation]:
        """Return all 15 standard formations."""
        return list(self._formations.values())

    def get_formation(self, name: str) -> Optional[Formation]:
        """Get a specific formation by name."""
        return self._formations.get(name)

    def get_formation_names(self) -> List[str]:
        """Return list of all available formation names."""
        return list(self._formations.keys())

    # ========================================================================
    # Task 18.2: Player Role Assignment
    # ========================================================================

    def get_roles_for_position(self, position_type: PositionType) -> List[PlayerRole]:
        """Get all available roles for a given position type."""
        return self._position_roles.get(position_type, [])

    def get_roles_for_formation_position(
        self, formation_name: str, position_index: int
    ) -> List[PlayerRole]:
        """Get available roles for a specific position in a formation."""
        formation = self.get_formation(formation_name)
        if not formation:
            return []
        if position_index < 0 or position_index >= len(formation.positions):
            return []
        position = formation.positions[position_index]
        return self.get_roles_for_position(position.position_type)

    def assign_role(
        self, preset: TacticPreset, position_index: int, role_name: str
    ) -> bool:
        """
        Assign a role to a position in the tactic preset.
        Returns True if the role is valid for that position.
        """
        formation = self.get_formation(preset.formation_name)
        if not formation:
            return False
        if position_index < 0 or position_index >= len(formation.positions):
            return False

        position_type = formation.positions[position_index].position_type
        valid_roles = [r.name for r in self.get_roles_for_position(position_type)]
        if role_name not in valid_roles:
            return False

        # Update or create assignment
        for assignment in preset.player_assignments:
            if assignment.position_index == position_index:
                assignment.role = role_name
                return True

        # No existing assignment for this position, nothing to update role on
        # Role will be set when a player is assigned
        return True

    # ========================================================================
    # Task 18.3: Team Mentality Configuration (6 levels)
    # ========================================================================

    def get_mentality_levels(self) -> List[TacticMentality]:
        """Return all 6 mentality levels."""
        return list(TacticMentality)

    def set_mentality(self, preset: TacticPreset, mentality: TacticMentality) -> None:
        """Set the team mentality on a tactic preset."""
        preset.mentality = mentality

    # ========================================================================
    # Task 18.4: Pressing Intensity Settings (4 levels)
    # ========================================================================

    def get_pressing_levels(self) -> List[PressingIntensity]:
        """Return all 4 pressing intensity levels."""
        return list(PressingIntensity)

    def set_pressing(self, preset: TacticPreset, pressing: PressingIntensity) -> None:
        """Set the pressing intensity on a tactic preset."""
        preset.pressing = pressing

    # ========================================================================
    # Task 18.5: Defensive Line Height Configuration (4 levels)
    # ========================================================================

    def get_defensive_line_levels(self) -> List[DefensiveLineHeight]:
        """Return all 4 defensive line height levels."""
        return list(DefensiveLineHeight)

    def set_defensive_line(
        self, preset: TacticPreset, line_height: DefensiveLineHeight
    ) -> None:
        """Set the defensive line height on a tactic preset."""
        preset.defensive_line = line_height

    # ========================================================================
    # Task 18.6: Width Configuration (3 levels)
    # ========================================================================

    def get_width_levels(self) -> List[TeamWidth]:
        """Return all 3 width levels."""
        return list(TeamWidth)

    def set_width(self, preset: TacticPreset, width: TeamWidth) -> None:
        """Set the team width on a tactic preset."""
        preset.width = width

    # ========================================================================
    # Task 18.7: Tempo Configuration (3 levels)
    # ========================================================================

    def get_tempo_levels(self) -> List[TeamTempo]:
        """Return all 3 tempo levels."""
        return list(TeamTempo)

    def set_tempo(self, preset: TacticPreset, tempo: TeamTempo) -> None:
        """Set the team tempo on a tactic preset."""
        preset.tempo = tempo


    # ========================================================================
    # Task 18.8: Tactic Preset Storage (up to 5 presets)
    # ========================================================================

    def create_preset(
        self,
        name: str,
        formation_name: str,
        existing_presets: List[TacticPreset],
    ) -> Optional[TacticPreset]:
        """
        Create a new tactic preset. Returns None if max presets reached
        or formation is invalid.
        """
        if len(existing_presets) >= self.MAX_PRESETS_PER_CAREER:
            logger.warning(
                "Cannot create preset: max %d presets reached",
                self.MAX_PRESETS_PER_CAREER,
            )
            return None

        if formation_name not in self._formations:
            logger.warning("Invalid formation name: %s", formation_name)
            return None

        preset = TacticPreset(name=name, formation_name=formation_name)
        return preset

    def delete_preset(
        self, preset_name: str, existing_presets: List[TacticPreset]
    ) -> List[TacticPreset]:
        """Delete a preset by name. Returns updated list."""
        return [p for p in existing_presets if p.name != preset_name]

    def rename_preset(self, preset: TacticPreset, new_name: str) -> None:
        """Rename a tactic preset."""
        preset.name = new_name

    def serialize_presets(self, presets: List[TacticPreset]) -> List[Dict[str, Any]]:
        """Serialize presets list for storage (e.g., JSON in Career model)."""
        return [p.to_dict() for p in presets]

    def deserialize_presets(self, data: List[Dict[str, Any]]) -> List[TacticPreset]:
        """Deserialize presets from stored data."""
        return [TacticPreset.from_dict(d) for d in data]

    # ========================================================================
    # Task 18.9: Tactic Application in Match Simulation
    # ========================================================================

    def get_tactic_match_modifiers(self, tactic: TacticPreset) -> MatchModifiers:
        """
        Calculate match simulation modifiers based on the tactic configuration.

        Returns MatchModifiers that affect possession, shots, defense, etc.
        """
        modifiers = MatchModifiers()

        # --- Mentality modifiers ---
        mentality_map = {
            TacticMentality.VERY_DEFENSIVE: {
                "possession_bonus": -0.05,
                "shot_frequency": 0.7,
                "defensive_strength": 1.3,
                "counter_attack_bonus": 0.15,
            },
            TacticMentality.DEFENSIVE: {
                "possession_bonus": -0.03,
                "shot_frequency": 0.8,
                "defensive_strength": 1.2,
                "counter_attack_bonus": 0.10,
            },
            TacticMentality.CAUTIOUS: {
                "possession_bonus": 0.0,
                "shot_frequency": 0.9,
                "defensive_strength": 1.1,
                "counter_attack_bonus": 0.05,
            },
            TacticMentality.BALANCED: {
                "possession_bonus": 0.0,
                "shot_frequency": 1.0,
                "defensive_strength": 1.0,
                "counter_attack_bonus": 0.0,
            },
            TacticMentality.ATTACKING: {
                "possession_bonus": 0.05,
                "shot_frequency": 1.2,
                "defensive_strength": 0.85,
                "counter_attack_bonus": 0.0,
            },
            TacticMentality.VERY_ATTACKING: {
                "possession_bonus": 0.10,
                "shot_frequency": 1.4,
                "defensive_strength": 0.7,
                "counter_attack_bonus": 0.0,
            },
        }
        m_mods = mentality_map.get(tactic.mentality, {})
        modifiers.possession_bonus = m_mods.get("possession_bonus", 0.0)
        modifiers.shot_frequency = m_mods.get("shot_frequency", 1.0)
        modifiers.defensive_strength = m_mods.get("defensive_strength", 1.0)
        modifiers.counter_attack_bonus = m_mods.get("counter_attack_bonus", 0.0)

        # --- Pressing modifiers ---
        pressing_map = {
            PressingIntensity.LOW: {
                "pressing_effectiveness": 0.7,
                "stamina_drain_rate": 0.85,
            },
            PressingIntensity.MEDIUM: {
                "pressing_effectiveness": 1.0,
                "stamina_drain_rate": 1.0,
            },
            PressingIntensity.HIGH: {
                "pressing_effectiveness": 1.25,
                "stamina_drain_rate": 1.2,
            },
            PressingIntensity.EXTREME: {
                "pressing_effectiveness": 1.5,
                "stamina_drain_rate": 1.4,
            },
        }
        p_mods = pressing_map.get(tactic.pressing, {})
        modifiers.pressing_effectiveness = p_mods.get("pressing_effectiveness", 1.0)
        modifiers.stamina_drain_rate = p_mods.get("stamina_drain_rate", 1.0)

        # --- Defensive line modifiers ---
        line_map = {
            DefensiveLineHeight.DEEP: {
                "offside_trap_chance": 0.0,
                "space_behind_defense": 0.05,
            },
            DefensiveLineHeight.STANDARD: {
                "offside_trap_chance": 0.05,
                "space_behind_defense": 0.10,
            },
            DefensiveLineHeight.HIGH: {
                "offside_trap_chance": 0.15,
                "space_behind_defense": 0.20,
            },
            DefensiveLineHeight.VERY_HIGH: {
                "offside_trap_chance": 0.30,
                "space_behind_defense": 0.30,
            },
        }
        l_mods = line_map.get(tactic.defensive_line, {})
        modifiers.offside_trap_chance = l_mods.get("offside_trap_chance", 0.0)
        modifiers.space_behind_defense = l_mods.get("space_behind_defense", 0.0)

        # --- Width modifiers ---
        width_map = {
            TeamWidth.NARROW: {"crossing_frequency": 0.7},
            TeamWidth.NORMAL: {"crossing_frequency": 1.0},
            TeamWidth.WIDE: {"crossing_frequency": 1.3},
        }
        w_mods = width_map.get(tactic.width, {})
        modifiers.crossing_frequency = w_mods.get("crossing_frequency", 1.0)

        # --- Tempo modifiers ---
        tempo_map = {
            TeamTempo.SLOW: {"passing_risk": 0.8},
            TeamTempo.NORMAL: {"passing_risk": 1.0},
            TeamTempo.FAST: {"passing_risk": 1.3},
        }
        t_mods = tempo_map.get(tactic.tempo, {})
        modifiers.passing_risk = t_mods.get("passing_risk", 1.0)

        return modifiers


    # ========================================================================
    # Task 18.10: Visual Pitch Diagram Display
    # ========================================================================

    def get_pitch_diagram_data(
        self, tactic: TacticPreset
    ) -> Dict[str, Any]:
        """
        Return position coordinates and metadata for rendering a pitch diagram.

        Returns a dict with:
        - formation_name: str
        - positions: list of {x, y, position_type, player_id, role}
        - pitch_bounds: {width: 100, height: 100}
        """
        formation = self.get_formation(tactic.formation_name)
        if not formation:
            return {"formation_name": "", "positions": [], "pitch_bounds": {"width": 100, "height": 100}}

        # Build position data with player assignments
        positions_data = []
        for idx, pos in enumerate(formation.positions):
            pos_data: Dict[str, Any] = {
                "index": idx,
                "x": pos.x,
                "y": pos.y,
                "position_type": pos.position_type.value,
                "player_id": None,
                "role": None,
            }

            # Check for custom position overrides and player assignments
            for assignment in tactic.player_assignments:
                if assignment.position_index == idx:
                    pos_data["player_id"] = assignment.player_id
                    pos_data["role"] = assignment.role
                    if assignment.custom_x is not None:
                        pos_data["x"] = assignment.custom_x
                    if assignment.custom_y is not None:
                        pos_data["y"] = assignment.custom_y
                    break

            positions_data.append(pos_data)

        return {
            "formation_name": tactic.formation_name,
            "positions": positions_data,
            "pitch_bounds": {"width": 100, "height": 100},
        }

    # ========================================================================
    # Task 18.11: Drag-and-Drop Player Positioning
    # ========================================================================

    def set_player_position(
        self,
        tactic: TacticPreset,
        player_id: int,
        position_index: int,
        x: Optional[float] = None,
        y: Optional[float] = None,
        role: Optional[str] = None,
    ) -> bool:
        """
        Set or update a player's position in the tactic.

        Args:
            tactic: The tactic preset to modify
            player_id: The player's ID
            position_index: Index in the formation (0-10)
            x: Optional custom x coordinate (0-100)
            y: Optional custom y coordinate (0-100)
            role: Optional role name

        Returns:
            True if successful, False if invalid parameters
        """
        formation = self.get_formation(tactic.formation_name)
        if not formation:
            return False
        if position_index < 0 or position_index >= len(formation.positions):
            return False

        # Validate coordinates if provided
        if x is not None and (x < 0 or x > 100):
            return False
        if y is not None and (y < 0 or y > 100):
            return False

        # Validate role if provided
        if role is not None:
            position_type = formation.positions[position_index].position_type
            valid_roles = [r.name for r in self.get_roles_for_position(position_type)]
            if role not in valid_roles:
                return False

        # Remove any existing assignment for this player or position
        tactic.player_assignments = [
            a
            for a in tactic.player_assignments
            if a.player_id != player_id and a.position_index != position_index
        ]

        # Determine default role if not provided
        if role is None:
            position_type = formation.positions[position_index].position_type
            roles = self.get_roles_for_position(position_type)
            role = roles[0].name if roles else ""

        # Add new assignment
        assignment = PlayerPositionAssignment(
            player_id=player_id,
            position_index=position_index,
            role=role,
            custom_x=x,
            custom_y=y,
        )
        tactic.player_assignments.append(assignment)
        return True

    def move_player_position(
        self, tactic: TacticPreset, player_id: int, new_x: float, new_y: float
    ) -> bool:
        """
        Move a player to a new custom position (drag-and-drop).

        Args:
            tactic: The tactic preset to modify
            player_id: The player's ID
            new_x: New x coordinate (0-100)
            new_y: New y coordinate (0-100)

        Returns:
            True if successful, False if player not found or invalid coords
        """
        if new_x < 0 or new_x > 100 or new_y < 0 or new_y > 100:
            return False

        for assignment in tactic.player_assignments:
            if assignment.player_id == player_id:
                assignment.custom_x = new_x
                assignment.custom_y = new_y
                return True

        return False

    def reset_player_position(self, tactic: TacticPreset, player_id: int) -> bool:
        """Reset a player's position to the formation default."""
        for assignment in tactic.player_assignments:
            if assignment.player_id == player_id:
                assignment.custom_x = None
                assignment.custom_y = None
                return True
        return False


    # ========================================================================
    # Task 18.12: Position Compatibility Validation
    # ========================================================================

    def validate_position_compatibility(
        self,
        player_position_str: str,
        target_position_type: PositionType,
    ) -> PositionCompatibility:
        """
        Check if a player's natural positions are compatible with the assigned position.

        Args:
            player_position_str: The player's position string from Player_DB
                                 (e.g., "AM/ST RL", "D C", "GK", "M RC")
            target_position_type: The position type being assigned

        Returns:
            PositionCompatibility with score and details
        """
        natural_positions = self._parse_player_positions(player_position_str)

        # Check direct compatibility
        if target_position_type in natural_positions:
            return PositionCompatibility(
                is_compatible=True,
                compatibility_score=1.0,
                natural_positions=[p.value for p in natural_positions],
                assigned_position=target_position_type.value,
                message="Natural position",
            )

        # Check adjacent compatibility
        for nat_pos in natural_positions:
            adjacent = POSITION_ADJACENCY.get(nat_pos, [])
            if target_position_type in adjacent:
                return PositionCompatibility(
                    is_compatible=True,
                    compatibility_score=0.7,
                    natural_positions=[p.value for p in natural_positions],
                    assigned_position=target_position_type.value,
                    message="Can play this position with reduced effectiveness",
                )

        # Check secondary adjacency (two steps away)
        for nat_pos in natural_positions:
            adjacent = POSITION_ADJACENCY.get(nat_pos, [])
            for adj_pos in adjacent:
                secondary = POSITION_ADJACENCY.get(adj_pos, [])
                if target_position_type in secondary:
                    return PositionCompatibility(
                        is_compatible=True,
                        compatibility_score=0.4,
                        natural_positions=[p.value for p in natural_positions],
                        assigned_position=target_position_type.value,
                        message="Unfamiliar position - significant effectiveness penalty",
                    )

        # Incompatible
        return PositionCompatibility(
            is_compatible=False,
            compatibility_score=0.0,
            natural_positions=[p.value for p in natural_positions],
            assigned_position=target_position_type.value,
            message="Incompatible position - player cannot play here effectively",
        )

    def _parse_player_positions(self, position_str: str) -> List[PositionType]:
        """
        Parse a player position string into a list of compatible PositionTypes.

        Examples:
            "GK" -> [GK]
            "D C" -> [CB]
            "AM/ST RL" -> [LW, RW, AM, ST, CF]
            "D/DM C" -> [CB, DM, CM]
            "M RL" -> [LM, RM, LW, RW]
        """
        if not position_str:
            return []

        result: List[PositionType] = []
        position_str = position_str.strip()

        # Split by "/" for multi-line positions (e.g., "AM/ST RL", "D/DM C")
        parts = position_str.split("/")

        # The last part contains the side indicator (C, L, R, RL, RLC)
        # e.g., "AM/ST RL" -> parts = ["AM", "ST RL"]
        # e.g., "D C" -> parts = ["D C"]
        if len(parts) == 1:
            # Simple position like "D C", "GK", "M RL"
            key = position_str
            if key in POSITION_COMPATIBILITY_MAP:
                result.extend(POSITION_COMPATIBILITY_MAP[key])
            else:
                # Try to parse generically
                result.extend(self._generic_position_parse(position_str))
        else:
            # Multi-position like "AM/ST RL" or "D/DM C"
            # Extract the side from the last part
            last_part = parts[-1]
            side = ""
            base_last = last_part

            # Check if last part has a space separating position from side
            if " " in last_part:
                base_last, side = last_part.rsplit(" ", 1)
            else:
                # No side indicator in last part, check if it's just a position
                base_last = last_part
                side = ""

            # Process each position prefix with the side
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # Last part - use base_last
                    pos_key = f"{base_last} {side}" if side else base_last
                else:
                    # Earlier parts - combine with side
                    pos_key = f"{part} {side}" if side else part

                if pos_key in POSITION_COMPATIBILITY_MAP:
                    for pt in POSITION_COMPATIBILITY_MAP[pos_key]:
                        if pt not in result:
                            result.append(pt)
                else:
                    parsed = self._generic_position_parse(pos_key)
                    for pt in parsed:
                        if pt not in result:
                            result.append(pt)

        return result

    def _generic_position_parse(self, pos_str: str) -> List[PositionType]:
        """Fallback parser for position strings not in the map."""
        result: List[PositionType] = []
        pos_str = pos_str.strip().upper()

        if "GK" in pos_str:
            result.append(PositionType.GK)
        if "ST" in pos_str:
            result.append(PositionType.ST)
            result.append(PositionType.CF)

        # Check for position base + side
        has_left = "L" in pos_str.split(" ")[-1] if " " in pos_str else False
        has_right = "R" in pos_str.split(" ")[-1] if " " in pos_str else False
        has_center = "C" in pos_str.split(" ")[-1] if " " in pos_str else False

        base = pos_str.split(" ")[0] if " " in pos_str else pos_str

        if base == "D":
            if has_center:
                result.append(PositionType.CB)
            if has_left:
                result.append(PositionType.LB)
            if has_right:
                result.append(PositionType.RB)
            if not (has_center or has_left or has_right):
                result.append(PositionType.CB)
        elif base == "DM":
            if has_center:
                result.append(PositionType.DM)
                result.append(PositionType.CM)
            if has_left:
                result.append(PositionType.DM)
                result.append(PositionType.LM)
            if has_right:
                result.append(PositionType.DM)
                result.append(PositionType.RM)
            if not (has_center or has_left or has_right):
                result.append(PositionType.DM)
        elif base == "M":
            if has_center:
                result.append(PositionType.CM)
            if has_left:
                result.append(PositionType.LM)
            if has_right:
                result.append(PositionType.RM)
            if not (has_center or has_left or has_right):
                result.append(PositionType.CM)
        elif base == "AM":
            if has_center:
                result.append(PositionType.AM)
            if has_left:
                result.append(PositionType.LW)
            if has_right:
                result.append(PositionType.RW)
            if not (has_center or has_left or has_right):
                result.append(PositionType.AM)

        return result


    # ========================================================================
    # Task 18.13: In-Match Tactical Adjustments
    # ========================================================================

    def apply_in_match_adjustment(
        self,
        tactic: TacticPreset,
        adjustment_type: str,
        params: Dict[str, Any],
        minute: int = 0,
    ) -> Optional[TacticalAdjustment]:
        """
        Apply an in-match tactical adjustment.

        Supported adjustment types:
        - "formation_change": Change formation mid-match
            params: {"new_formation": "4-3-3"}
        - "mentality_shift": Change team mentality
            params: {"new_mentality": "Attacking"}
        - "pressing_change": Change pressing intensity
            params: {"new_pressing": "High"}
        - "defensive_line_change": Change defensive line height
            params: {"new_line": "Deep"}
        - "width_change": Change team width
            params: {"new_width": "Wide"}
        - "tempo_change": Change team tempo
            params: {"new_tempo": "Fast"}
        - "substitution": Make a substitution
            params: {"player_out_id": 1, "player_in_id": 2, "position_index": 3, "role": "Poacher"}

        Args:
            tactic: The active tactic preset to modify
            adjustment_type: Type of adjustment
            params: Parameters for the adjustment
            minute: Match minute when adjustment is applied

        Returns:
            TacticalAdjustment if successful, None if invalid
        """
        adjustment = TacticalAdjustment(
            adjustment_type=adjustment_type,
            params=params,
            minute=minute,
        )

        if adjustment_type == "formation_change":
            new_formation = params.get("new_formation", "")
            if new_formation not in self._formations:
                logger.warning("Invalid formation for in-match change: %s", new_formation)
                return None
            tactic.formation_name = new_formation
            # Clear custom positions as formation changed
            for assignment in tactic.player_assignments:
                assignment.custom_x = None
                assignment.custom_y = None
            adjustment.reason = f"Formation changed to {new_formation}"

        elif adjustment_type == "mentality_shift":
            new_mentality_str = params.get("new_mentality", "")
            try:
                new_mentality = TacticMentality(new_mentality_str)
                tactic.mentality = new_mentality
                adjustment.reason = f"Mentality shifted to {new_mentality_str}"
            except ValueError:
                logger.warning("Invalid mentality: %s", new_mentality_str)
                return None

        elif adjustment_type == "pressing_change":
            new_pressing_str = params.get("new_pressing", "")
            try:
                new_pressing = PressingIntensity(new_pressing_str)
                tactic.pressing = new_pressing
                adjustment.reason = f"Pressing changed to {new_pressing_str}"
            except ValueError:
                logger.warning("Invalid pressing: %s", new_pressing_str)
                return None

        elif adjustment_type == "defensive_line_change":
            new_line_str = params.get("new_line", "")
            try:
                new_line = DefensiveLineHeight(new_line_str)
                tactic.defensive_line = new_line
                adjustment.reason = f"Defensive line changed to {new_line_str}"
            except ValueError:
                logger.warning("Invalid defensive line: %s", new_line_str)
                return None

        elif adjustment_type == "width_change":
            new_width_str = params.get("new_width", "")
            try:
                new_width = TeamWidth(new_width_str)
                tactic.width = new_width
                adjustment.reason = f"Width changed to {new_width_str}"
            except ValueError:
                logger.warning("Invalid width: %s", new_width_str)
                return None

        elif adjustment_type == "tempo_change":
            new_tempo_str = params.get("new_tempo", "")
            try:
                new_tempo = TeamTempo(new_tempo_str)
                tactic.tempo = new_tempo
                adjustment.reason = f"Tempo changed to {new_tempo_str}"
            except ValueError:
                logger.warning("Invalid tempo: %s", new_tempo_str)
                return None

        elif adjustment_type == "substitution":
            player_out_id = params.get("player_out_id")
            player_in_id = params.get("player_in_id")
            position_index = params.get("position_index")
            role = params.get("role")

            if player_out_id is None or player_in_id is None:
                logger.warning("Substitution requires player_out_id and player_in_id")
                return None

            # Find the outgoing player's assignment
            out_assignment = None
            for a in tactic.player_assignments:
                if a.player_id == player_out_id:
                    out_assignment = a
                    break

            if out_assignment:
                # Replace player in the same position
                out_assignment.player_id = player_in_id
                if role:
                    out_assignment.role = role
                if position_index is not None:
                    out_assignment.position_index = position_index
            elif position_index is not None:
                # Player wasn't assigned, create new assignment
                self.set_player_position(
                    tactic, player_in_id, position_index, role=role
                )

            adjustment.reason = f"Substitution: player {player_out_id} off, {player_in_id} on"

        else:
            logger.warning("Unknown adjustment type: %s", adjustment_type)
            return None

        logger.info(
            "In-match adjustment at minute %d: %s", minute, adjustment.reason
        )
        return adjustment

    def get_available_adjustments(self) -> List[str]:
        """Return list of available in-match adjustment types."""
        return [
            "formation_change",
            "mentality_shift",
            "pressing_change",
            "defensive_line_change",
            "width_change",
            "tempo_change",
            "substitution",
        ]
