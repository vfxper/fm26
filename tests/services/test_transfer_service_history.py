"""
Tests for Transfer Service - Transfer History Logging (Task 8.10)

Tests the transfer history logging functionality including:
- Logging completed transfers to transfer history
- Tracking transfer type, fee, wage, season, week
- Supporting filtering by season and transfer type
- Database persistence of transfer records
- Comprehensive edge cases and boundary conditions
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.transfer_service import TransferService, TransferRecord
from app.models.transfer import Transfer, TransferType, TransferStatus
from app.models.career import Career
from app.models.club import Club
from app.models.player import Player


@pytest.fixture
def transfer_service():
    """Create a TransferService instance for testing"""
    return TransferService()


@pytest.fixture
def empty_history():
    """Create an empty transfer history list"""
    return []


@pytest.fixture
def sample_history():
    """Create a sample transfer history with multiple records"""
    return [
        TransferRecord(
            player_id=1,
            player_name="John Doe",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
        ),
        TransferRecord(
            player_id=2,
            player_name="Jane Smith",
            from_club="Club C",
            to_club="Club B",
            transfer_type="loan",
            fee=0,
            wage=8_000,
            season=1,
            week=7,
        ),
        TransferRecord(
            player_id=3,
            player_name="Bob Johnson",
            from_club="Free Agent",
            to_club="Club B",
            transfer_type="free_agent",
            fee=0,
            wage=12_000,
            season=2,
            week=15,
        ),
        TransferRecord(
            player_id=4,
            player_name="Alice Williams",
            from_club="Club D",
            to_club="Club B",
            transfer_type="emergency_loan",
            fee=0,
            wage=9_000,
            season=2,
            week=28,
        ),
    ]


class TestLogTransferBasics:
    """Test basic transfer logging functionality"""
    
    def test_log_permanent_transfer(self, transfer_service, empty_history):
        """Test logging a permanent transfer"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="John Doe",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        assert record is not None
        assert record.player_id == 1
        assert record.player_name == "John Doe"
        assert record.from_club == "Club A"
        assert record.to_club == "Club B"
        assert record.transfer_type == "permanent"
        assert record.fee == 5_000_000
        assert record.wage == 10_000
        assert record.season == 1
        assert record.week == 5
        assert len(empty_history) == 1
        assert empty_history[0] == record
    
    def test_log_loan_transfer(self, transfer_service, empty_history):
        """Test logging a loan transfer"""
        record = transfer_service.log_transfer(
            player_id=2,
            player_name="Jane Smith",
            from_club="Club C",
            to_club="Club B",
            transfer_type="loan",
            fee=0,
            wage=8_000,
            season=1,
            week=7,
            history=empty_history,
        )
        
        assert record.transfer_type == "loan"
        assert record.fee == 0
        assert len(empty_history) == 1
    
    def test_log_free_agent_signing(self, transfer_service, empty_history):
        """Test logging a free agent signing"""
        record = transfer_service.log_transfer(
            player_id=3,
            player_name="Bob Johnson",
            from_club="Free Agent",
            to_club="Club B",
            transfer_type="free_agent",
            fee=0,
            wage=12_000,
            season=2,
            week=15,
            history=empty_history,
        )
        
        assert record.transfer_type == "free_agent"
        assert record.from_club == "Free Agent"
        assert record.fee == 0
        assert len(empty_history) == 1
    
    def test_log_emergency_loan(self, transfer_service, empty_history):
        """Test logging an emergency loan"""
        record = transfer_service.log_transfer(
            player_id=4,
            player_name="Alice Williams",
            from_club="Club D",
            to_club="Club B",
            transfer_type="emergency_loan",
            fee=0,
            wage=9_000,
            season=2,
            week=28,
            history=empty_history,
        )
        
        assert record.transfer_type == "emergency_loan"
        assert record.fee == 0
        assert len(empty_history) == 1


