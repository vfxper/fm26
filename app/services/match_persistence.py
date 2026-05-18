"""
Match Persistence Service - Database persistence for match results

This module provides functions to persist match simulation results to the database,
including match records, events, statistics, player ratings, and injuries.

Key Features:
- Atomic transaction handling for match data persistence
- Batch insertion of match events for performance
- Injury record creation with proper foreign key relationships
- Player ratings stored as JSON
- Comprehensive error handling and logging
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.models.match import Match, MatchStatus, WeatherCondition, PitchCondition
from app.models.match_event import MatchEvent, EventType, TeamSide
from app.models.injury import Injury, InjurySeverity, InjuryStatus
from app.services.match_simulator import MatchResult, InjuryEvent

logger = logging.getLogger(__name__)


async def save_match_result(
    session: AsyncSession,
    result: MatchResult,
    career_id: int,
    home_club_id: int,
    away_club_id: int,
    match_date: datetime,
    competition: str,
    venue: Optional[str] = None,
    weather: WeatherCondition = WeatherCondition.CLEAR,
    pitch_condition: PitchCondition = PitchCondition.GOOD,
    attendance: int = 0,
    home_advantage_applied: bool = True,
    season: int = 1,
    week: int = 1
) -> Match:
    """
    Save complete match result to database.
    
    Persists match record, all events, statistics, player ratings, and injuries
    in a single atomic transaction. If any part fails, the entire transaction
    is rolled back.
    
    Args:
        session: Async database session
        result: MatchResult object from match simulator
        career_id: Career ID for this match
        home_club_id: Home club ID
        away_club_id: Away club ID
        match_date: Date and time of the match
        competition: Competition name (e.g., "Premier League", "FA Cup")
        venue: Stadium name (optional)
        weather: Weather condition during match
        pitch_condition: Pitch quality during match
        attendance: Number of spectators
        home_advantage_applied: Whether home advantage was applied
        season: Season number (for injury tracking)
        week: Week number (for injury tracking)
    
    Returns:
        Match: Persisted Match object with ID
    
    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        # Create Match record
        match = Match(
            career_id=career_id,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            # Match Result
            home_score=result.home_score,
            away_score=result.away_score,
            # Match Metadata
            match_date=match_date,
            competition=competition,
            venue=venue,
            weather=weather,
            pitch_condition=pitch_condition,
            attendance=attendance,
            # Match Statistics
            home_possession=result.home_statistics.get("possession", 50),
            away_possession=result.away_statistics.get("possession", 50),
            home_shots=result.home_statistics.get("shots", 0),
            away_shots=result.away_statistics.get("shots", 0),
            home_shots_on_target=result.home_statistics.get("shots_on_target", 0),
            away_shots_on_target=result.away_statistics.get("shots_on_target", 0),
            home_passes=result.home_statistics.get("passes", 0),
            away_passes=result.away_statistics.get("passes", 0),
            home_pass_accuracy=result.home_statistics.get("pass_accuracy", 0),
            away_pass_accuracy=result.away_statistics.get("pass_accuracy", 0),
            home_tackles=result.home_statistics.get("tackles", 0),
            away_tackles=result.away_statistics.get("tackles", 0),
            home_fouls=result.home_statistics.get("fouls", 0),
            away_fouls=result.away_statistics.get("fouls", 0),
            home_yellow_cards=result.home_statistics.get("yellow_cards", 0),
            away_yellow_cards=result.away_statistics.get("yellow_cards", 0),
            home_red_cards=result.home_statistics.get("red_cards", 0),
            away_red_cards=result.away_statistics.get("red_cards", 0),
            # Match Duration
            match_duration=result.match_duration,
            extra_time_played=(result.match_duration > 90),
            # Home Advantage
            home_advantage_applied=home_advantage_applied,
            # Player Ratings (JSON)
            player_ratings=json.dumps(result.player_ratings) if result.player_ratings else None,
            # Match Status
            status=MatchStatus.COMPLETED
        )
        
        session.add(match)
        await session.flush()  # Flush to get match.id
        
        logger.info(
            f"Created match record: ID={match.id}, "
            f"score={match.home_score}-{match.away_score}, "
            f"competition={competition}"
        )
        
        # Save match events (batch insert for performance)
        if result.events:
            match_events = []
            for event_data in result.events:
                match_event = MatchEvent(
                    match_id=match.id,
                    event_type=EventType(event_data["event_type"]),
                    team=TeamSide(event_data["team"]),
                    minute=event_data["minute"],
                    second=event_data.get("second", 0),
                    player_id=event_data["player_id"],
                    target_player_id=event_data.get("target_player_id"),
                    position_x=event_data["position_x"],
                    position_y=event_data["position_y"],
                    success=event_data.get("success", False),
                    event_metadata=json.dumps(event_data.get("metadata")) if event_data.get("metadata") else None
                )
                match_events.append(match_event)
            
            session.add_all(match_events)
            logger.info(f"Created {len(match_events)} match events for match ID={match.id}")
        
        # Save injuries
        if result.injuries:
            injuries = []
            for injury_event in result.injuries:
                # Map severity string to enum
                severity_map = {
                    "minor": InjurySeverity.MINOR,
                    "moderate": InjurySeverity.MODERATE,
                    "severe": InjurySeverity.SEVERE
                }
                severity = severity_map.get(injury_event.severity.lower(), InjurySeverity.MINOR)
                
                # Calculate expected recovery date
                from datetime import timedelta
                recovery_days = injury_event.recovery_weeks * 7
                expected_recovery_date = match_date + timedelta(days=recovery_days)
                
                injury = Injury(
                    career_id=career_id,
                    player_id=injury_event.player_id,
                    squad_player_id=injury_event.squad_player_id,
                    injury_type=injury_event.injury_type,
                    injury_description=injury_event.injury_description,
                    severity=severity,
                    status=InjuryStatus.ACTIVE,
                    injury_date=match_date,
                    expected_recovery_date=expected_recovery_date,
                    recovery_weeks=injury_event.recovery_weeks,
                    occurred_in_match_id=match.id,
                    match_minute=injury_event.match_minute,
                    season=season,
                    week=week,
                    sharpness_penalty=10  # Standard 10% penalty
                )
                injuries.append(injury)
            
            session.add_all(injuries)
            logger.info(f"Created {len(injuries)} injury records for match ID={match.id}")
            
            # Set injured players' training to REHABILITATION
            from app.services.training_service import TrainingService
            training_service = TrainingService(session)
            for injury_event in result.injuries:
                await training_service.set_player_injured(
                    career_id=career_id,
                    squad_player_id=injury_event.squad_player_id,
                    season=season,
                    week=week
                )
        
        # Commit transaction
        await session.commit()
        
        logger.info(
            f"Successfully persisted match ID={match.id} with "
            f"{len(result.events)} events and {len(result.injuries)} injuries"
        )
        
        return match
        
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Failed to persist match result: {e}", exc_info=True)
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error persisting match result: {e}", exc_info=True)
        raise


