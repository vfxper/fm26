"""
Tests for MatchEvent Model
"""

import pytest
from datetime import datetime
from sqlalchemy import select, inspect

from app.models.match_event import MatchEvent, EventType, TeamSide
from app.models.match import Match, MatchStatus
from app.models.player import Player
from app.models.club import Club


@pytest.mark.asyncio
async def test_match_event_table_exists(test_db_session):
    """Test that match_events table exists in database"""
    # Get inspector to check table existence
    inspector = inspect(test_db_session.bind)
    
    # Check if match_events table exists
    tables = await test_db_session.run_sync(lambda sync_session: inspector.get_table_names())
    assert "match_events" in tables, "match_events table should exist"


@pytest.mark.asyncio
async def test_match_event_columns(test_db_session):
    """Test that match_events table has all required columns"""
    inspector = inspect(test_db_session.bind)
    
    # Get columns for match_events table
    columns = await test_db_session.run_sync(
        lambda sync_session: [col["name"] for col in inspector.get_columns("match_events")]
    )
    
    # Check required columns exist
    required_columns = [
        "id", "match_id", "player_id", "target_player_id",
        "event_type", "team", "minute", "second",
        "position_x", "position_y", "success", "metadata", "created_at"
    ]
    
    for col in required_columns:
        assert col in columns, f"Column '{col}' should exist in match_events table"


@pytest.mark.asyncio
async def test_match_event_indexes(test_db_session):
    """Test that match_events table has proper indexes"""
    inspector = inspect(test_db_session.bind)
    
    # Get indexes for match_events table
    indexes = await test_db_session.run_sync(
        lambda sync_session: inspector.get_indexes("match_events")
    )
    
    # Check that indexes exist
    index_names = [idx["name"] for idx in indexes]
    
    expected_indexes = [
        "idx_match_events_match_id",
        "idx_match_events_player_id",
        "idx_match_events_event_type",
        "idx_match_events_team",
        "idx_match_events_minute",
    ]
    
    for idx_name in expected_indexes:
        assert idx_name in index_names, f"Index '{idx_name}' should exist"


@pytest.mark.asyncio
async def test_create_match_event(test_db_session):
    """Test creating a match event record"""
    # Create test club
    club1 = Club(
        name="Test FC",
        country="England",
        league="Premier League",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=100000
    )
    club2 = Club(
        name="Opponent FC",
        country="England",
        league="Premier League",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=100000
    )
    test_db_session.add(club1)
    test_db_session.add(club2)
    await test_db_session.flush()
    
    # Create test match
    match = Match(
        home_club_id=club1.id,
        away_club_id=club2.id,
        match_date=datetime.now(),
        competition="Premier League",
        status=MatchStatus.IN_PROGRESS
    )
    test_db_session.add(match)
    await test_db_session.flush()
    
    # Create test player
    player = Player(
        uid="TEST001",
        name="Test Player",
        position="ST",
        age=25,
        ca=150,
        pa=180,
        nationality="England",
        club="Test FC",
        # Technical attributes
        corners=10, crossing=10, dribbling=15, finishing=18,
        first_touch=15, free_kicks=10, heading=12, long_shots=14,
        long_throws=8, marking=8, passing=14, penalty=16,
        tackling=8, technique=15,
        # Mental attributes
        aggression=12, anticipation=15, bravery=14, composure=16,
        concentration=14, decisions=15, determination=16, flair=14,
        leadership=12, off_the_ball=17, positioning=16, teamwork=14,
        vision=14, work_rate=15,
        # Physical attributes
        acceleration=16, agility=15, balance=14, jumping=13,
        stamina=15, pace=16, endurance=15, strength=14,
        # Financial
        price="10M",
        wage=50000,
        # Physical stats
        height=180,
        weight=75,
        left_foot=8,
        right_foot=18
    )
    test_db_session.add(player)
    await test_db_session.flush()
    
    # Create match event
    event = MatchEvent(
        match_id=match.id,
        player_id=player.id,
        event_type=EventType.SHOT,
        team=TeamSide.HOME,
        minute=45,
        second=30,
        position_x=85.0,
        position_y=50.0,
        success=True,
        event_metadata='{"shot_power": 85, "shot_type": "right_foot"}'
    )
    
    test_db_session.add(event)
    await test_db_session.commit()
    
    # Verify event was created
    result = await test_db_session.execute(
        select(MatchEvent).where(MatchEvent.id == event.id)
    )
    saved_event = result.scalar_one()
    
    assert saved_event is not None
    assert saved_event.match_id == match.id
    assert saved_event.player_id == player.id
    assert saved_event.event_type == EventType.SHOT
    assert saved_event.team == TeamSide.HOME
    assert saved_event.minute == 45
    assert saved_event.second == 30
    assert saved_event.position_x == 85.0
    assert saved_event.position_y == 50.0
    assert saved_event.success is True


