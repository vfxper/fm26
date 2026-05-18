"""
Unit tests for Celery tasks
"""

import pytest
from unittest.mock import patch, MagicMock
from celery import Task

from app.tasks.match_simulation import simulate_match, simulate_multiple_matches
from app.tasks.weekly_updates import (
    process_weekly_update,
    update_player_training,
    update_club_finances,
    process_player_aging,
)
from app.tasks.ai_manager import (
    generate_ai_tactics,
    generate_ai_transfers,
    process_ai_squad_selection,
)
from app.tasks.maintenance import cleanup_expired_results, health_check


class TestMatchSimulationTasks:
    """Test match simulation tasks"""
    
    def test_simulate_match_task_registered(self):
        """Test that simulate_match task is registered"""
        assert simulate_match.name == "app.tasks.match_simulation.simulate_match"
    
    def test_simulate_match_task_queue(self):
        """Test that simulate_match routes to matches queue"""
        assert simulate_match.queue == "matches"
    
    def test_simulate_match_task_priority(self):
        """Test that simulate_match has high priority"""
        assert simulate_match.priority == 10
    
    def test_simulate_match_execution(self):
        """Test simulate_match task execution"""
        result = simulate_match(
            match_id=1,
            home_team_id=10,
            away_team_id=20,
            competition_id=1,
        )
        
        # Verify result structure
        assert "match_id" in result
        assert "home_team_id" in result
        assert "away_team_id" in result
        assert "competition_id" in result
        assert "home_score" in result
        assert "away_score" in result
        assert "events" in result
        assert "statistics" in result
        assert "status" in result
        
        # Verify result values
        assert result["match_id"] == 1
        assert result["home_team_id"] == 10
        assert result["away_team_id"] == 20
        assert result["competition_id"] == 1
        assert result["status"] == "completed"
        assert isinstance(result["events"], list)
        assert isinstance(result["statistics"], dict)
    
    def test_simulate_match_returns_valid_score(self):
        """Test that simulate_match returns valid scores"""
        result = simulate_match(
            match_id=1,
            home_team_id=10,
            away_team_id=20,
            competition_id=1,
        )
        
        assert isinstance(result["home_score"], int)
        assert isinstance(result["away_score"], int)
        assert result["home_score"] >= 0
        assert result["away_score"] >= 0
    
    def test_simulate_multiple_matches_task_registered(self):
        """Test that simulate_multiple_matches task is registered"""
        assert simulate_multiple_matches.name == "app.tasks.match_simulation.simulate_multiple_matches"
    
    @patch("app.tasks.match_simulation.group")
    def test_simulate_multiple_matches_execution(self, mock_group):
        """Test simulate_multiple_matches task execution"""
        # Mock the group result
        mock_result_group = MagicMock()
        mock_result_group.get.return_value = [
            {"match_id": 1, "home_score": 2, "away_score": 1},
            {"match_id": 2, "home_score": 1, "away_score": 1},
            {"match_id": 3, "home_score": 0, "away_score": 2},
        ]
        mock_group.return_value.apply_async.return_value = mock_result_group
        
        result = simulate_multiple_matches(match_ids=[1, 2, 3])
        
        # Verify result structure
        assert "total" in result
        assert "completed" in result
        assert "failed" in result
        assert "results" in result
        
        # Verify result values
        assert result["total"] == 3
        assert result["completed"] == 3
        assert result["failed"] == 0
        assert len(result["results"]) == 3


class TestWeeklyUpdateTasks:
    """Test weekly update tasks"""
    
    def test_process_weekly_update_task_registered(self):
        """Test that process_weekly_update task is registered"""
        assert process_weekly_update.name == "app.tasks.weekly_updates.process_weekly_update"
    
    def test_process_weekly_update_task_queue(self):
        """Test that process_weekly_update routes to updates queue"""
        assert process_weekly_update.queue == "updates"
    
    def test_process_weekly_update_execution(self):
        """Test process_weekly_update task execution"""
        result = process_weekly_update()
        
        # Verify result structure
        assert "careers_processed" in result
        assert "players_trained" in result
        assert "players_aged" in result
        assert "contracts_expired" in result
        assert "injuries_recovered" in result
        assert "status" in result
        
        # Verify result values
        assert isinstance(result["careers_processed"], int)
        assert isinstance(result["players_trained"], int)
        assert isinstance(result["players_aged"], int)
        assert isinstance(result["contracts_expired"], int)
        assert isinstance(result["injuries_recovered"], int)
        assert result["status"] == "completed"
    
    def test_update_player_training_task_registered(self):
        """Test that update_player_training task is registered"""
        assert update_player_training.name == "app.tasks.weekly_updates.update_player_training"
    
    def test_update_player_training_execution(self):
        """Test update_player_training task execution"""
        result = update_player_training(
            career_id=1,
            player_ids=[101, 102, 103, 104, 105],
        )
        
        # Verify result structure
        assert "career_id" in result
        assert "players_updated" in result
        assert "attribute_changes" in result
        assert "status" in result
        
        # Verify result values
        assert result["career_id"] == 1
        assert result["players_updated"] == 5
        assert isinstance(result["attribute_changes"], list)
        assert result["status"] == "completed"
    
    def test_update_club_finances_task_registered(self):
        """Test that update_club_finances task is registered"""
        assert update_club_finances.name == "app.tasks.weekly_updates.update_club_finances"
    
    def test_update_club_finances_execution(self):
        """Test update_club_finances task execution"""
        result = update_club_finances(
            career_id=1,
            club_id=10,
        )
        
        # Verify result structure
        assert "career_id" in result
        assert "club_id" in result
        assert "income" in result
        assert "expenses" in result
        assert "balance" in result
        assert "status" in result
        
        # Verify result values
        assert result["career_id"] == 1
        assert result["club_id"] == 10
        assert isinstance(result["income"], int)
        assert isinstance(result["expenses"], int)
        assert isinstance(result["balance"], int)
        assert result["status"] == "completed"
    
    def test_process_player_aging_task_registered(self):
        """Test that process_player_aging task is registered"""
        assert process_player_aging.name == "app.tasks.weekly_updates.process_player_aging"
    
    def test_process_player_aging_execution(self):
        """Test process_player_aging task execution"""
        result = process_player_aging(player_ids=[201, 202, 203])
        
        # Verify result structure
        assert "players_aged" in result
        assert "attribute_changes" in result
        assert "status" in result
        
        # Verify result values
        assert result["players_aged"] == 3
        assert isinstance(result["attribute_changes"], list)
        assert result["status"] == "completed"


