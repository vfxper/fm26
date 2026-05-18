"""
Unit tests for duplicate detection and handling in Player CSV Loader

Tests Task 3.9: Implement duplicate detection and handling
- CSV duplicate detection (duplicate UIDs in CSV file)
- Database duplicate detection (UIDs already in database)
- Duplicate handling strategies (skip, log, report)
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock

from app.services.player_loader import (
    PlayerCSVParser,
    load_players_from_csv,
)
from app.models.player import Player


class TestCSVDuplicateDetection:
    """Test suite for CSV duplicate detection"""
    
    @pytest.fixture
    def duplicate_uid_csv(self, tmp_path):
        """Create a CSV file with duplicate UIDs"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Player One,ST,25,150,160,Country A,Club A,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,duplicate001
Player Two,AM,26,155,165,Country B,Club B,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,duplicate001
Player Three,DF,27,145,155,Country C,Club C,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,£900000,9000,178,74,14,14,unique001"""
        csv_file = tmp_path / "duplicate_uid.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def multiple_duplicates_csv(self, tmp_path):
        """Create a CSV file with multiple sets of duplicates"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Player A1,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,dup_a
Player A2,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,dup_a
Player B1,AM,26,155,165,Country,Club,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,dup_b
Player B2,AM,26,155,165,Country,Club,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,dup_b
Player C,DF,27,145,155,Country,Club,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,£900000,9000,178,74,14,14,unique_c"""
        csv_file = tmp_path / "multiple_duplicates.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def no_duplicates_csv(self, tmp_path):
        """Create a CSV file with no duplicates"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Player One,ST,25,150,160,Country A,Club A,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,unique001