@pytest.mark.asyncio
async def test_match_event_relationships(test_db_session):
    """Test that match event foreign keys work correctly"""
    # Create test clubs
    club1 = Club(
        name="Home FC",
        country="England",
        league="Premier League",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=100000
    )
    club2 = Club(
        name="Away FC",
        country="England",
        league="Premier League",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=100000
    )
    test_db_session.add_all([club1, club2])
    await test_db_session.flush()
    
    # Create test match
    match = Match(
        home_club_id=club1.id,
        away_club_id=club2.id,
        match_date=datetime.now(),
        competition="Premier League",
        status=MatchStatus.COMPLETED
    )
    test_db_session.add(match)
    await test_db_session.flush()
    
    # Create test players
    player1 = Player(
        uid="PLAYER001",
        name="Striker",
        position="ST",
        age=25,
        ca=150,
        pa=180,
        nationality="England",
        club="Home FC",
        corners=10, crossing=10, dribbling=15, finishing=18,
        first_touch=15, free_kicks=10, heading=12, long_shots=14,
        long_throws=8, marking=8, passing=14, penalty=16,
        tackling=8, technique=15,
        aggression=12, anticipation=15, bravery=14, composure=16,
        concentration=14, decisions=15, determination=16, flair=14,
        leadership=12, off_the_ball=17, positioning=16, teamwork=14,
        vision=14, work_rate=15,
        acceleration=16, agility=15, balance=14, jumping=13,
        stamina=15, pace=16, endurance=15, strength=14,
        price="10M",
        wage=50000,
        height=180,
        weight=75,
        left_foot=8,
        right_foot=18
    )
    
    player2 = Player(
        uid="PLAYER002",
        name="Midfielder",
        position="CM",
        age=26,
        ca=140,
        pa=160,
        nationality="England",
        club="Home FC",
        corners=12, crossing=12, dribbling=14, finishing=10,
        first_touch=16, free_kicks=12, heading=10, long_shots=12,
        long_throws=8, marking=12, passing=17, penalty=12,
        tackling=14, technique=16,
        aggression=10, anticipation=16, bravery=12, composure=15,
        concentration=16, decisions=17, determination=15, flair=12,
        leadership=14, off_the_ball=12, positioning=15, teamwork=17,
        vision=18, work_rate=16,
        acceleration=14, agility=14, balance=15, jumping=11,
        stamina=16, pace=14, endurance=16, strength=13,
        price="8M",
        wage=40000,
        height=178,
        weight=72,
        left_foot=15,
        right_foot=16
    )
    
    test_db_session.add_all([player1, player2])
    await test_db_session.flush()
    
    # Create pass event from player2 to player1
    pass_event = MatchEvent(
        match_id=match.id,
        player_id=player2.id,
        target_player_id=player1.id,
        event_type=EventType.PASS,
        team=TeamSide.HOME,
        minute=30,
        second=15,
        position_x=60.0,
        position_y=45.0,
        success=True,
        event_metadata='{"pass_distance": 25, "pass_type": "through_ball"}'
    )
    
    test_db_session.add(pass_event)
    await test_db_session.commit()
    
    # Verify relationships
    result = await test_db_session.execute(
        select(MatchEvent).where(MatchEvent.id == pass_event.id)
    )
    saved_event = result.scalar_one()
    
    assert saved_event.match_id == match.id
    assert saved_event.player_id == player2.id
    assert saved_event.target_player_id == player1.id


@pytest.mark.asyncio
async def test_match_event_helper_methods(test_db_session):
    """Test MatchEvent helper methods"""
    # Create minimal test data
    club1 = Club(
        name="Test FC",
        country="England",
        league="Premier League",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=100000
    )
    club2 = Club(
        name="Opponent FC",
        country="England",
        league="Premier League",
        reputation=50,
        balance=1000000,
        transfer_budget=500000,
        wage_budget=100000
    )
    test_db_session.add_all([club1, club2])
    await test_db_session.flush()
    
    match = Match(
        home_club_id=club1.id,
        away_club_id=club2.id,
        match_date=datetime.now(),
        competition="Premier League",
        status=MatchStatus.COMPLETED
    )
    test_db_session.add(match)
    await test_db_session.flush()
    
    player = Player(
        uid="TEST001",
        name="Test Player",
        position="ST",
        age=25,
        ca=150,
        pa=180,
        nationality="England",
        club="Test FC",
        corners=10, crossing=10, dribbling=15, finishing=18,
        first_touch=15, free_kicks=10, heading=12, long_shots=14,
        long_throws=8, marking=8, passing=14, penalty=16,
        tackling=8, technique=15,
        aggression=12, anticipation=15, bravery=14, composure=16,
        concentration=14, decisions=15, determination=16, flair=14,
        leadership=12, off_the_ball=17, positioning=16, teamwork=14,
        vision=14, work_rate=15,
        acceleration=16, agility=15, balance=14, jumping=13,
        stamina=15, pace=16, endurance=15, strength=14,
        price="10M",
        wage=50000,
        height=180,
        weight=75,
        left_foot=8,
        right_foot=18
    )
    test_db_session.add(player)
    await test_db_session.flush()
    
    # Test goal event
    goal_event = MatchEvent(
        match_id=match.id,
        player_id=player.id,
        event_type=EventType.GOAL,
        team=TeamSide.HOME,
        minute=45,
        second=30,
        position_x=95.0,
        position_y=50.0,
        success=True
    )
    
    assert goal_event.is_goal_event() is True
    assert goal_event.is_card_event() is False
    assert goal_event.is_attacking_event() is True
    assert goal_event.get_time_string() == "45:30"
    assert goal_event.is_in_first_half() is True
    assert goal_event.is_in_second_half() is False
    assert goal_event.get_position_zone() == "attacking_third"
    
    # Test yellow card event
    card_event = MatchEvent(
        match_id=match.id,
        player_id=player.id,
        event_type=EventType.YELLOW_CARD,
        team=TeamSide.HOME,
        minute=60,
        second=0,
        position_x=30.0,
        position_y=20.0,
        success=True
    )
    
    assert card_event.is_card_event() is True
    assert card_event.is_goal_event() is False
    assert card_event.is_in_second_half() is True
    assert card_event.get_position_zone() == "defensive_third"
    assert card_event.get_position_side() == "left"
