"""
Tests for Loan Deal System (Task 8.5)

This module tests the loan deal functionality including:
- Season-long loans (available during transfer windows)
- Emergency loans (available outside transfer windows)
- Wage contribution negotiation
- Loan duration management
- Loan return date tracking
- Squad player creation for loan players
- Transfer record creation for loans
"""

import pytest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from app.core.database import Base
from app.models.career import Career
from app.models.club import Club
from app.models.player import Player
from app.models.squad_player import SquadPlayer, SquadStatus
from app.models.transfer import Transfer, TransferType, TransferStatus
from app.models.user import User
from app.services.transfer_service import TransferService


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        telegram_id=12345,
        username="test_manager",
        first_name="Test",
        language_code="en"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_club(db_session):
    """Create a test club."""
    club = Club(
        name="Test FC",
        reputation=50,
        league="Test League",
        country="England",
        balance=10_000_000,
        transfer_budget=5_000_000,
        wage_budget=50_000,
        matchday_revenue=100_000,
        stadium_capacity=30_000,
    )
    db_session.add(club)
    await db_session.commit()
    await db_session.refresh(club)
    return club


@pytest.fixture
async def parent_club(db_session):
    """Create a parent club (loaning club)."""
    club = Club(
        name="Parent FC",
        reputation=60,
        league="Test League",
        country="England",
        balance=5_000_000,
        transfer_budget=2_000_000,
        wage_budget=40_000,
        matchday_revenue=80_000,
        stadium_capacity=25_000,
    )
    db_session.add(club)
    await db_session.commit()
    await db_session.refresh(club)
    return club


@pytest.fixture
async def test_career(db_session, test_user, test_club):
    """Create a test career."""
    career = Career(
        user_id=test_user.id,
        club_id=test_club.id,
        manager_name="Test Manager",
        current_season=1,
        current_week=5,  # During summer transfer window
        board_confidence=60,
        manager_reputation=50,
    )
    db_session.add(career)
    await db_session.commit()
    await db_session.refresh(career)
    return career


@pytest.fixture
async def test_player(db_session, parent_club):
    """Create a test player."""
    player = Player(
        uid="TEST001",
        name="Test Player",
        position="ST",
        age=22,
        nationality="England",
        club=parent_club.name,
        ca=130,
        pa=150,
        price="£1.5M",
        wage=4000,
        height=180,
        weight=75,
        left_foot=15,
        right_foot=10,
        # Technical attributes
        corners=12, crossing=13, dribbling=14, finishing=15,
        first_touch=14, free_kicks=11, heading=13, long_shots=12,
        long_throws=10, marking=8, passing=12, penalty=13,
        tackling=7, technique=14,
        # Mental attributes
        aggression=11, anticipation=13, bravery=12, composure=14,
        concentration=12, decisions=13, determination=14, flair=13,
        leadership=10, off_the_ball=14, positioning=13, teamwork=12,
        vision=12, work_rate=13,
        # Physical attributes
        acceleration=13, agility=12, balance=12, jumping=11,
        stamina=13, pace=13, endurance=13, strength=12,
    )
    db_session.add(player)
    await db_session.commit()
    await db_session.refresh(player)
    return player


@pytest.fixture
def transfer_service():
    """Create a transfer service instance."""
    return TransferService()


# ============================================================================
# Test Season-Long Loan During Open Window
# ============================================================================

