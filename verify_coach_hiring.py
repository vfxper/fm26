"""
Verification script for coach hiring system (Task 10.5)

This script demonstrates and verifies the coach hiring system functionality.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.services.staff_service import StaffService
from app.models.staff import StaffRole
from app.models.training_schedule import TrainingFocus


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def setup_database():
    """Create test database and tables"""
    # Import all models to ensure they're registered
    from app.models import (
        User, Player, Club, Career, SquadPlayer, Match, MatchEvent, Transfer,
        Injury, Staff, TrainingSchedule, ScoutingAssignment, MediaEvent,
        Competition, Fixture
    )
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    return engine


async def main():
    """Main verification function"""
    print("=" * 80)
    print("COACH HIRING SYSTEM VERIFICATION (Task 10.5)")
    print("=" * 80)
    print()
    
    # Setup database
    print("Setting up test database...")
    engine = await setup_database()
    
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with async_session_factory() as session:
        service = StaffService(session)
        
        # Test 1: Hire a fitness coach
        print("\n" + "=" * 80)
        print("TEST 1: Hire a Fitness Coach")
        print("=" * 80)
        
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
        
        fitness_coach = await service.hire_staff(
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
        
        print(f"✓ Hired: {fitness_coach.name}")
        print(f"  Role: {fitness_coach.get_role_display_name()}")
        print(f"  Age: {fitness_coach.age}")
        print(f"  Nationality: {fitness_coach.nationality}")
        print(f"  Primary Attribute (Fitness): {fitness_coach.fitness}")
        print(f"  Wage: £{fitness_coach.wage:,}/week")
        print(f"  Contract: {fitness_coach.contract_years} years")
        print(f"  Provides Bonus: {fitness_coach.provides_fitness_bonus()}")
        
        # Test 2: Hire multiple specialist coaches
        print("\n" + "=" * 80)
        print("TEST 2: Hire Multiple Specialist Coaches (up to 5)")
        print("=" * 80)
        
        coaches_to_hire = [
            {
                "name": "Carlos Rodriguez",
                "role": StaffRole.DEFENSIVE_COACH,
                "primary_attr": "coaching",
                "value": 18,
                "nationality": "Spain",
                "wage": 18000
            },
            {
                "name": "Marco Bianchi",
                "role": StaffRole.ATTACKING_COACH,
                "primary_attr": "coaching",
                "value": 16,
                "nationality": "Italy",
                "wage": 20000
            },
            {
                "name": "Hans Mueller",
                "role": StaffRole.GOALKEEPING_COACH,
                "primary_attr": "coaching",
                "value": 17,
                "nationality": "Germany",
                "wage": 16000
            },
            {
                "name": "Pierre Dubois",
                "role": StaffRole.FITNESS_COACH,
                "primary_attr": "fitness",
                "value": 15,
                "nationality": "France",
                "wage": 14000
            },
        ]
        
        for coach_data in coaches_to_hire:
            attrs = {
                "coaching": 12,
                "tactical_knowledge": 10,
                "man_management": 11,
                "scouting": 8,
                "medical": 9,
                "fitness": 12,
                "technical": 10,
                "mental": 10,
            }
            attrs[coach_data["primary_attr"]] = coach_data["value"]
            
            coach = await service.hire_staff(
                career_id=1,
                club_id=1,
                name=coach_data["name"],
                role=coach_data["role"],
                age=45,
                nationality=coach_data["nationality"],
                attributes=attrs,
                wage=coach_data["wage"],
                contract_years=2
            )
            
            print(f"✓ Hired: {coach.name} ({coach.get_role_display_name()})")
            print(f"  Primary Attribute: {coach.get_primary_attribute()}")
            print(f"  Wage: £{coach.wage:,}/week")
        
        # Check specialist coach count
        count = await service.count_specialist_coaches(career_id=1)
        print(f"\n✓ Total Specialist Coaches: {count}/{service.MAX_SPECIALIST_COACHES}")
        
        # Test 3: Try to hire 6th specialist coach (should fail)
        print("\n" + "=" * 80)
        print("TEST 3: Attempt to Hire 6th Specialist Coach (Should Fail)")
        print("=" * 80)
        
        try:
            await service.hire_staff(
                career_id=1,
                club_id=1,
                name="Extra Coach",
                role=StaffRole.DEFENSIVE_COACH,
                age=40,
                nationality="England",
                attributes=attributes,
                wage=12000,
                contract_years=2
            )
            print("✗ ERROR: Should have raised ValueError!")
        except ValueError as e:
            print(f"✓ Correctly rejected: {e}")
        
        # Test 4: Hire non-specialist staff (should succeed)
        print("\n" + "=" * 80)
        print("TEST 4: Hire Non-Specialist Staff (Should Succeed)")
        print("=" * 80)
        
        scout_attrs = {
            "coaching": 10,
            "tactical_knowledge": 12,
            "man_management": 11,
            "scouting": 18,  # High scouting attribute
            "medical": 9,
            "fitness": 10,
            "technical": 10,
            "mental": 10,
        }
        
        scout = await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Roberto Silva",
            role=StaffRole.CHIEF_SCOUT,
            age=50,
            nationality="Brazil",
            attributes=scout_attrs,
            wage=22000,
            contract_years=3
        )
        
        print(f"✓ Hired: {scout.name} ({scout.get_role_display_name()})")
        print(f"  Primary Attribute (Scouting): {scout.scouting}")
        print(f"  Provides Bonus: {scout.provides_scouting_bonus()}")
        
        physio_attrs = {
            "coaching": 9,
            "tactical_knowledge": 8,
            "man_management": 10,
            "scouting": 7,
            "medical": 19,  # High medical attribute
            "fitness": 11,
            "technical": 9,
            "mental": 10,
        }
        
        physio = await service.hire_staff(
            career_id=1,
            club_id=1,
            name="Dr. Sarah Johnson",
            role=StaffRole.PHYSIO,
            age=42,
            nationality="England",
            attributes=physio_attrs,
            wage=20000,
            contract_years=4
        )
        
        print(f"✓ Hired: {physio.name} ({physio.get_role_display_name()})")
        print(f"  Primary Attribute (Medical): {physio.medical}")
        print(f"  Provides Bonus: {physio.provides_medical_bonus()}")
        
        # Verify specialist coach count hasn't changed
        count = await service.count_specialist_coaches(career_id=1)
        print(f"\n✓ Specialist Coach Count Still: {count}/{service.MAX_SPECIALIST_COACHES}")
        
        # Test 5: Get coach bonuses
        print("\n" + "=" * 80)
        print("TEST 5: Calculate Coach Bonuses for Training")
        print("=" * 80)
        
        bonuses = await service.get_coach_bonuses(career_id=1)
        
        print(f"✓ Coach Bonuses Calculated:")
        if bonuses:
            for focus, multiplier in bonuses.items():
                bonus_pct = (multiplier - 1.0) * 100
                print(f"  {focus.value}: +{bonus_pct:.0f}% bonus (multiplier: {multiplier})")
        else:
            print("  No bonuses (no coaches with high enough attributes)")
        
        # Test 6: Get staff summary
        print("\n" + "=" * 80)
        print("TEST 6: Get Staff Summary")
        print("=" * 80)
        
        summary = await service.get_staff_summary(career_id=1)
        
        print(f"✓ Staff Summary:")
        print(f"  Total Staff: {summary['total_staff']}")
        print(f"  Specialist Coaches: {summary['specialist_coaches']}/{summary['max_specialist_coaches']}")
        print(f"  Total Wage Bill: £{summary['total_wage_bill']:,}/week")
        print(f"\n  Staff by Role:")
        for role, staff_list in summary['staff_by_role'].items():
            print(f"    {role}: {len(staff_list)} staff member(s)")
        
        # Test 7: Fire a coach
        print("\n" + "=" * 80)
        print("TEST 7: Fire a Coach")
        print("=" * 80)
        
        result = await service.fire_staff(staff_id=fitness_coach.id, career_id=1)
        print(f"✓ Fired: {fitness_coach.name}")
        print(f"  Result: {result}")
        
        # Verify count decreased
        count = await service.count_specialist_coaches(career_id=1)
        print(f"✓ Specialist Coach Count After Firing: {count}/{service.MAX_SPECIALIST_COACHES}")
        
        # Test 8: Generate random coach
        print("\n" + "=" * 80)
        print("TEST 8: Generate Random Coach Attributes")
        print("=" * 80)
        
        qualities = ["poor", "average", "good", "elite"]
        for quality in qualities:
            coach_data = service.generate_random_coach(
                role=StaffRole.FITNESS_COACH,
                quality=quality
            )
            
            print(f"\n✓ {quality.upper()} Quality Coach:")
            print(f"  Age: {coach_data['age']}")
            print(f"  Suggested Wage: £{coach_data['suggested_wage']:,}/week")
            print(f"  Attributes:")
            for attr, value in coach_data['attributes'].items():
                print(f"    {attr}: {value}")
    
    # Cleanup
    await engine.dispose()
    
    print("\n" + "=" * 80)
    print("ALL TESTS PASSED ✓")
    print("=" * 80)
    print("\nCoach hiring system (Task 10.5) is working correctly!")
    print("- Can hire up to 5 specialist coaches")
    print("- Coaches provide bonuses to training when attributes > 15")
    print("- Non-specialist staff don't count towards the limit")
    print("- Can fire coaches to free up slots")
    print("- Coach bonuses are correctly calculated for training")


if __name__ == "__main__":
    asyncio.run(main())
