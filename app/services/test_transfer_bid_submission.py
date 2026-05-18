"""
Tests for Transfer Bid Submission System (Task 8.2)

This module tests the transfer bid submission functionality including:
- Transfer window validation
- Squad size validation
- Budget validation
- AI acceptance probability calculation
- Transfer record creation
- Squad player creation on acceptance
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
async def selling_club(db_session):
    """Create a selling club."""
    club = Club(
        name="Selling FC",
        reputation=45,
        league="Test League",
        country="England",
        balance=2_000_000,
        transfer_budget=1_000_000,
        wage_budget=30_000,
        matchday_revenue=50_000,
        stadium_capacity=20_000,
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
async def test_player(db_session, selling_club):
    """Create a test player."""
    player = Player(
        uid="TEST001",
        name="Test Player",
        position="ST",
        age=25,
        nationality="England",
        club=selling_club.name,
        ca=140,
        pa=160,
        price="£2.5M",
        wage=5000,
        height=180,
        weight=75,
        left_foot=15,
        right_foot=10,
        # Technical attributes
        corners=12, crossing=13, dribbling=14, finishing=16,
        first_touch=15, free_kicks=11, heading=14, long_shots=13,
        long_throws=10, marking=8, passing=13, penalty=14,
        tackling=7, technique=15,
        # Mental attributes
        aggression=12, anticipation=14, bravery=13, composure=15,
        concentration=13, decisions=14, determination=15, flair=14,
        leadership=11, off_the_ball=15, positioning=14, teamwork=13,
        vision=13, work_rate=14,
        # Physical attributes
        acceleration=14, agility=13, balance=13, jumping=12,
        stamina=14, pace=14, endurance=14, strength=13,
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
# Test Transfer Window Validation
# ============================================================================

@pytest.mark.asyncio
async def test_transfer_bid_during_open_window(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a transfer bid during an open transfer window."""
    # Career is at week 5 (summer window: weeks 1-8)
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is True
    # Result can be accepted or rejected based on probability
    assert "accepted" in result
    assert "message" in result