Player Two,AM,26,155,165,Country B,Club B,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,unique002
Player Three,DF,27,145,155,Country C,Club C,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,£900000,9000,178,74,14,14,unique003"""
        csv_file = tmp_path / "no_duplicates.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    def test_detect_duplicate_uids_in_csv(self, duplicate_uid_csv):
        """Test that duplicate UIDs are detected in CSV"""
        parser = PlayerCSVParser(duplicate_uid_csv)
        df = parser.load()
        
        # Before cleaning, should have 3 rows
        assert len(df) == 3
        
        # Check for duplicates
        duplicate_uids = df[df['uid'].duplicated()]['uid'].tolist()
        assert len(duplicate_uids) > 0
        assert 'duplicate001' in duplicate_uids
    
    def test_clean_data_removes_duplicate_uids(self, duplicate_uid_csv):
        """Test that clean_data removes duplicate UIDs, keeping first occurrence"""
        parser = PlayerCSVParser(duplicate_uid_csv)
        df = parser.load()
        
        # Before cleaning
        assert len(df) == 3
        
        # Clean data
        clean_df, report = parser.clean_data(df)
        
        # After cleaning, should have 2 rows (one duplicate removed)
        assert len(clean_df) == 2
        assert report['duplicates_removed'] == 1
        
        # Check that first occurrence is kept
        player_one = clean_df[clean_df['uid'] == 'duplicate001']
        assert len(player_one) == 1
        assert player_one.iloc[0]['name'] == 'Player One'
        
        # Check that unique player is kept
        player_three = clean_df[clean_df['uid'] == 'unique001']
        assert len(player_three) == 1
        assert player_three.iloc[0]['name'] == 'Player Three'
    
    def test_clean_data_removes_multiple_duplicates(self, multiple_duplicates_csv):
        """Test that clean_data removes multiple sets of duplicates"""
        parser = PlayerCSVParser(multiple_duplicates_csv)
        df = parser.load()
        
        # Before cleaning: 5 rows
        assert len(df) == 5
        
        # Clean data
        clean_df, report = parser.clean_data(df)
        
        # After cleaning: 3 rows (2 duplicates removed)
        assert len(clean_df) == 3
        assert report['duplicates_removed'] == 2
        
        # Check that first occurrences are kept
        assert 'Player A1' in clean_df['name'].values
        assert 'Player B1' in clean_df['name'].values
        assert 'Player C' in clean_df['name'].values
        
        # Check that duplicates are removed
        assert 'Player A2' not in clean_df['name'].values
        assert 'Player B2' not in clean_df['name'].values
    
    def test_clean_data_no_duplicates(self, no_duplicates_csv):
        """Test that clean_data handles CSV with no duplicates correctly"""
        parser = PlayerCSVParser(no_duplicates_csv)
        df = parser.load()
        
        # Before cleaning
        assert len(df) == 3
        
        # Clean data
        clean_df, report = parser.clean_data(df)
        
        # After cleaning, should still have 3 rows
        assert len(clean_df) == 3
        assert report['duplicates_removed'] == 0
    
    def test_duplicate_detection_logs_warning(self, duplicate_uid_csv, caplog):
        """Test that duplicate detection logs a warning"""
        import logging
        caplog.set_level(logging.INFO)
        
        parser = PlayerCSVParser(duplicate_uid_csv)
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        # Check that warning was logged
        assert any('duplicate' in record.message.lower() for record in caplog.records)
    
    def test_validation_report_includes_duplicate_info(self, duplicate_uid_csv):
        """Test that validation report includes duplicate information"""
        parser = PlayerCSVParser(duplicate_uid_csv)
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        assert 'duplicates_removed' in report
        assert report['duplicates_removed'] == 1
        assert report['original_count'] == 3
        assert report['valid_count'] == 2


class TestDatabaseDuplicateDetection:
    """Test suite for database duplicate detection"""
    
    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Player One,ST,25,150,160,Country A,Club A,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,db_player001
Player Two,AM,26,155,165,Country B,Club B,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,db_player002
Player Three,DF,27,145,155,Country C,Club C,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,£900000,9000,178,74,14,14,db_player003"""
        csv_file = tmp_path / "db_test.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    def test_load_players_without_db_session(self, sample_csv_file):
        """Test loading players without database session (no DB duplicate check)"""
        players, report = load_players_from_csv(sample_csv_file, db_session=None)
        
        assert len(players) == 3
        assert report['db_duplicates_skipped'] == 0
        assert 'db_duplicate_uids' in report
        assert len(report['db_duplicate_uids']) == 0
    
    def test_load_players_with_db_session_no_duplicates(self, sample_csv_file):
        """Test loading players with database session when no duplicates exist"""
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # No existing players
        
        players, report = load_players_from_csv(sample_csv_file, mock_session)
        
        assert len(players) == 3
        assert report['db_duplicates_skipped'] == 0
        assert 'db_duplicate_uids' in report
    
    def test_load_players_with_db_session_with_duplicates(self, sample_csv_file):
        """Test loading players with database session when duplicates exist"""
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Simulate that db_player001 and db_player002 already exist in database
        mock_query.all.return_value = [
            ('db_player001',),
            ('db_player002',)
        ]
        
        players, report = load_players_from_csv(sample_csv_file, mock_session)
        
        # Only Player Three should be loaded (Player One and Two are duplicates)
        assert len(players) == 1
        assert players[0].uid == 'db_player003'
        assert players[0].name == 'Player Three'
        
        # Check report
        assert report['db_duplicates_skipped'] == 2
        assert 'db_duplicate_uids' in report
        assert 'db_player001' in report['db_duplicate_uids']
        assert 'db_player002' in report['db_duplicate_uids']
    
    def test_load_players_with_db_session_all_duplicates(self, sample_csv_file):
        """Test loading players when all are duplicates in database"""
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Simulate that all players already exist in database
        mock_query.all.return_value = [
            ('db_player001',),
            ('db_player002',),
            ('db_player003',)
        ]
        
        players, report = load_players_from_csv(sample_csv_file, mock_session)
        
        # No players should be loaded
        assert len(players) == 0
        assert report['db_duplicates_skipped'] == 3
        assert report['successfully_created'] == 0
    
    def test_load_players_db_duplicate_detection_disabled(self, sample_csv_file):
        """Test loading players with DB session but duplicate detection disabled"""
        # Mock database session
        mock_session = Mock()
        
        # Load with detect_db_duplicates=False
        players, report = load_players_from_csv(
            sample_csv_file, 
            mock_session, 
            detect_db_duplicates=False
        )
        
        # All players should be loaded (no DB duplicate check)
        assert len(players) == 3
        assert report['db_duplicates_skipped'] == 0
        
        # Database should not have been queried
        mock_session.query.assert_not_called()
    
    def test_load_players_db_error_handling(self, sample_csv_file, caplog):
        """Test that database errors during duplicate check are handled gracefully"""
        import logging
        caplog.set_level(logging.WARNING)
        
        # Mock database session that raises an error
        mock_session = Mock()
        mock_session.query.side_effect = Exception("Database connection error")
        
        # Should not raise exception, but log warning and continue
        players, report = load_players_from_csv(sample_csv_file, mock_session)
        
        # All players should be loaded (fallback to no DB duplicate check)
        assert len(players) == 3
        assert report['db_duplicates_skipped'] == 0
        
        # Check that warning was logged
        assert any('failed to check database' in record.message.lower() for record in caplog.records)
    
    def test_load_players_db_batch_query(self, tmp_path):
        """Test that database duplicate check uses batch queries for large datasets"""
        # Create CSV with many players
        rows = []
        rows.append("name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid")
        
        for i in range(1500):  # More than batch size (1000)
            rows.append(f"Player {i},ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,player{i:04d}")
        
        csv_file = tmp_path / "large_test.csv"
        csv_file.write_text('\n'.join(rows), encoding='utf-8')
        
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []  # No duplicates
        
        players, report = load_players_from_csv(str(csv_file), mock_session)
        
        # Check that query was called multiple times (batching)
        assert mock_session.query.call_count >= 2  # At least 2 batches for 1500 players