@pytest.mark.asyncio
async def test_season_long_loan_during_open_window(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a season-long loan during an open transfer window."""
    # Career is at week 5 (summer window: weeks 1-8)
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=0.5,  # Pay 50% of wages
    )
    
    assert result["success"] is True
    # Result can be accepted or rejected based on probability
    assert "accepted" in result
    assert "message" in result
    assert result["loan_type"] == "season_long"


@pytest.mark.asyncio
async def test_season_long_loan_during_closed_window(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a season-long loan when transfer window is closed."""
    # Set career to week 15 (window closed)
    test_career.current_week = 15
    await db_session.commit()
    
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=0.5,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "window_closed"
    assert "window is closed" in result["message"].lower()


# ============================================================================
# Test Emergency Loan Outside Window
# ============================================================================

@pytest.mark.asyncio
async def test_emergency_loan_outside_window(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting an emergency loan outside transfer window."""
    # Set career to week 15 (window closed)
    test_career.current_week = 15
    await db_session.commit()
    
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="emergency",
        wage_contribution=0.75,  # Pay 75% of wages
        loan_duration_weeks=8,
    )
    
    assert result["success"] is True
    # Emergency loans should be possible outside windows
    assert "accepted" in result
    assert result["loan_type"] == "emergency"


@pytest.mark.asyncio
async def test_emergency_loan_without_duration(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting an emergency loan without specifying duration."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="emergency",
        wage_contribution=0.5,
        # Missing loan_duration_weeks
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "missing_duration"


@pytest.mark.asyncio
async def test_emergency_loan_duration_too_long(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting an emergency loan with duration > 12 weeks."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="emergency",
        wage_contribution=0.5,
        loan_duration_weeks=15,  # Exceeds 12 week limit
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "duration_too_long"


# ============================================================================
# Test Wage Contribution Validation
# ============================================================================

@pytest.mark.asyncio
async def test_loan_with_invalid_wage_contribution_negative(
    db_session, test_career, test_player, transfer_service
):
    """Test loan with negative wage contribution."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=-0.1,  # Invalid
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "invalid_wage_contribution"


@pytest.mark.asyncio
async def test_loan_with_invalid_wage_contribution_over_one(
    db_session, test_career, test_player, transfer_service
):
    """Test loan with wage contribution > 1.0."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=1.5,  # Invalid
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "invalid_wage_contribution"


@pytest.mark.asyncio
async def test_loan_with_zero_wage_contribution(
    db_session, test_career, test_player, transfer_service
):
    """Test loan with 0% wage contribution (parent club pays all)."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=0.0,  # Valid - parent club pays all
    )
    
    assert result["success"] is True
    # Lower wage contribution = lower acceptance chance
    assert "accepted" in result


@pytest.mark.asyncio
async def test_loan_with_full_wage_contribution(
    db_session, test_career, test_player, transfer_service
):
    """Test loan with 100% wage contribution (borrowing club pays all)."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=1.0,  # Valid - borrowing club pays all
    )
    
    assert result["success"] is True
    # Higher wage contribution = higher acceptance chance
    assert "accepted" in result


# ============================================================================
# Test Squad Size Validation
# ============================================================================

@pytest.mark.asyncio
async def test_loan_with_full_squad(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a loan when squad is full (40 players)."""
    # Create 40 dummy players in the squad
    for i in range(40):
        dummy_player = Player(
            uid=f"DUMMY{i:03d}",
            name=f"Dummy Player {i}",
            position="MF",
            age=20,
            nationality="England",
            club=test_career.club.name if hasattr(test_career, 'club') else "Test FC",
            ca=100,
            pa=120,
            price="£100K",
            wage=1000,
            height=175,
            weight=70,
            left_foot=10,
            right_foot=10,
            # Required attributes
            corners=10, crossing=10, dribbling=10, finishing=10,
            first_touch=10, free_kicks=10, heading=10, long_shots=10,
            long_throws=10, marking=10, passing=10, penalty=10,
            tackling=10, technique=10,
            aggression=10, anticipation=10, bravery=10, composure=10,
            concentration=10, decisions=10, determination=10, flair=10,
            leadership=10, off_the_ball=10, positioning=10, teamwork=10,
            vision=10, work_rate=10,
            acceleration=10, agility=10, balance=10, jumping=10,
            stamina=10, pace=10, endurance=10, strength=10,
        )
        db_session.add(dummy_player)
        await db_session.flush()
        
        squad_player = SquadPlayer(
            career_id=test_career.id,
            player_id=dummy_player.id,
            contract_start_date=date.today(),
            contract_end_date=date.today() + relativedelta(years=2),
            wage=1000,
            squad_number=i + 1,
            squad_status=SquadStatus.BACKUP,
            morale=70,
        )
        db_session.add(squad_player)
    
    await db_session.commit()
    
    # Try to add 41st player via loan
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=0.5,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "squad_full"
    assert "squad is full" in result["message"].lower()


# ============================================================================
# Test Player Already in Squad
# ============================================================================

@pytest.mark.asyncio
async def test_loan_player_already_in_squad(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a loan for a player already in the squad."""
    # Add player to squad first
    squad_player = SquadPlayer(
        career_id=test_career.id,
        player_id=test_player.id,
        contract_start_date=date.today(),
        contract_end_date=date.today() + relativedelta(years=2),
        wage=4000,
        squad_number=9,
        squad_status=SquadStatus.FIRST_TEAM,
        morale=75,
    )
    db_session.add(squad_player)
    await db_session.commit()
    
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=0.5,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "already_in_squad"
    assert "already in your squad" in result["message"].lower()


# ============================================================================
# Test Loan Transfer Record Creation
# ============================================================================

@pytest.mark.asyncio
async def test_loan_transfer_record_created(
    db_session, test_career, test_player, transfer_service
):
    """Test that a transfer record is created when loan is submitted."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="season_long",
        wage_contribution=0.6,
    )
    
    assert result["success"] is True
    assert "transfer_id" in result
    
    # Verify transfer record exists
    transfer_result = await db_session.execute(
        select(Transfer).where(Transfer.id == result["transfer_id"])
    )
    transfer = transfer_result.scalar_one_or_none()
    
    assert transfer is not None
    assert transfer.career_id == test_career.id
    assert transfer.player_id == test_player.id
    assert transfer.transfer_fee == 0  # No fee for loans
    assert transfer.wage_contribution == 0.6
    assert transfer.transfer_type == TransferType.LOAN
    assert transfer.season == test_career.current_season
    assert transfer.week == test_career.current_week


@pytest.mark.asyncio
async def test_emergency_loan_transfer_record_type(
    db_session, test_career, test_player, transfer_service
):
    """Test that emergency loan creates correct transfer type."""
    test_career.current_week = 15  # Outside window
    await db_session.commit()
    
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="emergency",
        wage_contribution=0.8,
        loan_duration_weeks=10,
    )
    
    assert result["success"] is True
    assert "transfer_id" in result
    
    # Verify transfer type is EMERGENCY_LOAN
    transfer_result = await db_session.execute(
        select(Transfer).where(Transfer.id == result["transfer_id"])
    )
    transfer = transfer_result.scalar_one_or_none()
    
    assert transfer.transfer_type == TransferType.EMERGENCY_LOAN
    assert transfer.loan_duration == 10


