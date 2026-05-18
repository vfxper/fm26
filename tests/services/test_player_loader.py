"""
Unit tests for Player CSV Loader Service

Tests the PlayerCSVParser class and related functions for loading
player data from the 2600球员属性.csv file.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

from app.services.player_loader import (
    PlayerCSVParser,
    PlayerLoaderError,
    CSVNotFoundError,
    CSVEncodingError,
    CSVParseError,
    CSVValidationError,
    load_players_from_csv,
    _create_player_from_row
)
from app.models.player import Player


class TestPlayerCSVParser:
    """Test suite for PlayerCSVParser class"""
    
    @pytest.fixture
    def sample_csv_content(self):
        """Sample CSV content with valid player data"""
        return """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Lionel Messi,AM/ST RL,37,180,180,Argentina,Inter Miami,15,14,20,18,20,17,8,16,5,6,19,15,7,20,8,18,12,18,17,18,16,20,15,19,10,16,20,15,16,15,18,10,14,16,14,12,£50000000,50000,170,72,20,15,messi001
Cristiano Ronaldo,ST RL,39,175,175,Portugal,Al Nassr,12,13,17,19,16,16,18,17,8,8,16,18,9,17,14,17,15,17,15,17,18,15,18,18,12,15,17,16,15,14,16,16,15,15,15,16,£30000000,45000,187,84,12,20,ronaldo001
Kevin De Bruyne,AM C,33,185,185,Belgium,Manchester City,16,18,16,15,18,17,10,18,7,9,20,16,11,19,10,18,13,18,16,19,17,17,16,16,14,17,20,17,14,15,17,12,16,15,16,14,£80000000,55000,181,70,20,12,debruyne001"""
    
    @pytest.fixture
    def temp_csv_file(self, sample_csv_content, tmp_path):
        """Create a temporary CSV file for testing"""
        csv_file = tmp_path / "test_players.csv"
        csv_file.write_text(sample_csv_content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def invalid_csv_file(self, tmp_path):
        """Create a CSV file with invalid data"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Invalid Player,ST,999,250,250,Unknown,No Club,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,£0,0,50,300,25,25,invalid001"""
        csv_file = tmp_path / "invalid_players.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def missing_columns_csv(self, tmp_path):
        """Create a CSV file with missing required columns"""
        content = """name,position,age
Messi,AM,37
Ronaldo,ST,39"""
        csv_file = tmp_path / "missing_columns.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def empty_csv_file(self, tmp_path):
        """Create an empty CSV file"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def duplicate_uid_csv(self, tmp_path):
        """Create a CSV file with duplicate UIDs"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Player One,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,duplicate001