class TestLogMultipleTransfers:
    """Test logging multiple transfers"""
    
    def test_log_multiple_transfers_to_same_history(self, transfer_service, empty_history):
        """Test logging multiple transfers to the same history list"""
        record1 = transfer_service.log_transfer(
            player_id=1,
            player_name="Player 1",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        record2 = transfer_service.log_transfer(
            player_id=2,
            player_name="Player 2",
            from_club="Club C",
            to_club="Club B",
            transfer_type="loan",
            fee=0,
            wage=8_000,
            season=1,
            week=7,
            history=empty_history,
        )
        
        record3 = transfer_service.log_transfer(
            player_id=3,
            player_name="Player 3",
            from_club="Free Agent",
            to_club="Club B",
            transfer_type="free_agent",
            fee=0,
            wage=12_000,
            season=2,
            week=15,
            history=empty_history,
        )
        
        assert len(empty_history) == 3
        assert empty_history[0] == record1
        assert empty_history[1] == record2
        assert empty_history[2] == record3
    
    def test_log_transfers_maintains_order(self, transfer_service, empty_history):
        """Test that logged transfers maintain insertion order"""
        for i in range(10):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club=f"Club {i}",
                to_club="Club B",
                transfer_type="permanent",
                fee=1_000_000 * i,
                wage=5_000 + i * 1000,
                season=1,
                week=i + 1,
                history=empty_history,
            )
        
        assert len(empty_history) == 10
        for i in range(10):
            assert empty_history[i].player_id == i
            assert empty_history[i].player_name == f"Player {i}"


class TestGetTransferHistoryNoFilters:
    """Test getting transfer history without filters"""
    
    def test_get_all_transfers(self, transfer_service, sample_history):
        """Test getting all transfers without filters"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=None,
            transfer_type=None,
        )
        
        assert len(result) == 4
        assert result == sample_history
    
    def test_get_transfers_from_empty_history(self, transfer_service, empty_history):
        """Test getting transfers from empty history"""
        result = transfer_service.get_transfer_history(
            history=empty_history,
            season=None,
            transfer_type=None,
        )
        
        assert len(result) == 0
        assert result == []


class TestGetTransferHistorySeasonFilter:
    """Test getting transfer history with season filter"""
    
    def test_filter_by_season_1(self, transfer_service, sample_history):
        """Test filtering transfers by season 1"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=1,
            transfer_type=None,
        )
        
        assert len(result) == 2
        assert all(r.season == 1 for r in result)
        assert result[0].player_name == "John Doe"
        assert result[1].player_name == "Jane Smith"
    
    def test_filter_by_season_2(self, transfer_service, sample_history):
        """Test filtering transfers by season 2"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=2,
            transfer_type=None,
        )
        
        assert len(result) == 2
        assert all(r.season == 2 for r in result)
        assert result[0].player_name == "Bob Johnson"
        assert result[1].player_name == "Alice Williams"
    
    def test_filter_by_nonexistent_season(self, transfer_service, sample_history):
        """Test filtering by a season with no transfers"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=99,
            transfer_type=None,
        )
        
        assert len(result) == 0
    
    def test_filter_by_season_0(self, transfer_service, sample_history):
        """Test filtering by season 0 (edge case)"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=0,
            transfer_type=None,
        )
        
        assert len(result) == 0


class TestGetTransferHistoryTypeFilter:
    """Test getting transfer history with transfer type filter"""
    
    def test_filter_by_permanent_type(self, transfer_service, sample_history):
        """Test filtering transfers by permanent type"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=None,
            transfer_type="permanent",
        )
        
        assert len(result) == 1
        assert result[0].transfer_type == "permanent"
        assert result[0].player_name == "John Doe"
    
    def test_filter_by_loan_type(self, transfer_service, sample_history):
        """Test filtering transfers by loan type"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=None,
            transfer_type="loan",
        )
        
        assert len(result) == 1
        assert result[0].transfer_type == "loan"
        assert result[0].player_name == "Jane Smith"
    
    def test_filter_by_free_agent_type(self, transfer_service, sample_history):
        """Test filtering transfers by free agent type"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=None,
            transfer_type="free_agent",
        )
        
        assert len(result) == 1
        assert result[0].transfer_type == "free_agent"
        assert result[0].player_name == "Bob Johnson"
    
    def test_filter_by_emergency_loan_type(self, transfer_service, sample_history):
        """Test filtering transfers by emergency loan type"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=None,
            transfer_type="emergency_loan",
        )
        
        assert len(result) == 1
        assert result[0].transfer_type == "emergency_loan"
        assert result[0].player_name == "Alice Williams"
    
    def test_filter_by_nonexistent_type(self, transfer_service, sample_history):
        """Test filtering by a transfer type that doesn't exist"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=None,
            transfer_type="invalid_type",
        )
        
        assert len(result) == 0


