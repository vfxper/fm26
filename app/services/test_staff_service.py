"""
Unit tests for StaffService - Coach hiring and management
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.staff_service import StaffService
from app.models.staff import Staff, StaffRole
from app.models.training_schedule import TrainingFocus
from app.models.user import User
from app.models.club import Club
from app.models.career import Career


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """Create test database engine"""
    # Import all models to ensure they're registered with Base.metadata
    from app.models import (
        User, Player, Club, Career, SquadPlayer, Match, MatchEvent, Transfer,
        Injury, Staff, TrainingSchedule, ScoutingAssignment, MediaEvent,
        Competition, Fixture
    )
    from app.models.player import Player as PlayerModel
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        future=True,
        connect_args={"check_same_thread": False}
    )
    
    # Remove the GIN index from the players table before creating tables
    players_table = PlayerModel.__table__
    gin_index = None
    for idx in list(players_table.indexes):
        if idx.name == 'idx_players_fts':
            gin_index = idx
            players_table.indexes.discard(idx)
            break
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Restore the GIN index
    if gin_index:
        players_table.indexes.add(gin_index)
    
    yield engine
    
    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Create test database session"""
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
class TestStaffService:
    """Test suite for StaffService"""
    
    async def test_hire_fitness_coach(self, db_session: AsyncSession):
        """Test hiring a fitness coach"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 12,
            "tactical_knowledge": 10,
            "man_management": 11,
            "scouting": 8,
            "medical": 9,
            "fitness": 16,  # High fitness attribute
            "technical": 10,
            "mental": 10,
        }
        
        staff = await service.hire_staff(
            career_id=1,
            club_id=1,
            name="John Smith",
            role=StaffRole.FITNESS_COACH,
            age=45,
            nationality="England",
            attributes=attributes,
            wage=15000,
            contract_years=3
        )
        
        assert staff.id is not None
        assert staff.name == "John Smith"
        assert staff.role == StaffRole.FITNESS_COACH
        assert staff.age == 45
        assert staff.nationality == "England"
        assert staff.fitness == 16
        assert staff.wage == 15000
        assert staff.contract_years == 3
        assert staff.morale == 70  # Default starting morale
        assert staff.performance_rating == 10  # Default starting performance
    
    async def test_hire_multiple_specialist_coaches(self, db_session: AsyncSession):
        """Test hiring multiple specialist coaches up to the limit"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 16,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire 5 specialist coaches (the maximum)
        coaches = []
        roles = [
            StaffRole.FITNESS_COACH,
            StaffRole.DEFENSIVE_COACH,
            StaffRole.ATTACKING_COACH,
            StaffRole.GOALKEEPING_COACH,
            StaffRole.FITNESS_COACH,  # Can hire multiple of same role
        ]
        
        for i, role in enumerate(roles):
            coach = await service.hire_staff(
                career_id=1,
                club_id=1,
                name=f"Coach {i+1}",
                role=role,
                age=40 + i,
                nationality="England",
                attributes=attributes,
                wage=12000 + i * 1000,
                contract_years=2
            )
            coaches.append(coach)
        
        assert len(coaches) == 5
        
        # Verify count
        count = await service.count_specialist_coaches(career_id=1)
        assert count == 5
    
    async def test_hire_exceeds_specialist_coach_limit(self, db_session: AsyncSession):
        """Test that hiring more than 5 specialist coaches raises an error"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 14,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire 5 specialist coaches
        for i in range(5):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name=f"Coach {i+1}",
                role=StaffRole.FITNESS_COACH,
                age=40,
                nationality="England",
                attributes=attributes,
                wage=12000,
                contract_years=2
            )
        
        # Try to hire a 6th specialist coach
        with pytest.raises(ValueError, match="Cannot hire more than 5 specialist coaches"):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name="Coach 6",
                role=StaffRole.DEFENSIVE_COACH,
                age=40,
                nationality="England",
                attributes=attributes,
                wage=12000,
                contract_years=2
            )
    
    async def test_hire_non_specialist_staff_no_limit(self, db_session: AsyncSession):
        """Test that non-specialist staff (scouts, physio) don't count towards limit"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 12,
            "tactical_knowledge": 10,
            "man_management": 11,
            "scouting": 16,
            "medical": 16,
            "fitness": 10,
            "technical": 10,
            "mental": 10,
        }
        
        # Hire 5 specialist coaches
        for i in range(5):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name=f"Coach {i+1}",
                role=StaffRole.FITNESS_COACH,
                age=40,
                nationality="England",
                attributes=attributes,
                wage=12000,
                contract_years=2
            )
        
        # Should be able to hire non-specialist staff
        scout = await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Chief Scout",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="England",
            attributes=attributes,
            wage=18000,
            contract_years=3
        )
        
        physio = await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Head Physio",
            role=StaffRole.PHYSIO,
            age=45,
            nationality="England",
            attributes=attributes,
            wage=16000,
            contract_years=2
        )
        
        assert scout.id is not None
        assert physio.id is not None
        
        # Specialist coach count should still be 5
        count = await service.count_specialist_coaches(career_id=1)
        assert count == 5
    
    async def test_fire_staff(self, db_session: AsyncSession):
        """Test firing a staff member"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 16,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire a coach
        coach = await service.hire_staff(
            career_id=1,
            club_id=1,
            name="John Doe",
            role=StaffRole.FITNESS_COACH,
            age=45,
            nationality="England",
            attributes=attributes,
            wage=15000,
            contract_years=3
        )
        
        coach_id = coach.id
        
        # Fire the coach
        result = await service.fire_staff(staff_id=coach_id, career_id=1)
        assert result is True
        
        # Verify coach is gone
        all_staff = await service.get_all_staff(career_id=1)
        assert len(all_staff) == 0
    
    async def test_get_coach_bonuses_fitness_coach(self, db_session: AsyncSession):
        """Test that fitness coach with high fitness attribute provides bonus"""
        service = StaffService(db_session)
        
        # Hire fitness coach with high fitness attribute (> 15)
        attributes = {
            "coaching": 12,
            "tactical_knowledge": 10,
            "man_management": 11,
            "scouting": 8,
            "medical": 9,
            "fitness": 17,  # High fitness attribute
            "technical": 10,
            "mental": 10,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Fitness Coach",
            role=StaffRole.FITNESS_COACH,
            age=45,
            nationality="England",
            attributes=attributes,
            wage=15000,
            contract_years=3
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have 10% bonus for FITNESS training
        assert TrainingFocus.FITNESS in bonuses
        assert bonuses[TrainingFocus.FITNESS] == 1.1  # 1.0 + 10%
    
    async def test_get_coach_bonuses_defensive_coach(self, db_session: AsyncSession):
        """Test that defensive coach with high coaching attribute provides bonus"""
        service = StaffService(db_session)
        
        # Hire defensive coach with high coaching attribute (> 15)
        attributes = {
            "coaching": 18,  # High coaching attribute
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 12,
            "technical": 11,
            "mental": 10,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Defensive Coach",
            role=StaffRole.DEFENSIVE_COACH,
            age=50,
            nationality="England",
            attributes=attributes,
            wage=18000,
            contract_years=2
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have 10% bonus for DEFENDING training
        assert TrainingFocus.DEFENDING in bonuses
        assert bonuses[TrainingFocus.DEFENDING] == 1.1
    
    async def test_get_coach_bonuses_attacking_coach(self, db_session: AsyncSession):
        """Test that attacking coach with high coaching attribute provides bonus"""
        service = StaffService(db_session)
        
        # Hire attacking coach with high coaching attribute (> 15)
        attributes = {
            "coaching": 16,  # High coaching attribute
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 12,
            "technical": 11,
            "mental": 10,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Attacking Coach",
            role=StaffRole.ATTACKING_COACH,
            age=48,
            nationality="Spain",
            attributes=attributes,
            wage=20000,
            contract_years=3
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have 10% bonus for ATTACKING training
        assert TrainingFocus.ATTACKING in bonuses
        assert bonuses[TrainingFocus.ATTACKING] == 1.1
    
    async def test_get_coach_bonuses_goalkeeping_coach(self, db_session: AsyncSession):
        """Test that goalkeeping coach with high coaching attribute provides bonus"""
        service = StaffService(db_session)
        
        # Hire goalkeeping coach with high coaching attribute (> 15)
        attributes = {
            "coaching": 17,  # High coaching attribute
            "tactical_knowledge": 12,
            "man_management": 11,
            "scouting": 8,
            "medical": 9,
            "fitness": 10,
            "technical": 13,
            "mental": 10,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="GK Coach",
            role=StaffRole.GOALKEEPING_COACH,
            age=52,
            nationality="Italy",
            attributes=attributes,
            wage=17000,
            contract_years=2
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have 10% bonus for INDIVIDUAL_TECHNICAL training (for goalkeepers)
        assert TrainingFocus.INDIVIDUAL_TECHNICAL in bonuses
        assert bonuses[TrainingFocus.INDIVIDUAL_TECHNICAL] == 1.1
    
    async def test_get_coach_bonuses_low_attribute_no_bonus(self, db_session: AsyncSession):
        """Test that coach with low attribute does not provide bonus"""
        service = StaffService(db_session)
        
        # Hire fitness coach with low fitness attribute (<= 15)
        attributes = {
            "coaching": 12,
            "tactical_knowledge": 10,
            "man_management": 11,
            "scouting": 8,
            "medical": 9,
            "fitness": 14,  # Low fitness attribute
            "technical": 10,
            "mental": 10,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Weak Fitness Coach",
            role=StaffRole.FITNESS_COACH,
            age=45,
            nationality="England",
            attributes=attributes,
            wage=10000,
            contract_years=2
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have no bonus for FITNESS training
        assert TrainingFocus.FITNESS not in bonuses
    
    async def test_get_coach_bonuses_multiple_coaches(self, db_session: AsyncSession):
        """Test getting bonuses from multiple coaches"""
        service = StaffService(db_session)
        
        # Hire multiple coaches with high attributes
        coaches_data = [
            {
                "name": "Fitness Coach",
                "role": StaffRole.FITNESS_COACH,
                "primary_attr": "fitness",
                "value": 18,
                "expected_focus": TrainingFocus.FITNESS
            },
            {
                "name": "Defensive Coach",
                "role": StaffRole.DEFENSIVE_COACH,
                "primary_attr": "coaching",
                "value": 17,
                "expected_focus": TrainingFocus.DEFENDING
            },
            {
                "name": "Attacking Coach",
                "role": StaffRole.ATTACKING_COACH,
                "primary_attr": "coaching",
                "value": 16,
                "expected_focus": TrainingFocus.ATTACKING
            },
        ]
        
        for coach_data in coaches_data:
            attributes = {
                "coaching": 12,
                "tactical_knowledge": 10,
                "man_management": 11,
                "scouting": 8,
                "medical": 9,
                "fitness": 12,
                "technical": 10,
                "mental": 10,
            }
            attributes[coach_data["primary_attr"]] = coach_data["value"]
            
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name=coach_data["name"],
                role=coach_data["role"],
                age=45,
                nationality="England",
                attributes=attributes,
                wage=15000,
                contract_years=3
            )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have bonuses for all three training focuses
        assert len(bonuses) == 3
        assert TrainingFocus.FITNESS in bonuses
        assert TrainingFocus.DEFENDING in bonuses
        assert TrainingFocus.ATTACKING in bonuses
        assert all(bonus == 1.1 for bonus in bonuses.values())
    
    async def test_get_coach_bonuses_assistant_manager(self, db_session: AsyncSession):
        """Test that assistant manager with high tactical_knowledge provides tactics bonus"""
        service = StaffService(db_session)
        
        # Hire assistant manager with high tactical_knowledge (> 15)
        attributes = {
            "coaching": 14,
            "tactical_knowledge": 18,  # High tactical_knowledge attribute
            "man_management": 15,
            "scouting": 10,
            "medical": 9,
            "fitness": 12,
            "technical": 13,
            "mental": 14,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Assistant Manager",
            role=StaffRole.ASSISTANT_MANAGER,
            age=48,
            nationality="Germany",
            attributes=attributes,
            wage=25000,
            contract_years=3
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have 10% bonus for TACTICS training
        assert TrainingFocus.TACTICS in bonuses
        assert bonuses[TrainingFocus.TACTICS] == 1.1
    
    async def test_get_coach_bonuses_sports_scientist(self, db_session: AsyncSession):
        """Test that sports scientist with high technical attribute provides mental training bonus"""
        service = StaffService(db_session)
        
        # Hire sports scientist with high technical attribute (> 15)
        attributes = {
            "coaching": 12,
            "tactical_knowledge": 13,
            "man_management": 11,
            "scouting": 10,
            "medical": 14,
            "fitness": 13,
            "technical": 17,  # High technical attribute
            "mental": 12,
        }
        
        await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Sports Scientist",
            role=StaffRole.SPORTS_SCIENTIST,
            age=35,
            nationality="Netherlands",
            attributes=attributes,
            wage=20000,
            contract_years=2
        )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have 10% bonus for INDIVIDUAL_MENTAL training
        assert TrainingFocus.INDIVIDUAL_MENTAL in bonuses
        assert bonuses[TrainingFocus.INDIVIDUAL_MENTAL] == 1.1
    
    async def test_get_coach_bonuses_all_roles(self, db_session: AsyncSession):
        """Test getting bonuses from all bonus-eligible roles simultaneously"""
        service = StaffService(db_session)
        
        # Hire all bonus-eligible staff with high attributes
        all_coaches_data = [
            {
                "name": "Fitness Coach",
                "role": StaffRole.FITNESS_COACH,
                "primary_attr": "fitness",
                "value": 18,
                "expected_focus": TrainingFocus.FITNESS
            },
            {
                "name": "Defensive Coach",
                "role": StaffRole.DEFENSIVE_COACH,
                "primary_attr": "coaching",
                "value": 17,
                "expected_focus": TrainingFocus.DEFENDING
            },
            {
                "name": "Attacking Coach",
                "role": StaffRole.ATTACKING_COACH,
                "primary_attr": "coaching",
                "value": 16,
                "expected_focus": TrainingFocus.ATTACKING
            },
            {
                "name": "GK Coach",
                "role": StaffRole.GOALKEEPING_COACH,
                "primary_attr": "coaching",
                "value": 17,
                "expected_focus": TrainingFocus.INDIVIDUAL_TECHNICAL
            },
            {
                "name": "Assistant Manager",
                "role": StaffRole.ASSISTANT_MANAGER,
                "primary_attr": "tactical_knowledge",
                "value": 18,
                "expected_focus": TrainingFocus.TACTICS
            },
            {
                "name": "Sports Scientist",
                "role": StaffRole.SPORTS_SCIENTIST,
                "primary_attr": "technical",
                "value": 16,
                "expected_focus": TrainingFocus.INDIVIDUAL_MENTAL
            },
        ]
        
        for coach_data in all_coaches_data:
            attributes = {
                "coaching": 12,
                "tactical_knowledge": 10,
                "man_management": 11,
                "scouting": 8,
                "medical": 9,
                "fitness": 12,
                "technical": 10,
                "mental": 10,
            }
            attributes[coach_data["primary_attr"]] = coach_data["value"]
            
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name=coach_data["name"],
                role=coach_data["role"],
                age=45,
                nationality="England",
                attributes=attributes,
                wage=15000,
                contract_years=3
            )
        
        # Get coach bonuses
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        # Should have bonuses for all 6 training focuses
        assert len(bonuses) == 6
        assert TrainingFocus.FITNESS in bonuses
        assert TrainingFocus.DEFENDING in bonuses
        assert TrainingFocus.ATTACKING in bonuses
        assert TrainingFocus.INDIVIDUAL_TECHNICAL in bonuses
        assert TrainingFocus.TACTICS in bonuses
        assert TrainingFocus.INDIVIDUAL_MENTAL in bonuses
        assert all(bonus == 1.1 for bonus in bonuses.values())
    
    async def test_get_staff_summary(self, db_session: AsyncSession):
        """Test getting staff summary"""
        service = StaffService(db_session)
        
        # Hire multiple staff members
        staff_data = [
            {"role": StaffRole.FITNESS_COACH, "wage": 15000},
            {"role": StaffRole.DEFENSIVE_COACH, "wage": 16000},
            {"role": StaffRole.CHIEF_SCOUT, "wage": 18000},
            {"role": StaffRole.PHYSIO, "wage": 14000},
        ]
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 16,
            "medical": 16,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        for i, data in enumerate(staff_data):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name=f"Staff {i+1}",
                role=data["role"],
                age=45,
                nationality="England",
                attributes=attributes,
                wage=data["wage"],
                contract_years=3
            )
        
        # Get summary
        summary = await service.get_staff_summary(career_id=1)
        
        assert summary["total_staff"] == 4
        assert summary["specialist_coaches"] == 2  # FITNESS_COACH and DEFENSIVE_COACH
        assert summary["max_specialist_coaches"] == 5
        assert summary["total_wage_bill"] == 15000 + 16000 + 18000 + 14000
        assert len(summary["staff_by_role"]) == 4
    
    async def test_generate_random_coach(self, db_session: AsyncSession):
        """Test generating random coach attributes"""
        service = StaffService(db_session)
        
        # Generate coaches of different qualities
        qualities = ["poor", "average", "good", "elite"]
        
        for quality in qualities:
            coach_data = service.generate_random_coach(
                role=StaffRole.FITNESS_COACH,
                quality=quality
            )
            
            assert "attributes" in coach_data
            assert "suggested_wage" in coach_data
            assert "age" in coach_data
            assert "quality" in coach_data
            
            # Check attribute ranges
            attrs = coach_data["attributes"]
            if quality == "poor":
                assert all(5 <= v <= 10 for v in attrs.values())
            elif quality == "average":
                assert all(10 <= v <= 15 for v in attrs.values())
            elif quality == "good":
                assert any(v >= 15 for v in attrs.values())
            elif quality == "elite":
                assert any(v >= 18 for v in attrs.values())
    
    async def test_invalid_contract_years(self, db_session: AsyncSession):
        """Test that invalid contract years raises an error"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Try to hire with invalid contract years
        with pytest.raises(ValueError, match="Contract years must be between 1 and 5"):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name="Coach",
                role=StaffRole.FITNESS_COACH,
                age=45,
                nationality="England",
                attributes=attributes,
                wage=15000,
                contract_years=6  # Invalid
            )
    
    async def test_invalid_age(self, db_session: AsyncSession):
        """Test that invalid age raises an error"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Try to hire with invalid age
        with pytest.raises(ValueError, match="Staff age must be between 18 and 80"):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name="Coach",
                role=StaffRole.FITNESS_COACH,
                age=85,  # Invalid
                nationality="England",
                attributes=attributes,
                wage=15000,
                contract_years=3
            )
    
    async def test_invalid_wage(self, db_session: AsyncSession):
        """Test that invalid wage raises an error"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Try to hire with invalid wage
        with pytest.raises(ValueError, match="Wage must be positive"):
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name="Coach",
                role=StaffRole.FITNESS_COACH,
                age=45,
                nationality="England",
                attributes=attributes,
                wage=0,  # Invalid
                contract_years=3
            )