Player Two,AM,26,155,165,Country,Club,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,duplicate001"""
        csv_file = tmp_path / "duplicate_uid.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    def test_init_with_valid_file(self, temp_csv_file):
        """Test initialization with a valid CSV file"""
        parser = PlayerCSVParser(temp_csv_file)
        assert parser.csv_path == Path(temp_csv_file)
        assert parser.encoding == 'utf-8'
    
    def test_init_with_nonexistent_file(self):
        """Test initialization with a non-existent file raises error"""
        with pytest.raises(CSVNotFoundError) as exc_info:
            PlayerCSVParser('nonexistent_file.csv')
        assert 'not found' in str(exc_info.value).lower()
    
    def test_init_with_custom_encoding(self, temp_csv_file):
        """Test initialization with custom encoding"""
        parser = PlayerCSVParser(temp_csv_file, encoding='utf-8-sig')
        assert parser.encoding == 'utf-8-sig'
    
    def test_load_valid_csv(self, temp_csv_file):
        """Test loading a valid CSV file"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3  # 3 players in sample
        assert 'name' in df.columns
        assert 'uid' in df.columns
        assert df.iloc[0]['name'] == 'Lionel Messi'
    
    def test_load_empty_csv_raises_error(self, empty_csv_file):
        """Test loading an empty CSV raises parse error"""
        parser = PlayerCSVParser(empty_csv_file)
        with pytest.raises(CSVParseError) as exc_info:
            parser.load()
        assert 'parse' in str(exc_info.value).lower() or 'column' in str(exc_info.value).lower()
    
    def test_load_missing_columns_raises_error(self, missing_columns_csv):
        """Test loading CSV with missing columns raises error"""
        parser = PlayerCSVParser(missing_columns_csv)
        with pytest.raises(CSVValidationError) as exc_info:
            parser.load()
        assert 'missing required columns' in str(exc_info.value).lower()
    
    def test_validate_row_valid_data(self, temp_csv_file):
        """Test validate_row with valid player data"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        # First row should be valid
        is_valid, errors = parser.validate_row(df.iloc[0])
        assert is_valid is True
        assert errors == []
    
    def test_validate_row_invalid_age(self, temp_csv_file):
        """Test validate_row rejects invalid age"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        # Modify age to invalid value
        row = df.iloc[0].copy()
        row['age'] = 999
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_row_invalid_ca(self, temp_csv_file):
        """Test validate_row rejects CA out of range"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        # Modify CA to invalid value
        row = df.iloc[0].copy()
        row['ca'] = 250
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_row_invalid_attribute(self, temp_csv_file):
        """Test validate_row rejects attribute out of range"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        # Modify attribute to invalid value
        row = df.iloc[0].copy()
        row['dribbling'] = 25
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_row_missing_required_field(self, temp_csv_file):
        """Test validate_row rejects missing required fields"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        # Remove required field
        row = df.iloc[0].copy()
        row['name'] = None
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_clean_data_removes_duplicates(self, duplicate_uid_csv):
        """Test clean_data removes duplicate UIDs"""
        parser = PlayerCSVParser(duplicate_uid_csv)
        df = parser.load()
        
        assert len(df) == 2  # Before cleaning
        
        clean_df, report = parser.clean_data(df)
        assert len(clean_df) == 1  # After cleaning, only one remains
        assert report['duplicates_removed'] == 1
    
    def test_clean_data_strips_whitespace(self, temp_csv_file):
        """Test clean_data strips whitespace from string fields"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        # Verify that string fields are properly stripped (no leading/trailing spaces)
        assert not clean_df.iloc[0]['name'].startswith(' ')
        assert not clean_df.iloc[0]['name'].endswith(' ')
        assert not clean_df.iloc[0]['position'].startswith(' ')
        assert not clean_df.iloc[0]['position'].endswith(' ')
        assert not clean_df.iloc[0]['uid'].startswith(' ')
        assert not clean_df.iloc[0]['uid'].endswith(' ')
    
    def test_clean_data_converts_numeric_fields(self, temp_csv_file):
        """Test clean_data converts numeric fields to correct types"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        # Check integer fields are Int64
        assert clean_df['age'].dtype == 'Int64'
        assert clean_df['ca'].dtype == 'Int64'
        assert clean_df['pa'].dtype == 'Int64'
        assert clean_df['dribbling'].dtype == 'Int64'
    
    def test_clean_data_filters_invalid_rows(self, invalid_csv_file):
        """Test clean_data filters out invalid rows"""
        parser = PlayerCSVParser(invalid_csv_file)
        df = parser.load()
        
        assert len(df) == 1  # Before cleaning
        
        clean_df, report = parser.clean_data(df)
        assert len(clean_df) == 0  # After cleaning, invalid row removed
        assert report['invalid_count'] == 1
    
    def test_clean_data_selects_required_columns(self, temp_csv_file):
        """Test clean_data selects only required columns"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        # All columns should be from REQUIRED_COLUMNS
        for col in clean_df.columns:
            assert col in parser.REQUIRED_COLUMNS
    
    def test_parse_csv_convenience_method(self, temp_csv_file):
        """Test parse_csv convenience method"""
        parser = PlayerCSVParser(temp_csv_file)
        df, report = parser.parse_csv(temp_csv_file)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        # Should be cleaned data
        assert df['age'].dtype == 'Int64'
        assert isinstance(report, dict)
    
    def test_parse_csv_with_nonexistent_file(self):
        """Test parse_csv with non-existent file raises error"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)  # Create without __init__
        parser.csv_path = Path('dummy.csv')
        parser.encoding = 'utf-8'
        
        with pytest.raises(CSVNotFoundError):
            parser.parse_csv('nonexistent.csv')
    
    def test_get_column_info(self, temp_csv_file):
        """Test get_column_info returns correct information"""
        parser = PlayerCSVParser(temp_csv_file)
        info = parser.get_column_info()
        
        assert 'column_count' in info
        assert 'columns' in info
        assert 'sample_row' in info
        assert info['column_count'] > 0
        assert 'name' in info['columns']
    
    def test_validate_player_data(self, temp_csv_file):
        """Test validate_player_data returns validation report"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        report = parser.validate_player_data(df)
        
        assert 'total_rows' in report
        assert 'valid_rows' in report
        assert 'issues' in report
        assert report['total_rows'] == 3
        assert report['valid_rows'] > 0
    
    def test_validate_player_data_detects_missing_values(self, tmp_path):
        """Test validate_player_data detects missing values"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Messi,,37,180,180,Argentina,Club,15,14,20,18,20,17,8,16,5,6,19,15,7,20,8,18,12,18,17,18,16,20,15,19,10,16,20,15,16,15,18,10,14,16,14,12,£50000000,50000,170,72,20,15,messi001"""
        csv_file = tmp_path / "missing_values.csv"
        csv_file.write_text(content, encoding='utf-8')
        
        parser = PlayerCSVParser(str(csv_file))
        df = parser.load()
        report = parser.validate_player_data(df)
        
        # Should detect missing position
        assert len(report['issues']) > 0
        missing_issues = [i for i in report['issues'] if i['type'] == 'missing_values']
        assert len(missing_issues) > 0