async def get_match_with_events(
    session: AsyncSession,
    match_id: int
) -> Optional[Dict]:
    """
    Retrieve match with all events.
    
    Args:
        session: Async database session
        match_id: Match ID to retrieve
    
    Returns:
        Dict with match data and events, or None if not found
    """
    from sqlalchemy import select
    
    try:
        # Get match
        result = await session.execute(
            select(Match).where(Match.id == match_id)
        )
        match = result.scalar_one_or_none()
        
        if not match:
            return None
        
        # Get events
        result = await session.execute(
            select(MatchEvent)
            .where(MatchEvent.match_id == match_id)
            .order_by(MatchEvent.minute, MatchEvent.second)
        )
        events = result.scalars().all()
        
        return {
            "match": match.to_dict(),
            "events": [event.to_dict() for event in events]
        }
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve match {match_id}: {e}", exc_info=True)
        raise


async def get_career_matches(
    session: AsyncSession,
    career_id: int,
    limit: int = 10,
    offset: int = 0
) -> List[Match]:
    """
    Retrieve matches for a career.
    
    Args:
        session: Async database session
        career_id: Career ID
        limit: Maximum number of matches to return
        offset: Number of matches to skip
    
    Returns:
        List of Match objects
    """
    from sqlalchemy import select
    
    try:
        result = await session.execute(
            select(Match)
            .where(Match.career_id == career_id)
            .order_by(Match.match_date.desc())
            .limit(limit)
            .offset(offset)
        )
        matches = result.scalars().all()
        return list(matches)
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve career matches: {e}", exc_info=True)
        raise


async def get_player_match_events(
    session: AsyncSession,
    player_id: int,
    limit: int = 100
) -> List[MatchEvent]:
    """
    Retrieve recent match events for a player.
    
    Args:
        session: Async database session
        player_id: Player ID
        limit: Maximum number of events to return
    
    Returns:
        List of MatchEvent objects
    """
    from sqlalchemy import select, or_
    
    try:
        result = await session.execute(
            select(MatchEvent)
            .where(
                or_(
                    MatchEvent.player_id == player_id,
                    MatchEvent.target_player_id == player_id
                )
            )
            .order_by(MatchEvent.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        return list(events)
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to retrieve player events: {e}", exc_info=True)
        raise
