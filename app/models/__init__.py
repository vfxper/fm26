"""
Data Models - SQLAlchemy ORM models
"""

from app.models.user import User
from app.models.player import Player
from app.models.club import Club
from app.models.career import Career
from app.models.squad_player import SquadPlayer, SquadStatus
from app.models.match import Match, MatchStatus, WeatherCondition, PitchCondition
from app.models.match_event import MatchEvent, EventType, TeamSide

# Additional models will be imported here as they are created in subsequent tasks
from app.models.transfer import Transfer, TransferType, TransferStatus
from app.models.injury import Injury, InjurySeverity, InjuryStatus
from app.models.staff import Staff, StaffRole
from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.scouting_assignment import ScoutingAssignment, AssignmentType, AssignmentStatus
from app.models.media_event import MediaEvent, MediaEventType, MediaEventStatus
from app.models.competition import Competition, CompetitionType
from app.models.fixture import Fixture, FixtureStatus
from app.models.financial_transaction import (
    FinancialTransaction,
    TransactionType,
    IncomeCategory,
    ExpenditureCategory,
)
from app.models.season_deficit_record import SeasonDeficitRecord
from app.models.sponsorship_deal import SponsorshipDeal
from app.models.infrastructure_upgrade import InfrastructureUpgrade, UpgradeStatus
from app.models.scouting_shortlist import ScoutingShortlist

__all__ = [
    "User",
    "Player",
    "Club",
    "Career",
    "SquadPlayer",
    "SquadStatus",
    "Match",
    "MatchStatus",
    "WeatherCondition",
    "PitchCondition",
    "MatchEvent",
    "EventType",
    "TeamSide",
    "Transfer",
    "TransferType",
    "TransferStatus",
    "Injury",
    "InjurySeverity",
    "InjuryStatus",
    "Staff",
    "StaffRole",
    "TrainingSchedule",
    "TrainingFocus",
    "TrainingIntensity",
    "ScoutingAssignment",
    "AssignmentType",
    "AssignmentStatus",
    "MediaEvent",
    "MediaEventType",
    "MediaEventStatus",
    "Competition",
    "CompetitionType",
    "Fixture",
    "FixtureStatus",
    "FinancialTransaction",
    "TransactionType",
    "IncomeCategory",
    "ExpenditureCategory",
    "SeasonDeficitRecord",
    "SponsorshipDeal",
    "InfrastructureUpgrade",
    "UpgradeStatus",
    "ScoutingShortlist",
]