class TestLoadPlayersFromCSV:
    """Test suite for load_players_from_csv function that returns Player objects"""
    
    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Test Player,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,test001"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def multi_player_csv_file(self, tmp_path):
        """Create a CSV file with multiple players"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Player One,ST,25,150,160,Country A,Club A,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,player001
Player Two,AM,26,155,165,Country B,Club B,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,11,£1100000,11000,182,76,16,16,player002
Player Three,DF,27,145,155,Country C,Club C,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,£900000,9000,178,74,14,14,player003"""
        csv_file = tmp_path / "multi_test.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    def test_load_players_from_csv_returns_player_objects(self, sample_csv_file):
        """Test that load_players_from_csv returns Player model objects"""
        players, report = load_players_from_csv(sample_csv_file, db_session=None)
        
        assert isinstance(players, list)
        assert len(players) == 1
        assert isinstance(players[0], Player)
        assert isinstance(report, dict)
    
    def test_load_players_from_csv_maps_all_fields(self, sample_csv_file):
        """Test that all CSV fields are correctly mapped to Player model"""
        players, report = load_players_from_csv(sample_csv_file, db_session=None)
        player = players[0]
        
        # Basic fields
        assert player.name == 'Test Player'
        assert player.position == 'ST'
        assert player.age == 25
        assert player.ca == 150
        assert player.pa == 160
        assert player.nationality == 'Country'
        assert player.club == 'Club'
        assert player.uid == 'test001'
        
        # Technical attributes
        assert player.corners == 10
        assert player.crossing == 10
        assert player.dribbling == 10
        assert player.finishing == 10
        assert player.first_touch == 10
        assert player.free_kicks == 10
        assert player.heading == 10
        assert player.long_shots == 10
        assert player.long_throws == 10
        assert player.marking == 10
        assert player.passing == 10
        assert player.penalty == 10
        assert player.tackling == 10
        assert player.technique == 10
        
        # Mental attributes
        assert player.aggression == 10
        assert player.anticipation == 10
        assert player.bravery == 10
        assert player.composure == 10
        assert player.concentration == 10
        assert player.decisions == 10
        assert player.determination == 10
        assert player.flair == 10
        assert player.leadership == 10
        assert player.off_the_ball == 10
        assert player.positioning == 10
        assert player.teamwork == 10
        assert player.vision == 10
        assert player.work_rate == 10
        
        # Physical attributes
        assert player.acceleration == 10
        assert player.agility == 10
        assert player.balance == 10
        assert player.jumping == 10
        assert player.stamina == 10
        assert player.pace == 10
        assert player.endurance == 10
        assert player.strength == 10
        
        # Financial and physical stats
        assert player.price == '£1000000'
        assert player.wage == 10000
        assert player.height == 180
        assert player.weight == 75
        assert player.left_foot == 15
        assert player.right_foot == 15
    
    def test_load_players_from_csv_multiple_players(self, multi_player_csv_file):
        """Test loading multiple players from CSV"""
        players, report = load_players_from_csv(multi_player_csv_file, db_session=None)
        
        assert len(players) == 3
        assert all(isinstance(p, Player) for p in players)
        
        # Check that each player has unique data
        names = [p.name for p in players]
        assert names == ['Player One', 'Player Two', 'Player Three']
        
        uids = [p.uid for p in players]
        assert uids == ['player001', 'player002', 'player003']
    
    def test_load_players_from_csv_handles_invalid_rows(self, tmp_path):
        """Test that invalid rows are skipped with error logging"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Valid Player,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,valid001
Invalid Player,ST,999,250,250,Country,Club,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,£0,0,50,300,25,25,invalid001"""
        csv_file = tmp_path / "mixed_valid_invalid.csv"
        csv_file.write_text(content, encoding='utf-8')
        
        players, report = load_players_from_csv(str(csv_file), db_session=None)
        
        # Only valid player should be loaded (invalid row filtered by clean_data)
        assert len(players) == 1
        assert players[0].name == 'Valid Player'
        assert report['invalid_count'] == 1
    
    def test_load_players_from_csv_with_nonexistent_file(self):
        """Test that loading non-existent file raises error"""
        with pytest.raises(CSVNotFoundError):
            load_players_from_csv('nonexistent.csv', db_session=None)
    
    def test_load_players_from_csv_preserves_price_format(self, sample_csv_file):
        """Test that price field is preserved as string with currency symbols"""
        players, report = load_players_from_csv(sample_csv_file, db_session=None)
        player = players[0]
        
        # Price should be kept as string
        assert isinstance(player.price, str)
        assert player.price == '£1000000'