# ============================================================================
# Test Squad Player Creation on Acceptance
# ============================================================================

@pytest.mark.asyncio
async def test_squad_player_created_on_loan_acceptance(
    db_session, test_career, test_player, transfer_service
):
    """Test that a squad player record is created when loan is accepted."""
    # Run multiple times to get an accepted loan
    for _ in range(10):
        result = await transfer_service.submit_loan_offer_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            loan_type="season_long",
            wage_contribution=1.0,  # Full wage = higher acceptance chance
        )
        
        if result["accepted"]:
            assert "squad_player_id" in result
            assert "squad_number" in result
            assert "loan_return_date" in result
            
            # Verify squad player record exists
            squad_player_result = await db_session.execute(
                select(SquadPlayer).where(
                    SquadPlayer.id == result["squad_player_id"]
                )
            )
            squad_player = squad_player_result.scalar_one_or_none()
            
            assert squad_player is not None
            assert squad_player.career_id == test_career.id
            assert squad_player.player_id == test_player.id
            assert squad_player.squad_status == SquadStatus.FIRST_TEAM
            assert squad_player.morale == 70  # Default morale
            assert 1 <= squad_player.squad_number <= 99
            
            # Verify contract dates (loan return date)
            assert squad_player.contract_start_date == date.today()
            # Season-long loan should end at week 52
            expected_weeks = 52 - test_career.current_week
            expected_end = date.today() + relativedelta(weeks=expected_weeks)
            assert squad_player.contract_end_date == expected_end
            
            # Verify wage is only the contribution
            expected_wage = int(test_player.wage * 1.0)
            assert squad_player.wage == expected_wage
            break
        else:
            # Clean up rejected loan for next attempt
            await db_session.rollback()


# ============================================================================
# Test Loan Duration Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_season_long_loan_duration(
    db_session, test_career, test_player, transfer_service
):
    """Test that season-long loan duration is calculated correctly."""
    test_career.current_week = 10
    await db_session.commit()
    
    for _ in range(10):
        result = await transfer_service.submit_loan_offer_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            loan_type="season_long",
            wage_contribution=1.0,
        )
        
        if result["accepted"]:
            # Season-long loan: until end of season (week 52)
            expected_duration = 52 - 10  # 42 weeks
            assert result["loan_duration_weeks"] == expected_duration
            
            # Verify return date
            expected_return = date.today() + relativedelta(weeks=expected_duration)
            assert result["loan_return_date"] == expected_return.isoformat()
            break
        else:
            await db_session.rollback()


@pytest.mark.asyncio
async def test_emergency_loan_duration(
    db_session, test_career, test_player, transfer_service
):
    """Test that emergency loan duration is set correctly."""
    test_career.current_week = 15
    await db_session.commit()
    
    for _ in range(10):
        result = await transfer_service.submit_loan_offer_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            loan_type="emergency",
            wage_contribution=1.0,
            loan_duration_weeks=8,
        )
        
        if result["accepted"]:
            assert result["loan_duration_weeks"] == 8
            
            # Verify return date
            expected_return = date.today() + relativedelta(weeks=8)
            assert result["loan_return_date"] == expected_return.isoformat()
            break
        else:
            await db_session.rollback()