class TestDuplicateHandlingStrategies:
    """Test suite for duplicate handling strategies"""
    
    @pytest.fixture
    def mixed_duplicates_csv(self, tmp_path):
        """Create a CSV file with both CSV and potential DB duplicates"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
CSV Dup 1,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,csv_dup
CSV Dup 2,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,csv_dup
DB Dup,AM,26,155,165,Country,Club,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,db_dup
Unique,DF,27,145,155,Country,Club,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,£900000,9000,178,74,14,14,unique"""
        csv_file = tmp_path / "mixed_duplicates.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    def test_handle_both_csv_and_db_duplicates(self, mixed_duplicates_csv):
        """Test handling both CSV duplicates and database duplicates"""
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        # Simulate that db_dup already exists in database
        mock_query.all.return_value = [('db_dup',)]
        
        players, report = load_players_from_csv(mixed_duplicates_csv, mock_session)
        
        # Should have 2 players: CSV Dup 1 (first occurrence) and Unique
        # CSV Dup 2 removed by CSV duplicate detection
        # DB Dup removed by database duplicate detection
        assert len(players) == 2
        
        player_names = [p.name for p in players]
        assert 'CSV Dup 1' in player_names
        assert 'Unique' in player_names
        assert 'CSV Dup 2' not in player_names
        assert 'DB Dup' not in player_names
        
        # Check report
        assert report['csv_duplicates_removed'] == 1  # CSV Dup 2
        assert report['db_duplicates_skipped'] == 1  # DB Dup
        assert report['total_duplicates_handled'] == 2
    
    def test_duplicate_handling_preserves_first_occurrence(self, mixed_duplicates_csv):
        """Test that duplicate handling preserves first occurrence (keep='first')"""
        parser = PlayerCSVParser(mixed_duplicates_csv)
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        # Check that first occurrence of csv_dup is kept
        csv_dup_player = clean_df[clean_df['uid'] == 'csv_dup']
        assert len(csv_dup_player) == 1
        assert csv_dup_player.iloc[0]['name'] == 'CSV Dup 1'
    
    def test_validation_report_comprehensive(self, mixed_duplicates_csv):
        """Test that validation report includes all duplicate information"""
        # Mock database session
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [('db_dup',)]
        
        players, report = load_players_from_csv(mixed_duplicates_csv, mock_session)
        
        # Check all required fields in report
        assert 'original_count' in report
        assert 'csv_duplicates_removed' in report
        assert 'db_duplicates_skipped' in report
        assert 'total_duplicates_handled' in report
        assert 'valid_count' in report
        assert 'successfully_created' in report
        
        # Check values
        assert report['original_count'] == 4
        assert report['csv_duplicates_removed'] == 1
        assert report['db_duplicates_skipped'] == 1
        assert report['total_duplicates_handled'] == 2
        assert report['successfully_created'] == 2


class TestDuplicateDetectionPerformance:
    """Test suite for duplicate detection performance"""
    
    def test_duplicate_detection_efficient_for_large_csv(self, tmp_path):
        """Test that duplicate detection is efficient for large CSV files"""
        import time
        
        # Create CSV with 1000 players including some duplicates
        rows = []
        rows.append("name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid")
        
        for i in range(1000):
            # Add some duplicates (every 100th player is a duplicate)
            uid = f"player{i % 100:04d}" if i >= 100 else f"player{i:04d}"
            rows.append(f"Player {i},ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,{uid}")
        
        csv_file = tmp_path / "large_test.csv"
        csv_file.write_text('\n'.join(rows), encoding='utf-8')
        
        # Measure time
        start_time = time.time()
        
        parser = PlayerCSVParser(str(csv_file))
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Should complete in reasonable time (< 5 seconds for 1000 players)
        assert elapsed_time < 5.0
        
        # Check that duplicates were removed
        assert report['duplicates_removed'] > 0
        assert len(clean_df) < len(df)