class TestCreatePlayerFromRow:
    """Test suite for _create_player_from_row helper function"""
    
    @pytest.fixture
    def valid_row(self):
        """Create a valid player row as pandas Series"""
        data = {
            'uid': 'test001',
            'name': 'Test Player',
            'position': 'ST',
            'age': 25,
            'ca': 150,
            'pa': 160,
            'nationality': 'Country',
            'club': 'Club',
            # Technical
            'corners': 10, 'crossing': 10, 'dribbling': 10, 'finishing': 10,
            'first_touch': 10, 'free_kicks': 10, 'heading': 10, 'long_shots': 10,
            'long_throws': 10, 'marking': 10, 'passing': 10, 'penalty': 10,
            'tackling': 10, 'technique': 10,
            # Mental
            'aggression': 10, 'anticipation': 10, 'bravery': 10, 'composure': 10,
            'concentration': 10, 'decisions': 10, 'determination': 10, 'flair': 10,
            'leadership': 10, 'off_the_ball': 10, 'positioning': 10, 'teamwork': 10,
            'vision': 10, 'work_rate': 10,
            # Physical
            'acceleration': 10, 'agility': 10, 'balance': 10, 'jumping': 10,
            'stamina': 10, 'pace': 10, 'endurance': 10, 'strength': 10,
            # Financial and physical stats
            'price': '£1000000', 'wage': 10000, 'height': 180, 'weight': 75,
            'left_foot': 15, 'right_foot': 15
        }
        return pd.Series(data)
    
    def test_create_player_from_valid_row(self, valid_row):
        """Test creating Player object from valid row"""
        player = _create_player_from_row(valid_row)
        
        assert isinstance(player, Player)
        assert player.name == 'Test Player'
        assert player.uid == 'test001'
        assert player.ca == 150
        assert player.pa == 160
    
    def test_create_player_from_row_missing_required_field(self, valid_row):
        """Test that missing required field raises ValueError"""
        row = valid_row.copy()
        row['name'] = None
        
        with pytest.raises(ValueError) as exc_info:
            _create_player_from_row(row)
        assert 'name' in str(exc_info.value).lower()
    
    def test_create_player_from_row_invalid_numeric_field(self, valid_row):
        """Test that invalid numeric field raises ValueError"""
        row = valid_row.copy()
        row['age'] = 'not a number'
        
        with pytest.raises(ValueError) as exc_info:
            _create_player_from_row(row)
        assert 'age' in str(exc_info.value).lower()
    
    def test_create_player_from_row_empty_string_field(self, valid_row):
        """Test that empty required string field raises ValueError"""
        row = valid_row.copy()
        row['uid'] = ''
        
        with pytest.raises(ValueError) as exc_info:
            _create_player_from_row(row)
        assert 'uid' in str(exc_info.value).lower()
    
    def test_create_player_from_row_allows_empty_price(self, valid_row):
        """Test that empty price field is allowed"""
        row = valid_row.copy()
        row['price'] = ''
        
        player = _create_player_from_row(row)
        assert player.price == ''
    
    def test_create_player_from_row_handles_nan_values(self, valid_row):
        """Test that NaN values in required fields raise ValueError"""
        row = valid_row.copy()
        row['nationality'] = pd.NA
        
        with pytest.raises(ValueError) as exc_info:
            _create_player_from_row(row)
        assert 'nationality' in str(exc_info.value).lower()