class TestAIManagerTasks:
    """Test AI manager tasks"""
    
    def test_generate_ai_tactics_task_registered(self):
        """Test that generate_ai_tactics task is registered"""
        assert generate_ai_tactics.name == "app.tasks.ai_manager.generate_ai_tactics"
    
    def test_generate_ai_tactics_task_queue(self):
        """Test that generate_ai_tactics routes to ai queue"""
        assert generate_ai_tactics.queue == "ai"
    
    def test_generate_ai_tactics_execution(self):
        """Test generate_ai_tactics task execution"""
        result = generate_ai_tactics(
            team_id=10,
            opponent_team_id=20,
            competition_id=1,
        )
        
        # Verify result structure
        assert "team_id" in result
        assert "formation" in result
        assert "mentality" in result
        assert "pressing" in result
        assert "defensive_line" in result
        assert "width" in result
        assert "tempo" in result
        
        # Verify result values
        assert result["team_id"] == 10
        assert isinstance(result["formation"], str)
        assert isinstance(result["mentality"], str)
    
    def test_generate_ai_transfers_task_registered(self):
        """Test that generate_ai_transfers task is registered"""
        assert generate_ai_transfers.name == "app.tasks.ai_manager.generate_ai_transfers"
    
    def test_generate_ai_transfers_execution(self):
        """Test generate_ai_transfers task execution"""
        result = generate_ai_transfers(
            club_id=10,
            transfer_budget=10000000,
        )
        
        # Verify result structure
        assert "club_id" in result
        assert "bids" in result
        assert "total_bid_amount" in result
        
        # Verify result values
        assert result["club_id"] == 10
        assert isinstance(result["bids"], list)
        assert isinstance(result["total_bid_amount"], int)
    
    def test_process_ai_squad_selection_task_registered(self):
        """Test that process_ai_squad_selection task is registered"""
        assert process_ai_squad_selection.name == "app.tasks.ai_manager.process_ai_squad_selection"
    
    def test_process_ai_squad_selection_execution(self):
        """Test process_ai_squad_selection task execution"""
        result = process_ai_squad_selection(
            team_id=10,
            match_id=100,
        )
        
        # Verify result structure
        assert "team_id" in result
        assert "match_id" in result
        assert "starting_11" in result
        assert "substitutes" in result
        assert "captain_id" in result
        
        # Verify result values
        assert result["team_id"] == 10
        assert result["match_id"] == 100
        assert len(result["starting_11"]) == 11
        assert len(result["substitutes"]) == 7


class TestMaintenanceTasks:
    """Test maintenance tasks"""
    
    def test_cleanup_expired_results_task_registered(self):
        """Test that cleanup_expired_results task is registered"""
        assert cleanup_expired_results.name == "app.tasks.maintenance.cleanup_expired_results"
    
    def test_cleanup_expired_results_task_queue(self):
        """Test that cleanup_expired_results routes to default queue"""
        assert cleanup_expired_results.queue == "default"
    
    def test_cleanup_expired_results_execution(self):
        """Test cleanup_expired_results task execution"""
        result = cleanup_expired_results()
        
        # Verify result structure
        assert "results_deleted" in result
        assert "memory_freed" in result
        assert "status" in result
        
        # Verify result values
        assert isinstance(result["results_deleted"], int)
        assert isinstance(result["memory_freed"], int)
        assert result["status"] == "completed"
    
    def test_health_check_task_registered(self):
        """Test that health_check task is registered"""
        assert health_check.name == "app.tasks.maintenance.health_check"
    
    def test_health_check_execution(self):
        """Test health_check task execution"""
        result = health_check()
        
        # Verify result structure
        assert "workers_active" in result
        assert "queues_status" in result
        assert "status" in result
        
        # Verify result values
        assert isinstance(result["workers_active"], int)
        assert isinstance(result["queues_status"], dict)
        assert result["status"] in ["healthy", "unhealthy"]


class TestTaskBindings:
    """Test that tasks are properly bound"""
    
    def test_simulate_match_is_bound(self):
        """Test that simulate_match is bound to task instance"""
        # Bound tasks have 'self' as first parameter
        assert simulate_match.bind is True
    
    def test_process_weekly_update_is_bound(self):
        """Test that process_weekly_update is bound to task instance"""
        assert process_weekly_update.bind is True
    
    def test_generate_ai_tactics_is_bound(self):
        """Test that generate_ai_tactics is bound to task instance"""
        assert generate_ai_tactics.bind is True


class TestTaskRetryConfiguration:
    """Test task retry configuration"""
    
    def test_tasks_inherit_base_task_retry(self):
        """Test that tasks inherit retry configuration from BaseTask"""
        # All tasks should inherit from BaseTask which has autoretry configured
        assert hasattr(simulate_match, "autoretry_for")
        assert hasattr(process_weekly_update, "autoretry_for")
        assert hasattr(generate_ai_tactics, "autoretry_for")
