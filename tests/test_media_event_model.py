"""
Unit tests for MediaEvent model
"""

import pytest
from datetime import datetime, timedelta
from app.models.media_event import MediaEvent, MediaEventType, MediaEventStatus


def test_media_event_creation():
    """Test basic MediaEvent creation"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.PRE_MATCH_CONFERENCE,
        event_question="How do you feel about the upcoming match?",
        response_options='[{"text": "We are confident", "reputation_impact": 2}]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    assert event.career_id == 1
    assert event.event_type == MediaEventType.PRE_MATCH_CONFERENCE
    assert event.event_status == MediaEventStatus.PENDING
    assert event.is_pending()
    assert not event.is_responded()


def test_media_event_type_checks():
    """Test event type checking methods"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.POST_MATCH_CONFERENCE,
        event_question="What are your thoughts on the result?",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    assert event.is_post_match_conference()
    assert not event.is_pre_match_conference()
    assert not event.is_player_interview()
    assert not event.is_media_pressure()
    assert not event.is_rival_comment()


def test_media_event_respond():
    """Test responding to a media event"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.PRE_MATCH_CONFERENCE,
        event_question="Test question",
        response_options='[{"text": "Option 1"}, {"text": "Option 2"}]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    assert event.is_pending()
    assert event.selected_response is None
    
    event.respond(1, '{"player_1": 5}')
    
    assert event.is_responded()
    assert event.selected_response == 1
    assert event.morale_impact == '{"player_1": 5}'


def test_media_event_expire():
    """Test expiring a media event"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.PLAYER_INTERVIEW,
        event_question="Test question",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    assert event.is_pending()
    
    event.expire()
    
    assert event.is_expired()
    assert not event.is_pending()


def test_media_event_impact_checks():
    """Test impact checking methods"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.MEDIA_PRESSURE,
        event_question="Test question",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24),
        reputation_impact=5,
        board_confidence_impact=-3
    )
    
    assert event.has_positive_reputation_impact()
    assert not event.has_negative_reputation_impact()
    assert event.has_negative_board_impact()
    assert not event.has_positive_board_impact()


def test_media_event_set_impacts():
    """Test setting impact values with bounds checking"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.RIVAL_COMMENT,
        event_question="Test question",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    # Test reputation impact bounds
    event.set_reputation_impact(15)  # Should be clamped to 10
    assert event.reputation_impact == 10
    
    event.set_reputation_impact(-15)  # Should be clamped to -10
    assert event.reputation_impact == -10
    
    # Test board confidence impact bounds
    event.set_board_confidence_impact(8)
    assert event.board_confidence_impact == 8
    
    event.set_board_confidence_impact(-12)  # Should be clamped to -10
    assert event.board_confidence_impact == -10


def test_media_event_to_dict():
    """Test converting MediaEvent to dictionary"""
    now = datetime.now()
    expiry = now + timedelta(hours=24)
    
    event = MediaEvent(
        career_id=1,
        match_id=5,
        event_type=MediaEventType.PRE_MATCH_CONFERENCE,
        event_question="Test question",
        response_options='[{"text": "Option 1"}]',
        event_date=now,
        expiry_date=expiry,
        reputation_impact=3,
        board_confidence_impact=-1
    )
    
    event_dict = event.to_dict()
    
    assert event_dict["career_id"] == 1
    assert event_dict["match_id"] == 5
    assert event_dict["event"]["type"] == "pre_match_conference"
    assert event_dict["event"]["question"] == "Test question"
    assert event_dict["event"]["status"] == "pending"
    assert event_dict["impact"]["reputation_impact"] == 3
    assert event_dict["impact"]["board_confidence_impact"] == -1


def test_media_event_display_names():
    """Test display name methods"""
    event = MediaEvent(
        career_id=1,
        event_type=MediaEventType.PLAYER_INTERVIEW,
        event_question="Test question",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    assert event.get_event_type_display_name() == "Player Interview"
    assert event.get_status_display_name() == "Pending Response"
    
    event.respond(0)
    assert event.get_status_display_name() == "Responded"


def test_media_event_match_related():
    """Test match-related event checking"""
    event_with_match = MediaEvent(
        career_id=1,
        match_id=10,
        event_type=MediaEventType.POST_MATCH_CONFERENCE,
        event_question="Test question",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    event_without_match = MediaEvent(
        career_id=1,
        event_type=MediaEventType.MEDIA_PRESSURE,
        event_question="Test question",
        response_options='[]',
        event_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(hours=24)
    )
    
    assert event_with_match.is_match_related()
    assert not event_without_match.is_match_related()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