class TestDatabaseIntegration:
    """Test suite for database integration (if database is available)"""
    
    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
DB Test Player,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,dbtest001"""
        csv_file = tmp_path / "db_test.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    def test_player_objects_ready_for_bulk_insert(self, sample_csv_file):
        """Test that Player objects can be used with bulk_save_objects"""
        players, report = load_players_from_csv(sample_csv_file, db_session=None)
        
        # Verify that Player objects have all required attributes for database insertion
        player = players[0]
        
        # Check that all required database fields are present
        assert hasattr(player, 'uid')
        assert hasattr(player, 'name')
        assert hasattr(player, 'position')
        assert hasattr(player, 'age')
        assert hasattr(player, 'ca')
        assert hasattr(player, 'pa')
        
        # Check that Player object doesn't have an id yet (not persisted)
        assert player.id is None or not hasattr(player, 'id')


class TestLoadPlayersFromCSVLegacy:
    """Test suite for legacy load_players_from_csv function (DataFrame return)"""
    
    # Note: The old tests are preserved here for backward compatibility
    # The new load_players_from_csv returns Player objects, not DataFrame


class TestRealCSVFile:
    """Test suite for the actual 2600球员属性.csv file if it exists"""
    
    @pytest.fixture
    def real_csv_path(self):
        """Path to the real CSV file"""
        return 'fm26/2600球员属性.csv'
    
    def test_load_real_csv_if_exists(self, real_csv_path):
        """Test loading the real CSV file if it exists"""
        if not Path(real_csv_path).exists():
            pytest.skip("Real CSV file not found")
        
        parser = PlayerCSVParser(real_csv_path)
        df = parser.load()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'name' in df.columns
        assert 'uid' in df.columns
    
    def test_clean_real_csv_if_exists(self, real_csv_path):
        """Test cleaning the real CSV file if it exists"""
        if not Path(real_csv_path).exists():
            pytest.skip("Real CSV file not found")
        
        parser = PlayerCSVParser(real_csv_path)
        df = parser.load()
        clean_df = parser.clean_data(df)
        
        assert isinstance(clean_df, pd.DataFrame)
        assert len(clean_df) > 0
        # Should have cleaned data
        assert clean_df['age'].dtype == 'Int64'
        assert clean_df['ca'].dtype == 'Int64'
    
    def test_validate_real_csv_if_exists(self, real_csv_path):
        """Test validation of the real CSV file if it exists"""
        if not Path(real_csv_path).exists():
            pytest.skip("Real CSV file not found")
        
        parser = PlayerCSVParser(real_csv_path)
        df = parser.load()
        report = parser.validate_player_data(df)
        
        assert report['total_rows'] > 0
        assert report['valid_rows'] > 0
        # Most rows should be valid
        assert report['valid_rows'] / report['total_rows'] > 0.9


class TestErrorHandling:
    """Test suite for error handling"""
    
    def test_csv_not_found_error_inheritance(self):
        """Test CSVNotFoundError inherits from PlayerLoaderError"""
        assert issubclass(CSVNotFoundError, PlayerLoaderError)
    
    def test_csv_encoding_error_inheritance(self):
        """Test CSVEncodingError inherits from PlayerLoaderError"""
        assert issubclass(CSVEncodingError, PlayerLoaderError)
    
    def test_csv_parse_error_inheritance(self):
        """Test CSVParseError inherits from PlayerLoaderError"""
        assert issubclass(CSVParseError, PlayerLoaderError)
    
    def test_csv_validation_error_inheritance(self):
        """Test CSVValidationError inherits from PlayerLoaderError"""
        assert issubclass(CSVValidationError, PlayerLoaderError)
    
    def test_player_loader_error_is_exception(self):
        """Test PlayerLoaderError inherits from Exception"""
        assert issubclass(PlayerLoaderError, Exception)



class TestEnhancedValidation:
    """Test suite for enhanced validation in Task 3.2"""
    
    @pytest.fixture
    def temp_csv_file(self, tmp_path):
        """Create a temporary CSV file for testing"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Lionel Messi,AM/ST RL,37,180,180,Argentina,Inter Miami,15,14,20,18,20,17,8,16,5,6,19,15,7,20,8,18,12,18,17,18,16,20,15,19,10,16,20,15,16,15,18,10,14,16,14,12,£50000000,50000,170,72,20,15,messi001