# ============================================================================
# Test Wage Cost Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_loan_wage_cost_calculation(
    db_session, test_career, test_player, transfer_service
):
    """Test that loan wage cost is calculated correctly based on contribution."""
    for _ in range(10):
        result = await transfer_service.submit_loan_offer_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            loan_type="season_long",
            wage_contribution=0.6,  # Pay 60% of wages
        )
        
        if result["accepted"]:
            # Player wage is 4000, contribution is 60%
            expected_wage_cost = int(4000 * 0.6)  # 2400
            assert result["wage_cost_per_week"] == expected_wage_cost
            
            # Total wage cost = wage_cost_per_week * duration
            total_cost = expected_wage_cost * result["loan_duration_weeks"]
            assert result["total_wage_cost"] == total_cost
            break
        else:
            await db_session.rollback()


# ============================================================================
# Test Get Active Loans
# ============================================================================

@pytest.mark.asyncio
async def test_get_active_loans(
    db_session, test_career, test_player, transfer_service
):
    """Test retrieving active loan players."""
    # Create an accepted loan
    for _ in range(10):
        result = await transfer_service.submit_loan_offer_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            loan_type="season_long",
            wage_contribution=1.0,
        )
        
        if result["accepted"]:
            break
        else:
            await db_session.rollback()
    
    # Get active loans
    active_loans = await transfer_service.get_active_loans(
        db=db_session,
        career_id=test_career.id,
    )
    
    assert len(active_loans) >= 1
    loan = active_loans[0]
    
    assert "player" in loan
    assert loan["player"]["name"] == test_player.name
    assert "parent_club" in loan
    assert "loan_type" in loan
    assert "loan_return_date" in loan
    assert "wage_contribution" in loan
    assert "squad_number" in loan


@pytest.mark.asyncio
async def test_get_active_loans_empty(
    db_session, test_career, transfer_service
):
    """Test retrieving active loans when there are none."""
    active_loans = await transfer_service.get_active_loans(
        db=db_session,
        career_id=test_career.id,
    )
    
    assert len(active_loans) == 0


# ============================================================================
# Test Loan Acceptance Probability
# ============================================================================

def test_loan_acceptance_probability_high_contribution(transfer_service):
    """Test loan acceptance probability with high wage contribution."""
    # Higher wage contribution should increase acceptance chance
    result = transfer_service.submit_loan_offer(
        career_week=5,
        current_squad_size=20,
        player_club_id=1,
        career_club_id=2,
        player_contract_months=24,
        loan_type="season_long",
        wage_contribution=1.0,  # Full wage
    )
    
    # Should have reasonable acceptance chance
    assert result.success is True


def test_loan_acceptance_probability_low_contribution(transfer_service):
    """Test loan acceptance probability with low wage contribution."""
    # Lower wage contribution should decrease acceptance chance
    result = transfer_service.submit_loan_offer(
        career_week=5,
        current_squad_size=20,
        player_club_id=1,
        career_club_id=2,
        player_contract_months=24,
        loan_type="season_long",
        wage_contribution=0.0,  # No wage contribution
    )
    
    # Should still be valid but lower acceptance chance
    assert result.success is True


def test_emergency_loan_acceptance_bonus(transfer_service):
    """Test that emergency loans have acceptance bonus."""
    # Emergency loans should have slightly higher acceptance
    result = transfer_service.submit_loan_offer(
        career_week=15,  # Outside window
        current_squad_size=20,
        player_club_id=1,
        career_club_id=2,
        player_contract_months=24,
        loan_type="emergency",
        wage_contribution=0.5,
    )
    
    assert result.success is True


# ============================================================================
# Test Invalid Loan Type
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_loan_type(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a loan with invalid loan type."""
    result = await transfer_service.submit_loan_offer_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        loan_type="invalid_type",
        wage_contribution=0.5,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert "rejection_reason" in result


# ============================================================================
# Test Short Contract Rejection
# ============================================================================

def test_loan_short_contract_rejection(transfer_service):
    """Test that loans are rejected for players with short contracts."""
    result = transfer_service.submit_loan_offer(
        career_week=5,
        current_squad_size=20,
        player_club_id=1,
        career_club_id=2,
        player_contract_months=5,  # Less than 6 months
        loan_type="season_long",
        wage_contribution=0.5,
    )
    
    assert result.success is False
    assert result.rejection_reason == "short_contract"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