@pytest.mark.asyncio
async def test_transfer_bid_during_closed_window(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a transfer bid when transfer window is closed."""
    # Set career to week 15 (window closed)
    test_career.current_week = 15
    await db_session.commit()
    
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "window_closed"
    assert "window is closed" in result["message"].lower()


@pytest.mark.asyncio
async def test_transfer_bid_during_winter_window(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a transfer bid during winter transfer window."""
    # Set career to week 27 (winter window: weeks 26-30)
    test_career.current_week = 27
    await db_session.commit()
    
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is True
    assert "accepted" in result


# ============================================================================
# Test Squad Size Validation
# ============================================================================

@pytest.mark.asyncio
async def test_transfer_bid_with_full_squad(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a transfer bid when squad is full (40 players)."""
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
    
    # Try to add 41st player
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "squad_full"
    assert "squad is full" in result["message"].lower()


# ============================================================================
# Test Budget Validation
# ============================================================================

@pytest.mark.asyncio
async def test_transfer_bid_insufficient_budget(
    db_session, test_career, test_club, test_player, transfer_service
):
    """Test submitting a transfer bid with insufficient budget."""
    # Set club budget to less than bid amount
    test_club.transfer_budget = 1_000_000
    await db_session.commit()
    
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,  # More than available budget
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "insufficient_budget"
    assert "insufficient" in result["message"].lower()


@pytest.mark.asyncio
async def test_transfer_bid_with_sufficient_budget(
    db_session, test_career, test_club, test_player, transfer_service
):
    """Test submitting a transfer bid with sufficient budget."""
    # Ensure club has enough budget
    test_club.transfer_budget = 5_000_000
    await db_session.commit()
    
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is True
    # Budget should be deducted if accepted
    if result["accepted"]:
        await db_session.refresh(test_club)
        assert test_club.transfer_budget == 2_500_000  # 5M - 2.5M


# ============================================================================
# Test Player Already in Squad
# ============================================================================

@pytest.mark.asyncio
async def test_transfer_bid_player_already_in_squad(
    db_session, test_career, test_player, transfer_service
):
    """Test submitting a transfer bid for a player already in the squad."""
    # Add player to squad first
    squad_player = SquadPlayer(
        career_id=test_career.id,
        player_id=test_player.id,
        contract_start_date=date.today(),
        contract_end_date=date.today() + relativedelta(years=2),
        wage=5000,
        squad_number=9,
        squad_status=SquadStatus.FIRST_TEAM,
        morale=75,
    )
    db_session.add(squad_player)
    await db_session.commit()
    
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    assert result["success"] is False
    assert result["accepted"] is False
    assert result["rejection_reason"] == "already_in_squad"
    assert "already in your squad" in result["message"].lower()


# ============================================================================
# Test AI Acceptance Probability
# ============================================================================

def test_acceptance_probability_high_bid(transfer_service):
    """Test acceptance probability with a high bid (150% of market value)."""
    probability = transfer_service.calculate_acceptance_probability(
        bid_amount=3_750_000,  # 150% of market value
        market_value=2_500_000,
        selling_club_balance=1_000_000,
        contract_months=12,
        player_status="FIRST_TEAM",
    )
    
    # Should have high probability (>= 0.6 base + bonuses)
    assert probability >= 0.6


def test_acceptance_probability_low_bid(transfer_service):
    """Test acceptance probability with a low bid (70% of market value)."""
    probability = transfer_service.calculate_acceptance_probability(
        bid_amount=1_750_000,  # 70% of market value
        market_value=2_500_000,
        selling_club_balance=1_000_000,
        contract_months=24,
        player_status="KEY_PLAYER",
    )
    
    # Should be rejected (lowball offer)
    assert probability == 0.0


def test_acceptance_probability_desperate_club(transfer_service):
    """Test acceptance probability when selling club is in financial trouble."""
    probability = transfer_service.calculate_acceptance_probability(
        bid_amount=2_500_000,  # 100% of market value
        market_value=2_500_000,
        selling_club_balance=-500_000,  # Negative balance
        contract_months=6,  # Contract expiring soon
        player_status="NOT_NEEDED",
    )
    
    # Should have very high probability due to multiple factors
    # Base: 0.2 (100% value) + 0.2 (negative balance) + 0.3 (6 months) + 0.2 (not needed) = 0.9
    assert probability >= 0.8


def test_acceptance_probability_key_player(transfer_service):
    """Test acceptance probability for a key player."""
    probability = transfer_service.calculate_acceptance_probability(
        bid_amount=2_500_000,  # 100% of market value
        market_value=2_500_000,
        selling_club_balance=5_000_000,  # Healthy balance
        contract_months=36,  # Long contract
        player_status="KEY_PLAYER",
    )
    
    # Should have low probability due to key player status
    # Base: 0.2 (100% value) - 0.2 (key player) = 0.0
    assert probability <= 0.2


# ============================================================================
# Test Transfer Record Creation
# ============================================================================

@pytest.mark.asyncio
async def test_transfer_record_created(
    db_session, test_career, test_player, transfer_service
):
    """Test that a transfer record is created when bid is submitted."""
    result = await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
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
    assert transfer.transfer_fee == 2_500_000
    assert transfer.wage_offer == 6_000
    assert transfer.contract_length == 3
    assert transfer.transfer_type == TransferType.PERMANENT
    assert transfer.season == test_career.current_season
    assert transfer.week == test_career.current_week


@pytest.mark.asyncio
async def test_transfer_status_accepted(
    db_session, test_career, test_player, transfer_service
):
    """Test transfer status when bid is accepted."""
    # Run multiple times to get an accepted bid (probability-based)
    for _ in range(10):
        result = await transfer_service.submit_transfer_bid_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            bid_amount=3_750_000,  # High bid for better acceptance chance
            wage_offer=6_000,
            contract_length=3,
        )
        
        if result["accepted"]:
            # Verify transfer status is COMPLETED
            transfer_result = await db_session.execute(
                select(Transfer).where(Transfer.id == result["transfer_id"])
            )
            transfer = transfer_result.scalar_one_or_none()
            
            assert transfer.transfer_status == TransferStatus.COMPLETED
            assert transfer.completion_date is not None
            break
        else:
            # Clean up rejected transfer for next attempt
            await db_session.rollback()


# ============================================================================
# Test Squad Player Creation on Acceptance
# ============================================================================

@pytest.mark.asyncio
async def test_squad_player_created_on_acceptance(
    db_session, test_career, test_player, transfer_service
):
    """Test that a squad player record is created when bid is accepted."""
    # Run multiple times to get an accepted bid
    for _ in range(10):
        result = await transfer_service.submit_transfer_bid_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            bid_amount=3_750_000,  # High bid
            wage_offer=6_000,
            contract_length=3,
        )
        
        if result["accepted"]:
            assert "squad_player_id" in result
            assert "squad_number" in result
            
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
            assert squad_player.wage == 6_000
            assert squad_player.squad_status == SquadStatus.FIRST_TEAM
            assert squad_player.morale == 70  # Default morale
            assert 1 <= squad_player.squad_number <= 99
            
            # Verify contract dates
            assert squad_player.contract_start_date == date.today()
            expected_end = date.today() + relativedelta(years=3)
            assert squad_player.contract_end_date == expected_end
            break
        else:
            # Clean up rejected transfer for next attempt
            await db_session.rollback()


# ============================================================================
# Test Budget Deduction on Acceptance
# ============================================================================

@pytest.mark.asyncio
async def test_budget_deducted_on_acceptance(
    db_session, test_career, test_club, test_player, transfer_service
):
    """Test that transfer budget is deducted when bid is accepted."""
    initial_budget = test_club.transfer_budget
    initial_spend = test_career.total_transfer_spend
    
    # Run multiple times to get an accepted bid
    for _ in range(10):
        result = await transfer_service.submit_transfer_bid_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            bid_amount=2_500_000,
            wage_offer=6_000,
            contract_length=3,
        )
        
        if result["accepted"]:
            await db_session.refresh(test_club)
            await db_session.refresh(test_career)
            
            # Verify budget deduction
            assert test_club.transfer_budget == initial_budget - 2_500_000
            assert result["new_transfer_budget"] == test_club.transfer_budget
            
            # Verify career total spend updated
            assert test_career.total_transfer_spend == initial_spend + 2_500_000
            break
        else:
            # Clean up rejected transfer for next attempt
            await db_session.rollback()


# ============================================================================
# Test Price Parsing
# ============================================================================

def test_parse_price_millions(transfer_service):
    """Test parsing price in millions."""
    assert transfer_service._parse_price_to_int("£2.5M") == 2_500_000
    assert transfer_service._parse_price_to_int("£10M") == 10_000_000
    assert transfer_service._parse_price_to_int("$5.75M") == 5_750_000


def test_parse_price_thousands(transfer_service):
    """Test parsing price in thousands."""
    assert transfer_service._parse_price_to_int("£500K") == 500_000
    assert transfer_service._parse_price_to_int("£250K") == 250_000
    assert transfer_service._parse_price_to_int("$750K") == 750_000


def test_parse_price_plain_number(transfer_service):
    """Test parsing plain number price."""
    assert transfer_service._parse_price_to_int("1000000") == 1_000_000
    assert transfer_service._parse_price_to_int("500000") == 500_000


def test_parse_price_invalid(transfer_service):
    """Test parsing invalid price."""
    assert transfer_service._parse_price_to_int("") == 0
    assert transfer_service._parse_price_to_int("invalid") == 0
    assert transfer_service._parse_price_to_int(None) == 0


# ============================================================================
# Test Transfer History
# ============================================================================

@pytest.mark.asyncio
async def test_get_transfer_bid_history(
    db_session, test_career, test_player, transfer_service
):
    """Test retrieving transfer bid history."""
    # Submit a few bids
    for i in range(3):
        await transfer_service.submit_transfer_bid_async(
            db=db_session,
            career_id=test_career.id,
            player_id=test_player.id,
            bid_amount=2_000_000 + (i * 500_000),
            wage_offer=5_000 + (i * 1_000),
            contract_length=3,
        )
    
    # Get history
    history = await transfer_service.get_transfer_bid_history(
        db=db_session,
        career_id=test_career.id,
    )
    
    assert len(history) >= 3
    assert all("player" in record for record in history)
    assert all("from_club_name" in record for record in history)
    assert all("to_club_name" in record for record in history)


@pytest.mark.asyncio
async def test_get_transfer_bid_history_filtered_by_season(
    db_session, test_career, test_player, transfer_service
):
    """Test retrieving transfer bid history filtered by season."""
    # Submit bid in season 1
    await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=2_500_000,
        wage_offer=6_000,
        contract_length=3,
    )
    
    # Change to season 2 and submit another bid
    test_career.current_season = 2
    await db_session.commit()
    
    await transfer_service.submit_transfer_bid_async(
        db=db_session,
        career_id=test_career.id,
        player_id=test_player.id,
        bid_amount=3_000_000,
        wage_offer=7_000,
        contract_length=3,
    )
    
    # Get history for season 1 only
    history_season_1 = await transfer_service.get_transfer_bid_history(
        db=db_session,
        career_id=test_career.id,
        season=1,
    )
    
    assert len(history_season_1) >= 1
    assert all(record["season"] == 1 for record in history_season_1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
