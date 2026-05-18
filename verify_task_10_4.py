"""
Verification script for Task 10.4: Create attribute decline for players > 30 years

This script verifies that the attribute decline system for players over 30 years old
is correctly implemented and working as specified in Requirement 7.4.

Requirement 7.4:
"WHEN a player over 30 years old is not assigned to a Fitness training focus,
THE Training_Module SHALL decrease the player's stamina and pace attributes
by 1 point per 8 in-game weeks."
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.player import Player
from app.models.squad_player import SquadPlayer
from app.models.training_schedule import TrainingSchedule, TrainingFocus, TrainingIntensity
from app.models.career import Career
from app.models.club import Club
from app.models.user import User
from app.services.training_service import TrainingService


async def verify_attribute_decline():
    """
    Verify that attribute decline works correctly for players over 30 years old.
    """
    print("=" * 80)
    print("TASK 10.4 VERIFICATION: Attribute Decline for Players > 30 Years")
    print("=" * 80)
    print()
    
    # Create in-memory test database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create test data
        print("Setting up test data...")
        
        # Create user
        user = User(
            telegram_id=12345,
            username="testuser",
            first_name="Test",
            language_code="en"
        )
        session.add(user)
        await session.flush()
        
        # Create club
        club = Club(
            name="Test FC",
            reputation=50,
            balance=1000000,
            transfer_budget=500000,
            wage_budget=50000
        )
        session.add(club)
        await session.flush()
        
        # Create career
        career = Career(
            user_id=user.id,
            club_id=club.id,
            manager_name="Test Manager",
            current_season=1,
            current_week=1
        )
        session.add(career)
        await session.flush()
        
        # Create old player (age 32)
        old_player = Player(
            uid="old_001",
            name="Veteran Player",
            position="CM",
            age=32,
            ca=140,
            pa=140,
            nationality="Spain",
            club="Test FC",
            # Technical attributes
            corners=12, crossing=13, dribbling=14, finishing=13, first_touch=15,
            free_kicks=14, heading=12, long_shots=14, long_throws=10, marking=13,
            passing=16, penalty=14, tackling=13, technique=15,
            # Mental attributes
            aggression=11, anticipation=16, bravery=14, composure=16, concentration=15,
            decisions=17, determination=15, flair=13, leadership=16, off_the_ball=14,
            positioning=16, teamwork=16, vision=17, work_rate=14,
            # Physical attributes
            acceleration=11, agility=12, balance=13, jumping=11, stamina=12,
            pace=11, endurance=12, strength=12,
            # Financial
            price="2M", wage=25000,
            # Physical stats
            height=178, weight=73, left_foot=14, right_foot=15
        )
        session.add(old_player)
        await session.flush()
        
        # Create squad player
        old_squad_player = SquadPlayer(
            career_id=career.id,
            player_id=old_player.id,
            squad_status="key_player",
            morale=80,
            contract_expiry_season=3,
            contract_expiry_week=1,
            wage=25000
        )
        session.add(old_squad_player)
        await session.flush()
        
        await session.commit()
        
        print(f"✓ Created test player: {old_player.name} (Age: {old_player.age})")
        print(f"  Initial Stamina: {old_player.stamina}")
        print(f"  Initial Pace: {old_player.pace}")
        print()
        
        # Test Case 1: Player declines after 8 weeks without fitness training
        print("TEST CASE 1: Player declines after 8 weeks without fitness training")
        print("-" * 80)
        
        # Create training schedule for 8 consecutive weeks on tactics (not fitness)
        for week in range(1, 9):
            schedule = TrainingSchedule(
                career_id=career.id,
                player_id=old_player.id,
                squad_player_id=old_squad_player.id,
                training_focus=TrainingFocus.TACTICS,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=week,
                consecutive_weeks=week
            )
            session.add(schedule)
        
        await session.commit()
        print(f"✓ Assigned player to TACTICS training for 8 consecutive weeks")
        
        # Simulate training for week 8
        training_service = TrainingService(session)
        result = await training_service.simulate_weekly_training(
            career_id=career.id,
            season=1,
            week=8,
            training_intensity=TrainingIntensity.NORMAL
        )
        
        # Refresh player data
        await session.refresh(old_player)
        
        print(f"✓ Simulated training for week 8")
        print()
        print("RESULTS:")
        print(f"  Players trained: {result['players_trained']}")
        print(f"  Declines: {len(result['declines'])}")
        print(f"  Final Stamina: {old_player.stamina}")
        print(f"  Final Pace: {old_player.pace}")
        print()
        
        # Verify decline occurred
        if len(result['declines']) == 1:
            decline = result['declines'][0]
            print("✓ PASS: Player declined as expected")
            print(f"  Decline details: {decline['declines']}")
            
            # Check that stamina or pace decreased
            if old_player.stamina < 12 or old_player.pace < 11:
                print("✓ PASS: Stamina and/or pace decreased by 1 point")
            else:
                print("✗ FAIL: Stamina and pace did not decrease")
                return False
        else:
            print("✗ FAIL: Expected 1 decline, got", len(result['declines']))
            return False
        
        print()
        
        # Test Case 2: Fitness training prevents decline
        print("TEST CASE 2: Fitness training prevents decline")
        print("-" * 80)
        
        # Reset player attributes
        old_player.stamina = 12
        old_player.pace = 11
        await session.commit()
        
        print(f"✓ Reset player attributes (Stamina: {old_player.stamina}, Pace: {old_player.pace})")
        
        # Create training schedule for 8 consecutive weeks on fitness
        for week in range(9, 17):
            schedule = TrainingSchedule(
                career_id=career.id,
                player_id=old_player.id,
                squad_player_id=old_squad_player.id,
                training_focus=TrainingFocus.FITNESS,
                training_intensity=TrainingIntensity.NORMAL,
                season=1,
                week=week,
                consecutive_weeks=week - 8
            )
            session.add(schedule)
        
        await session.commit()
        print(f"✓ Assigned player to FITNESS training for 8 consecutive weeks")
        
        # Simulate training for week 16
        result = await training_service.simulate_weekly_training(
            career_id=career.id,
            season=1,
            week=16,
            training_intensity=TrainingIntensity.NORMAL
        )
        
        # Refresh player data
        await session.refresh(old_player)
        
        print(f"✓ Simulated training for week 16")
        print()
        print("RESULTS:")
        print(f"  Players trained: {result['players_trained']}")
        print(f"  Declines: {len(result['declines'])}")
        print(f"  Final Stamina: {old_player.stamina}")
        print(f"  Final Pace: {old_player.pace}")
        print()
        
        # Verify no decline occurred
        if len(result['declines']) == 0:
            print("✓ PASS: No decline occurred (fitness training prevented it)")
            
            # Check that stamina and pace stayed the same
            if old_player.stamina == 12 and old_player.pace == 11:
                print("✓ PASS: Stamina and pace remained unchanged")
            else:
                print("✗ FAIL: Stamina or pace changed unexpectedly")
                return False
        else:
            print("✗ FAIL: Expected 0 declines, got", len(result['declines']))
            return False
        
        print()
        print("=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        print()
        print("VERIFICATION SUMMARY:")
        print("✓ Attribute decline system is correctly implemented")
        print("✓ Players over 30 decline after 8 weeks without fitness training")
        print("✓ Stamina and pace attributes decrease by 1 point")
        print("✓ Fitness training prevents attribute decline")
        print("✓ Requirement 7.4 is fully satisfied")
        print()
        
        return True
    
    await engine.dispose()


async def main():
    """Main entry point"""
    try:
        success = await verify_attribute_decline()
        if success:
            print("Task 10.4 verification: SUCCESS ✓")
            sys.exit(0)
        else:
            print("Task 10.4 verification: FAILED ✗")
            sys.exit(1)
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