Cristiano Ronaldo,ST RL,39,175,175,Portugal,Al Nassr,12,13,17,19,16,16,18,17,8,8,16,18,9,17,14,17,15,17,15,17,18,15,18,18,12,15,17,16,15,14,16,16,15,15,15,16,£30000000,45000,187,84,12,20,ronaldo001
Kevin De Bruyne,AM C,33,185,185,Belgium,Manchester City,16,18,16,15,18,17,10,18,7,9,20,16,11,19,10,18,13,18,16,19,17,17,16,16,14,17,20,17,14,15,17,12,16,15,16,14,£80000000,55000,181,70,20,12,debruyne001"""
        csv_file = tmp_path / "test_players.csv"
        csv_file.write_text(content, encoding='utf-8')
        return str(csv_file)
    
    @pytest.fixture
    def valid_player_row(self):
        """Create a valid player row with all attributes"""
        data = {
            'uid': 'test001',
            'name': 'Test Player',
            'position': 'ST',
            'age': 25,
            'ca': 150,
            'pa': 160,
            'nationality': 'Country',
            'club': 'Club',
            # Technical (14 attributes)
            'corners': 10, 'crossing': 10, 'dribbling': 10, 'finishing': 10,
            'first_touch': 10, 'free_kicks': 10, 'heading': 10, 'long_shots': 10,
            'long_throws': 10, 'marking': 10, 'passing': 10, 'penalty': 10,
            'tackling': 10, 'technique': 10,
            # Mental (14 attributes)
            'aggression': 10, 'anticipation': 10, 'bravery': 10, 'composure': 10,
            'concentration': 10, 'decisions': 10, 'determination': 10, 'flair': 10,
            'leadership': 10, 'off_the_ball': 10, 'positioning': 10, 'teamwork': 10,
            'vision': 10, 'work_rate': 10,
            # Physical (8 attributes)
            'acceleration': 10, 'agility': 10, 'balance': 10, 'jumping': 10,
            'stamina': 10, 'pace': 10, 'endurance': 10, 'strength': 10,
            # Financial and physical stats
            'price': '£1000000', 'wage': 10000, 'height': 180, 'weight': 75,
            'left_foot': 15, 'right_foot': 15
        }
        return pd.Series(data)
    
    def test_validate_row_returns_tuple(self, temp_csv_file):
        """Test that validate_row returns tuple with bool and error list"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        result = parser.validate_row(df.iloc[0])
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)
    
    def test_validate_row_valid_data_returns_true_empty_errors(self, temp_csv_file):
        """Test that valid row returns True with empty error list"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        is_valid, errors = parser.validate_row(df.iloc[0])
        assert is_valid is True
        assert errors == []
    
    def test_validate_row_invalid_age_boundary_low(self, valid_player_row):
        """Test validation rejects age below 15"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['age'] = 14
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) > 0
        assert any('age' in error.lower() for error in errors)
    
    def test_validate_row_invalid_age_boundary_high(self, valid_player_row):
        """Test validation rejects age above 45"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['age'] = 46
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) > 0
        assert any('age' in error.lower() for error in errors)
    
    def test_validate_row_valid_age_boundaries(self, valid_player_row):
        """Test validation accepts age at boundaries (15 and 45)"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        # Test age 15
        row = valid_player_row.copy()
        row['age'] = 15
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
        
        # Test age 45
        row['age'] = 45
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
    
    def test_validate_row_invalid_ca_boundary_low(self, valid_player_row):
        """Test validation rejects CA below 1"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['ca'] = 0
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('ca' in error.lower() for error in errors)
    
    def test_validate_row_invalid_ca_boundary_high(self, valid_player_row):
        """Test validation rejects CA above 200"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['ca'] = 201
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('ca' in error.lower() for error in errors)
    
    def test_validate_row_invalid_pa_boundary_low(self, valid_player_row):
        """Test validation rejects PA below 1"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['pa'] = 0
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('pa' in error.lower() for error in errors)
    
    def test_validate_row_invalid_pa_boundary_high(self, valid_player_row):
        """Test validation rejects PA above 200"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['pa'] = 201
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('pa' in error.lower() for error in errors)
    
    def test_validate_row_all_technical_attributes(self, valid_player_row):
        """Test validation checks all 14 technical attributes"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        technical_attrs = [
            'corners', 'crossing', 'dribbling', 'finishing', 'first_touch',
            'free_kicks', 'heading', 'long_shots', 'long_throws', 'marking',
            'passing', 'penalty', 'tackling', 'technique'
        ]
        
        for attr in technical_attrs:
            row = valid_player_row.copy()
            row[attr] = 0  # Invalid value
            
            is_valid, errors = parser.validate_row(row)
            assert is_valid is False, f"Should reject invalid {attr}"
            assert any(attr in error for error in errors), f"Should mention {attr} in error"
    
    def test_validate_row_all_mental_attributes(self, valid_player_row):
        """Test validation checks all 14 mental attributes"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        mental_attrs = [
            'aggression', 'anticipation', 'bravery', 'composure', 'concentration',
            'decisions', 'determination', 'flair', 'leadership', 'off_the_ball',
            'positioning', 'teamwork', 'vision', 'work_rate'
        ]
        
        for attr in mental_attrs:
            row = valid_player_row.copy()
            row[attr] = 21  # Invalid value (above 20)
            
            is_valid, errors = parser.validate_row(row)
            assert is_valid is False, f"Should reject invalid {attr}"
            assert any(attr in error for error in errors), f"Should mention {attr} in error"
    
    def test_validate_row_all_physical_attributes(self, valid_player_row):
        """Test validation checks all 8 physical attributes"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        physical_attrs = [
            'acceleration', 'agility', 'balance', 'jumping',
            'stamina', 'pace', 'endurance', 'strength'
        ]
        
        for attr in physical_attrs:
            row = valid_player_row.copy()
            row[attr] = 0  # Invalid value
            
            is_valid, errors = parser.validate_row(row)
            assert is_valid is False, f"Should reject invalid {attr}"
            assert any(attr in error for error in errors), f"Should mention {attr} in error"
    
    def test_validate_row_foot_abilities(self, valid_player_row):
        """Test validation checks left_foot and right_foot attributes"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        # Test left_foot
        row = valid_player_row.copy()
        row['left_foot'] = 0
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('left_foot' in error for error in errors)
        
        # Test right_foot
        row = valid_player_row.copy()
        row['right_foot'] = 21
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('right_foot' in error for error in errors)
    
    def test_validate_row_height_boundaries(self, valid_player_row):
        """Test validation checks height range (150-220 cm)"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        # Below minimum
        row = valid_player_row.copy()
        row['height'] = 149
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('height' in error.lower() for error in errors)
        
        # Above maximum
        row['height'] = 221
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('height' in error.lower() for error in errors)
        
        # At boundaries (should be valid)
        row['height'] = 150
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
        
        row['height'] = 220
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
    
    def test_validate_row_weight_boundaries(self, valid_player_row):
        """Test validation checks weight range (50-120 kg)"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        # Below minimum
        row = valid_player_row.copy()
        row['weight'] = 49
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('weight' in error.lower() for error in errors)
        
        # Above maximum
        row['weight'] = 121
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('weight' in error.lower() for error in errors)
        
        # At boundaries (should be valid)
        row['weight'] = 50
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
        
        row['weight'] = 120
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
    
    def test_validate_row_wage_non_negative(self, valid_player_row):
        """Test validation checks wage is non-negative"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['wage'] = -1000
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert any('wage' in error.lower() for error in errors)
        
        # Zero wage should be valid
        row['wage'] = 0
        is_valid, errors = parser.validate_row(row)
        assert is_valid is True
    
    def test_validate_row_missing_required_fields(self, valid_player_row):
        """Test validation checks all required fields"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        required_fields = ['name', 'position', 'nationality', 'club', 'uid']
        
        for field in required_fields:
            row = valid_player_row.copy()
            row[field] = None
            
            is_valid, errors = parser.validate_row(row)
            assert is_valid is False, f"Should reject missing {field}"
            assert any(field in error for error in errors), f"Should mention {field} in error"
    
    def test_validate_row_empty_required_fields(self, valid_player_row):
        """Test validation rejects empty string required fields"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        required_fields = ['name', 'position', 'nationality', 'club', 'uid']
        
        for field in required_fields:
            row = valid_player_row.copy()
            row[field] = ''
            
            is_valid, errors = parser.validate_row(row)
            assert is_valid is False, f"Should reject empty {field}"
            assert any(field in error for error in errors), f"Should mention {field} in error"
    
    def test_validate_row_multiple_errors(self, valid_player_row):
        """Test validation returns all errors for a row with multiple issues"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.ATTRIBUTE_COLUMNS = PlayerCSVParser.ATTRIBUTE_COLUMNS
        
        row = valid_player_row.copy()
        row['age'] = 999  # Invalid age
        row['ca'] = 250  # Invalid CA
        row['dribbling'] = 25  # Invalid attribute
        row['height'] = 50  # Invalid height
        
        is_valid, errors = parser.validate_row(row)
        assert is_valid is False
        assert len(errors) >= 4  # Should have at least 4 errors
        assert any('age' in error.lower() for error in errors)
        assert any('ca' in error.lower() for error in errors)
        assert any('dribbling' in error for error in errors)
        assert any('height' in error.lower() for error in errors)
    
    def test_clean_data_returns_tuple(self, temp_csv_file):
        """Test that clean_data returns tuple with DataFrame and report"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        result = parser.clean_data(df)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], pd.DataFrame)
        assert isinstance(result[1], dict)
    
    def test_clean_data_validation_report_structure(self, temp_csv_file):
        """Test that validation report has expected structure"""
        parser = PlayerCSVParser(temp_csv_file)
        df = parser.load()
        
        clean_df, report = parser.clean_data(df)
        
        assert 'original_count' in report
        assert 'duplicates_removed' in report
        assert 'invalid_count' in report
        assert 'valid_count' in report
        assert 'validation_errors' in report
        assert 'error_summary' in report
        
        assert isinstance(report['original_count'], (int, np.integer))
        assert isinstance(report['duplicates_removed'], (int, np.integer))
        assert isinstance(report['invalid_count'], (int, np.integer))
        assert isinstance(report['valid_count'], (int, np.integer))
        assert isinstance(report['validation_errors'], list)
        assert isinstance(report['error_summary'], dict)
    
    def test_clean_data_filters_invalid_rows_with_report(self, tmp_path):
        """Test that clean_data filters invalid rows and reports them"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Valid Player,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,valid001
