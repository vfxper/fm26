"""
Unit tests for ScoutingAssignment model
"""

import pytest
from datetime import datetime, timedelta
from app.models.scouting_assignment import (
    ScoutingAssignment,
    AssignmentType,
    AssignmentStatus
)


def test_scouting_assignment_creation():
    """Test basic ScoutingAssignment model creation"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    assert assignment.career_id == 1
    assert assignment.staff_id == 1
    assert assignment.assignment_type == AssignmentType.PLAYER
    assert assignment.target_player_id == 100
    assert assignment.assignment_status == AssignmentStatus.ASSIGNED
    assert assignment.estimated_weeks == 3


def test_scouting_assignment_region():
    """Test region assignment creation"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.REGION,
        target_region="South America",
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=4
    )
    
    assert assignment.assignment_type == AssignmentType.REGION
    assert assignment.target_region == "South America"
    assert assignment.target_player_id is None
    assert assignment.target_competition is None


def test_scouting_assignment_competition():
    """Test competition assignment creation"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.COMPETITION,
        target_competition="Champions League",
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=2
    )
    
    assert assignment.assignment_type == AssignmentType.COMPETITION
    assert assignment.target_competition == "Champions League"
    assert assignment.target_player_id is None
    assert assignment.target_region is None


def test_is_completed():
    """Test is_completed method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.COMPLETED,
        estimated_weeks=3
    )
    
    assert assignment.is_completed() is True
    assert assignment.is_in_progress() is False
    assert assignment.is_assigned() is False


def test_is_in_progress():
    """Test is_in_progress method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.IN_PROGRESS,
        estimated_weeks=3
    )
    
    assert assignment.is_completed() is False
    assert assignment.is_in_progress() is True
    assert assignment.is_assigned() is False


def test_is_assigned():
    """Test is_assigned method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    assert assignment.is_completed() is False
    assert assignment.is_in_progress() is False
    assert assignment.is_assigned() is True


def test_start_assignment():
    """Test start_assignment method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    assignment.start_assignment()
    assert assignment.assignment_status == AssignmentStatus.IN_PROGRESS


def test_complete_assignment():
    """Test complete_assignment method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.IN_PROGRESS,
        estimated_weeks=3
    )
    
    report_data = '{"attributes": {"ca": 150, "pa": 180}}'
    assignment.complete_assignment(report_data)
    
    assert assignment.assignment_status == AssignmentStatus.COMPLETED
    assert assignment.report_data == report_data


def test_get_target_display_name():
    """Test get_target_display_name method"""
    # Player assignment
    player_assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    assert player_assignment.get_target_display_name() == "Player ID: 100"
    
    # Region assignment
    region_assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.REGION,
        target_region="Europe",
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    assert region_assignment.get_target_display_name() == "Region: Europe"
    
    # Competition assignment
    competition_assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.COMPETITION,
        target_competition="Premier League",
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    assert competition_assignment.get_target_display_name() == "Competition: Premier League"


def test_is_player_assignment():
    """Test is_player_assignment method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    assert assignment.is_player_assignment() is True
    assert assignment.is_region_assignment() is False
    assert assignment.is_competition_assignment() is False


def test_is_region_assignment():
    """Test is_region_assignment method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.REGION,
        target_region="Asia",
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    assert assignment.is_player_assignment() is False
    assert assignment.is_region_assignment() is True
    assert assignment.is_competition_assignment() is False


def test_is_competition_assignment():
    """Test is_competition_assignment method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=1,
        assignment_type=AssignmentType.COMPETITION,
        target_competition="La Liga",
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    assert assignment.is_player_assignment() is False
    assert assignment.is_region_assignment() is False
    assert assignment.is_competition_assignment() is True


def test_to_dict():
    """Test to_dict method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=2,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.IN_PROGRESS,
        estimated_weeks=3
    )
    
    result = assignment.to_dict()
    
    assert result["career_id"] == 1
    assert result["staff_id"] == 2
    assert result["assignment"]["type"] == "player"
    assert result["assignment"]["target_player_id"] == 100
    assert result["assignment"]["status"] == "in_progress"
    assert result["timeline"]["estimated_weeks"] == 3


def test_repr():
    """Test __repr__ method"""
    assignment = ScoutingAssignment(
        career_id=1,
        staff_id=2,
        assignment_type=AssignmentType.PLAYER,
        target_player_id=100,
        assignment_status=AssignmentStatus.ASSIGNED,
        estimated_weeks=3
    )
    
    repr_str = repr(assignment)
    assert "ScoutingAssignment" in repr_str
    assert "career_id=1" in repr_str
    assert "staff_id=2" in repr_str
    assert "assignment_type=player" in repr_str
    assert "status=assigned" in repr_str