@pytest.mark.asyncio
class TestStaffManagementView:
    """Test suite for get_staff_management_view()"""
    
    async def test_empty_staff_management_view(self, db_session: AsyncSession):
        """Test management view with no staff hired"""
        service = StaffService(db_session)
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        assert view["career_id"] == 1
        assert view["club_id"] == 1
        assert view["total_staff"] == 0
        assert view["specialist_coaches_count"] == 0
        assert view["max_specialist_coaches"] == 5
        assert view["specialist_coaches_display"] == "0/5"
        assert view["total_wage_bill"] == 0
        assert view["expiring_contracts"] == []
        assert view["low_morale_staff"] == []
        # All 8 roles should be available
        assert len(view["available_positions"]) == 8
        # Should have hiring recommendations for essential roles
        assert len(view["hiring_recommendations"]) > 0
    
    async def test_staff_grouped_by_role(self, db_session: AsyncSession):
        """Test that staff are correctly grouped by role"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 16,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 16,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire staff in different roles
        await service.hire_staff(
            career_id=1, club_id=1, name="Fitness Coach 1",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=3
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="Chief Scout",
            role=StaffRole.CHIEF_SCOUT, age=50, nationality="Spain",
            attributes=attributes, wage=18000, contract_years=2
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        assert view["total_staff"] == 2
        assert len(view["staff_by_role"]["fitness_coach"]) == 1
        assert len(view["staff_by_role"]["chief_scout"]) == 1
        assert view["staff_by_role"]["fitness_coach"][0]["name"] == "Fitness Coach 1"
        assert view["staff_by_role"]["chief_scout"][0]["name"] == "Chief Scout"
    
    async def test_specialist_coach_count_display(self, db_session: AsyncSession):
        """Test specialist coach count vs limit display"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 16,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 16,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire 3 specialist coaches
        for i, role in enumerate([StaffRole.FITNESS_COACH, StaffRole.DEFENSIVE_COACH, StaffRole.ATTACKING_COACH]):
            await service.hire_staff(
                career_id=1, club_id=1, name=f"Coach {i+1}",
                role=role, age=40+i, nationality="England",
                attributes=attributes, wage=15000, contract_years=3
            )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        assert view["specialist_coaches_count"] == 3
        assert view["specialist_coaches_display"] == "3/5"
    
    async def test_total_wage_bill(self, db_session: AsyncSession):
        """Test total wage bill calculation"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        await service.hire_staff(
            career_id=1, club_id=1, name="Coach A",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=3
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="Coach B",
            role=StaffRole.CHIEF_SCOUT, age=50, nationality="Spain",
            attributes=attributes, wage=20000, contract_years=2
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="Coach C",
            role=StaffRole.PHYSIO, age=40, nationality="Germany",
            attributes=attributes, wage=12000, contract_years=2
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        assert view["total_wage_bill"] == 15000 + 20000 + 12000
    
    async def test_expiring_contracts(self, db_session: AsyncSession):
        """Test detection of staff with expiring contracts (< 6 months)"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire a coach with a short contract (1 year - will expire soon relative to test)
        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Expiring Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=1
        )
        
        # Manually set contract to expire in 3 months
        coach.contract_expiry_date = datetime.now() + timedelta(days=80)
        await db_session.commit()
        
        # Hire another coach with long contract
        await service.hire_staff(
            career_id=1, club_id=1, name="Long Contract Coach",
            role=StaffRole.DEFENSIVE_COACH, age=50, nationality="Spain",
            attributes=attributes, wage=18000, contract_years=5
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        assert len(view["expiring_contracts"]) == 1
        assert view["expiring_contracts"][0]["name"] == "Expiring Coach"
    
    async def test_low_morale_staff(self, db_session: AsyncSession):
        """Test detection of staff with low morale (< 40)"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire a coach and set low morale
        coach = await service.hire_staff(
            career_id=1, club_id=1, name="Unhappy Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=3
        )
        coach.morale = 25
        await db_session.commit()
        
        # Hire another coach with normal morale
        await service.hire_staff(
            career_id=1, club_id=1, name="Happy Coach",
            role=StaffRole.DEFENSIVE_COACH, age=50, nationality="Spain",
            attributes=attributes, wage=18000, contract_years=3
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        assert len(view["low_morale_staff"]) == 1
        assert view["low_morale_staff"][0]["name"] == "Unhappy Coach"
        assert view["low_morale_staff"][0]["morale"] == 25
    
    async def test_available_positions(self, db_session: AsyncSession):
        """Test that available positions correctly shows unfilled roles"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire 3 staff members
        await service.hire_staff(
            career_id=1, club_id=1, name="AM",
            role=StaffRole.ASSISTANT_MANAGER, age=48, nationality="England",
            attributes=attributes, wage=25000, contract_years=3
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="FC",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=3
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="CS",
            role=StaffRole.CHIEF_SCOUT, age=50, nationality="Spain",
            attributes=attributes, wage=18000, contract_years=2
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        # 8 total roles - 3 filled = 5 available
        assert len(view["available_positions"]) == 5
        available_role_values = [p["role"] for p in view["available_positions"]]
        assert StaffRole.ASSISTANT_MANAGER.value not in available_role_values
        assert StaffRole.FITNESS_COACH.value not in available_role_values
        assert StaffRole.CHIEF_SCOUT.value not in available_role_values
        assert StaffRole.GOALKEEPING_COACH.value in available_role_values
        assert StaffRole.DEFENSIVE_COACH.value in available_role_values
    
    async def test_hiring_recommendations_essential_roles(self, db_session: AsyncSession):
        """Test hiring recommendations prioritize essential missing roles"""
        service = StaffService(db_session)
        
        # No staff hired - should recommend essential roles first
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        recommendations = view["hiring_recommendations"]
        high_priority = [r for r in recommendations if r["priority"] == "high"]
        
        # Should recommend Assistant Manager, Chief Scout, Physio as high priority
        high_priority_roles = [r["role"] for r in high_priority]
        assert StaffRole.ASSISTANT_MANAGER.value in high_priority_roles
        assert StaffRole.CHIEF_SCOUT.value in high_priority_roles
        assert StaffRole.PHYSIO.value in high_priority_roles
    
    async def test_hiring_recommendations_with_filled_essential_roles(self, db_session: AsyncSession):
        """Test that filled essential roles are not recommended"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 16,
            "man_management": 13,
            "scouting": 16,
            "medical": 16,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire all essential roles
        await service.hire_staff(
            career_id=1, club_id=1, name="AM",
            role=StaffRole.ASSISTANT_MANAGER, age=48, nationality="England",
            attributes=attributes, wage=25000, contract_years=3
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="CS",
            role=StaffRole.CHIEF_SCOUT, age=50, nationality="Spain",
            attributes=attributes, wage=18000, contract_years=2
        )
        await service.hire_staff(
            career_id=1, club_id=1, name="Physio",
            role=StaffRole.PHYSIO, age=40, nationality="Germany",
            attributes=attributes, wage=14000, contract_years=3
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        recommendations = view["hiring_recommendations"]
        high_priority = [r for r in recommendations if r["priority"] == "high"]
        
        # No high priority recommendations since essential roles are filled
        assert len(high_priority) == 0
    
    async def test_staff_detail_includes_bonus_info(self, db_session: AsyncSession):
        """Test that staff details include bonus provision information"""
        service = StaffService(db_session)
        
        # Hire a fitness coach with high fitness attribute (provides bonus)
        attributes = {
            "coaching": 12,
            "tactical_knowledge": 10,
            "man_management": 11,
            "scouting": 8,
            "medical": 9,
            "fitness": 18,  # High - provides bonus
            "technical": 10,
            "mental": 10,
        }
        
        await service.hire_staff(
            career_id=1, club_id=1, name="Elite Fitness Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=20000, contract_years=3
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        fitness_staff = view["staff_by_role"]["fitness_coach"]
        assert len(fitness_staff) == 1
        assert fitness_staff[0]["provides_bonus"] is True
        assert fitness_staff[0]["is_elite"] is True
        assert fitness_staff[0]["primary_attribute"] == 18
    
    async def test_view_filters_by_club_id(self, db_session: AsyncSession):
        """Test that view only returns staff for the specified club"""
        service = StaffService(db_session)
        
        attributes = {
            "coaching": 15,
            "tactical_knowledge": 14,
            "man_management": 13,
            "scouting": 10,
            "medical": 10,
            "fitness": 15,
            "technical": 12,
            "mental": 11,
        }
        
        # Hire staff for club 1
        await service.hire_staff(
            career_id=1, club_id=1, name="Club 1 Coach",
            role=StaffRole.FITNESS_COACH, age=45, nationality="England",
            attributes=attributes, wage=15000, contract_years=3
        )
        
        # Hire staff for club 2
        await service.hire_staff(
            career_id=1, club_id=2, name="Club 2 Coach",
            role=StaffRole.DEFENSIVE_COACH, age=50, nationality="Spain",
            attributes=attributes, wage=18000, contract_years=2
        )
        
        # View for club 1 should only show club 1 staff
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        assert view["total_staff"] == 1
        assert view["staff_by_role"]["fitness_coach"][0]["name"] == "Club 1 Coach"
    
    async def test_low_quality_staff_upgrade_recommendation(self, db_session: AsyncSession):
        """Test that low-quality staff trigger upgrade recommendations"""
        service = StaffService(db_session)
        
        # Hire a coach with very low primary attribute
        attributes = {
            "coaching": 5,
            "tactical_knowledge": 5,
            "man_management": 5,
            "scouting": 5,
            "medical": 5,
            "fitness": 7,  # Low fitness for a fitness coach
            "technical": 5,
            "mental": 5,
        }
        
        await service.hire_staff(
            career_id=1, club_id=1, name="Weak Coach",
            role=StaffRole.FITNESS_COACH, age=60, nationality="England",
            attributes=attributes, wage=5000, contract_years=1
        )
        
        view = await service.get_staff_management_view(career_id=1, club_id=1)
        
        # Should have a low-priority recommendation to upgrade
        low_priority = [r for r in view["hiring_recommendations"] if r["priority"] == "low"]
        upgrade_recs = [r for r in low_priority if "current_staff_id" in r]
        assert len(upgrade_recs) >= 1
        assert "consider upgrading" in upgrade_recs[0]["reason"]