Invalid Player,ST,999,250,250,Country,Club,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,£0,0,50,300,25,25,invalid001"""
        csv_file = tmp_path / "mixed_valid_invalid.csv"
        csv_file.write_text(content, encoding='utf-8')
        
        parser = PlayerCSVParser(str(csv_file))
        df = parser.load()
        clean_df, report = parser.clean_data(df)
        
        assert report['original_count'] == 2
        assert report['valid_count'] == 1
        assert report['invalid_count'] == 1
        assert len(report['validation_errors']) == 1
        assert report['validation_errors'][0]['player_name'] == 'Invalid Player'
        assert len(report['validation_errors'][0]['errors']) > 0
    
    def test_load_players_from_csv_returns_tuple(self, tmp_path):
        """Test that load_players_from_csv returns tuple with players and report"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Test Player,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,test001"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(content, encoding='utf-8')
        
        result = load_players_from_csv(str(csv_file), db_session=None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], dict)
    
    def test_load_players_from_csv_validation_report(self, tmp_path):
        """Test that load_players_from_csv returns comprehensive validation report"""
        content = """name,position,age,ca,pa,nationality,club,corners,crossing,dribbling,finishing,first_touch,free_kicks,heading,long_shots,long_throws,marking,passing,penalty,tackling,technique,aggression,anticipation,bravery,composure,concentration,decisions,determination,flair,leadership,off_the_ball,positioning,teamwork,vision,work_rate,acceleration,agility,balance,jumping,stamina,pace,endurance,strength,price,wage,height,weight,left_foot,right_foot,uid
Test Player,ST,25,150,160,Country,Club,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,10,£1000000,10000,180,75,15,15,test001"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(content, encoding='utf-8')
        
        players, report = load_players_from_csv(str(csv_file), db_session=None)
        
        assert 'original_count' in report
        assert 'valid_count' in report
        assert 'invalid_count' in report
        assert 'successfully_created' in report
        assert 'player_creation_failures' in report
        assert 'detailed_validation' in report
        
        assert report['successfully_created'] == len(players)
        assert report['player_creation_failures'] == 0
    
    def test_parse_csv_returns_tuple(self, temp_csv_file):
        """Test that parse_csv returns tuple with DataFrame and report"""
        parser = PlayerCSVParser.__new__(PlayerCSVParser)
        parser.csv_path = Path('dummy.csv')
        parser.encoding = 'utf-8'
        
        result = parser.parse_csv(temp_csv_file)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], pd.DataFrame)
        assert isinstance(result[1], dict)