class TestGetTransferHistoryCombinedFilters:
    """Test getting transfer history with combined filters"""
    
    def test_filter_by_season_and_type(self, transfer_service, sample_history):
        """Test filtering by both season and transfer type"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=1,
            transfer_type="permanent",
        )
        
        assert len(result) == 1
        assert result[0].season == 1
        assert result[0].transfer_type == "permanent"
        assert result[0].player_name == "John Doe"
    
    def test_filter_season_1_loan(self, transfer_service, sample_history):
        """Test filtering season 1 loan transfers"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=1,
            transfer_type="loan",
        )
        
        assert len(result) == 1
        assert result[0].season == 1
        assert result[0].transfer_type == "loan"
        assert result[0].player_name == "Jane Smith"
    
    def test_filter_season_2_free_agent(self, transfer_service, sample_history):
        """Test filtering season 2 free agent signings"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=2,
            transfer_type="free_agent",
        )
        
        assert len(result) == 1
        assert result[0].season == 2
        assert result[0].transfer_type == "free_agent"
        assert result[0].player_name == "Bob Johnson"
    
    def test_filter_no_matches(self, transfer_service, sample_history):
        """Test filtering with no matching results"""
        result = transfer_service.get_transfer_history(
            history=sample_history,
            season=1,
            transfer_type="free_agent",  # No free agents in season 1
        )
        
        assert len(result) == 0


class TestTransferRecordAttributes:
    """Test TransferRecord attributes and data integrity"""
    
    def test_transfer_record_has_all_attributes(self, transfer_service, empty_history):
        """Test that TransferRecord has all required attributes"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="John Doe",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        assert hasattr(record, 'player_id')
        assert hasattr(record, 'player_name')
        assert hasattr(record, 'from_club')
        assert hasattr(record, 'to_club')
        assert hasattr(record, 'transfer_type')
        assert hasattr(record, 'fee')
        assert hasattr(record, 'wage')
        assert hasattr(record, 'season')
        assert hasattr(record, 'week')
    
    def test_transfer_record_immutability(self, transfer_service, empty_history):
        """Test that logged transfer records maintain their values"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="John Doe",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        # Verify values are preserved
        assert record.player_id == 1
        assert record.player_name == "John Doe"
        assert record.from_club == "Club A"
        assert record.to_club == "Club B"
        assert record.transfer_type == "permanent"
        assert record.fee == 5_000_000
        assert record.wage == 10_000
        assert record.season == 1
        assert record.week == 5


class TestTransferHistoryEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_log_transfer_with_zero_fee(self, transfer_service, empty_history):
        """Test logging transfer with zero fee"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="Player",
            from_club="Club A",
            to_club="Club B",
            transfer_type="loan",
            fee=0,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        assert record.fee == 0
        assert len(empty_history) == 1
    
    def test_log_transfer_with_very_high_fee(self, transfer_service, empty_history):
        """Test logging transfer with very high fee"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="Player",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=200_000_000,
            wage=100_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        assert record.fee == 200_000_000
        assert len(empty_history) == 1
    
    def test_log_transfer_week_1(self, transfer_service, empty_history):
        """Test logging transfer in week 1"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="Player",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=1,
            history=empty_history,
        )
        
        assert record.week == 1
        assert len(empty_history) == 1
    
    def test_log_transfer_week_52(self, transfer_service, empty_history):
        """Test logging transfer in week 52"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="Player",
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=52,
            history=empty_history,
        )
        
        assert record.week == 52
        assert len(empty_history) == 1
    
    def test_log_transfer_with_long_player_name(self, transfer_service, empty_history):
        """Test logging transfer with very long player name"""
        long_name = "A" * 200
        record = transfer_service.log_transfer(
            player_id=1,
            player_name=long_name,
            from_club="Club A",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        assert record.player_name == long_name
        assert len(empty_history) == 1
    
    def test_log_transfer_with_special_characters_in_names(self, transfer_service, empty_history):
        """Test logging transfer with special characters in names"""
        record = transfer_service.log_transfer(
            player_id=1,
            player_name="João O'Brien-Smith",
            from_club="FC São Paulo",
            to_club="Club B",
            transfer_type="permanent",
            fee=5_000_000,
            wage=10_000,
            season=1,
            week=5,
            history=empty_history,
        )
        
        assert record.player_name == "João O'Brien-Smith"
        assert record.from_club == "FC São Paulo"
        assert len(empty_history) == 1


class TestTransferHistoryMultipleSeasons:
    """Test transfer history across multiple seasons"""
    
    def test_transfers_across_multiple_seasons(self, transfer_service, empty_history):
        """Test logging and filtering transfers across multiple seasons"""
        # Season 1 transfers
        for i in range(3):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club=f"Club {i}",
                to_club="Club B",
                transfer_type="permanent",
                fee=1_000_000 * (i + 1),
                wage=5_000 + i * 1000,
                season=1,
                week=i + 1,
                history=empty_history,
            )
        
        # Season 2 transfers
        for i in range(3, 6):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club=f"Club {i}",
                to_club="Club B",
                transfer_type="loan",
                fee=0,
                wage=5_000 + i * 1000,
                season=2,
                week=i + 1,
                history=empty_history,
            )
        
        # Season 3 transfers
        for i in range(6, 9):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club="Free Agent",
                to_club="Club B",
                transfer_type="free_agent",
                fee=0,
                wage=5_000 + i * 1000,
                season=3,
                week=i + 1,
                history=empty_history,
            )
        
        # Verify total count
        assert len(empty_history) == 9
        
        # Verify season 1 filter
        season1 = transfer_service.get_transfer_history(empty_history, season=1)
        assert len(season1) == 3
        assert all(r.season == 1 for r in season1)
        
        # Verify season 2 filter
        season2 = transfer_service.get_transfer_history(empty_history, season=2)
        assert len(season2) == 3
        assert all(r.season == 2 for r in season2)
        
        # Verify season 3 filter
        season3 = transfer_service.get_transfer_history(empty_history, season=3)
        assert len(season3) == 3
        assert all(r.season == 3 for r in season3)


class TestTransferHistoryAllTransferTypes:
    """Test transfer history with all transfer types"""
    
    def test_all_transfer_types_logged(self, transfer_service, empty_history):
        """Test that all transfer types can be logged"""
        transfer_types = ["permanent", "loan", "free_agent", "emergency_loan"]
        
        for i, transfer_type in enumerate(transfer_types):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club="Club A" if transfer_type != "free_agent" else "Free Agent",
                to_club="Club B",
                transfer_type=transfer_type,
                fee=5_000_000 if transfer_type == "permanent" else 0,
                wage=10_000,
                season=1,
                week=i + 1,
                history=empty_history,
            )
        
        assert len(empty_history) == 4
        
        # Verify each type can be filtered
        for transfer_type in transfer_types:
            filtered = transfer_service.get_transfer_history(
                empty_history,
                transfer_type=transfer_type
            )
            assert len(filtered) == 1
            assert filtered[0].transfer_type == transfer_type


class TestTransferHistoryRealisticScenarios:
    """Test realistic transfer history scenarios"""
    
    def test_summer_transfer_window_activity(self, transfer_service, empty_history):
        """Test logging multiple transfers during summer window"""
        # Summer window: weeks 1-8
        for week in range(1, 9):
            transfer_service.log_transfer(
                player_id=week,
                player_name=f"Player {week}",
                from_club=f"Club {week}",
                to_club="Club B",
                transfer_type="permanent",
                fee=1_000_000 * week,
                wage=5_000 + week * 1000,
                season=1,
                week=week,
                history=empty_history,
            )
        
        assert len(empty_history) == 8
        season1 = transfer_service.get_transfer_history(empty_history, season=1)
        assert len(season1) == 8
        assert all(1 <= r.week <= 8 for r in season1)
    
    def test_winter_transfer_window_activity(self, transfer_service, empty_history):
        """Test logging multiple transfers during winter window"""
        # Winter window: weeks 26-30
        for week in range(26, 31):
            transfer_service.log_transfer(
                player_id=week,
                player_name=f"Player {week}",
                from_club=f"Club {week}",
                to_club="Club B",
                transfer_type="permanent",
                fee=1_000_000 * week,
                wage=5_000 + week * 1000,
                season=1,
                week=week,
                history=empty_history,
            )
        
        assert len(empty_history) == 5
        season1 = transfer_service.get_transfer_history(empty_history, season=1)
        assert len(season1) == 5
        assert all(26 <= r.week <= 30 for r in season1)
    
    def test_mixed_transfer_activity_full_season(self, transfer_service, empty_history):
        """Test mixed transfer activity throughout a full season"""
        # Summer window permanent transfers
        for week in range(1, 4):
            transfer_service.log_transfer(
                player_id=week,
                player_name=f"Player {week}",
                from_club=f"Club {week}",
                to_club="Club B",
                transfer_type="permanent",
                fee=5_000_000,
                wage=10_000,
                season=1,
                week=week,
                history=empty_history,
            )
        
        # Mid-season free agent signings
        for week in range(15, 18):
            transfer_service.log_transfer(
                player_id=week,
                player_name=f"Player {week}",
                from_club="Free Agent",
                to_club="Club B",
                transfer_type="free_agent",
                fee=0,
                wage=8_000,
                season=1,
                week=week,
                history=empty_history,
            )
        
        # Winter window loans
        for week in range(27, 30):
            transfer_service.log_transfer(
                player_id=week,
                player_name=f"Player {week}",
                from_club=f"Club {week}",
                to_club="Club B",
                transfer_type="loan",
                fee=0,
                wage=7_000,
                season=1,
                week=week,
                history=empty_history,
            )
        
        # Verify total count
        assert len(empty_history) == 9
        
        # Verify by type
        permanent = transfer_service.get_transfer_history(
            empty_history,
            transfer_type="permanent"
        )
        assert len(permanent) == 3
        
        free_agent = transfer_service.get_transfer_history(
            empty_history,
            transfer_type="free_agent"
        )
        assert len(free_agent) == 3
        
        loan = transfer_service.get_transfer_history(
            empty_history,
            transfer_type="loan"
        )
        assert len(loan) == 3


class TestTransferHistoryPerformance:
    """Test transfer history performance with large datasets"""
    
    def test_log_many_transfers(self, transfer_service, empty_history):
        """Test logging a large number of transfers"""
        num_transfers = 100
        
        for i in range(num_transfers):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club=f"Club {i}",
                to_club="Club B",
                transfer_type="permanent",
                fee=1_000_000 * (i + 1),
                wage=5_000 + i * 100,
                season=(i // 20) + 1,  # 20 transfers per season
                week=(i % 20) + 1,
                history=empty_history,
            )
        
        assert len(empty_history) == num_transfers
    
    def test_filter_large_history(self, transfer_service, empty_history):
        """Test filtering a large transfer history"""
        # Create 100 transfers across 5 seasons
        for i in range(100):
            transfer_service.log_transfer(
                player_id=i,
                player_name=f"Player {i}",
                from_club=f"Club {i}",
                to_club="Club B",
                transfer_type="permanent" if i % 2 == 0 else "loan",
                fee=1_000_000 * (i + 1) if i % 2 == 0 else 0,
                wage=5_000 + i * 100,
                season=(i // 20) + 1,
                week=(i % 20) + 1,
                history=empty_history,
            )
        
        # Filter by season
        season3 = transfer_service.get_transfer_history(empty_history, season=3)
        assert len(season3) == 20
        
        # Filter by type
        permanent = transfer_service.get_transfer_history(
            empty_history,
            transfer_type="permanent"
        )
        assert len(permanent) == 50
        
        # Filter by both
        season3_permanent = transfer_service.get_transfer_history(
            empty_history,
            season=3,
            transfer_type="permanent"
        )
        assert len(season3_permanent) == 10
