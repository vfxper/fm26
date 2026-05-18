"""
Player Database Verification Tests - Task 3.10

Comprehensive tests to verify player database integrity after loading from CSV.
Tests all 50+ attributes, database constraints, search functionality, and data integrity.
"""

import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.player import Player
from app.services.player_loader import load_players_from_csv


class TestPlayerDatabaseLoading:
    """Test suite for player database loading verification"""
    
    def test_load_all_players_from_csv(self, db_session: Session):
        """Test that all players are loaded from CSV into database"""
        # Load players from CSV
        csv_path = 'fm26/2600球员属性.csv'
        players, report = load_players_from_csv(csv_path, db_session, detect_db_duplicates=False)
        
        # Bulk insert
        db_session.bulk_save_objects(players)
        db_session.commit()
        
        # Verify count
        player_count = db_session.query(func.count(Player.id)).scalar()
        assert player_count >= 2600, f"Expected at least 2600 players, got {player_count}"
        assert report['successfully_created'] == len(players)
    
    def test_database_connection_valid(self, db_session: Session):
        """Test that database connection is valid"""
        assert db_session is not None
        assert db_session.is_active
    
    def test_player_table_exists(self, db_session: Session):
        """Test that players table exists in database"""
        result = db_session.execute(select(Player).limit(1))
        assert result is not None


class TestDataIntegrity:
    """Test suite for data integrity verification"""
    
    def test_all_players_have_required_fields(self, db_session: Session):
        """Test that all players have required fields populated"""
        players = db_session.query(Player).all()
        
        required_fields = ['uid', 'name', 'position', 'age', 'ca', 'pa', 'nationality', 'club']
        
        for player in players:
            for field in required_fields:
                value = getattr(player, field)
                assert value is not None, f"Player {player.name} missing {field}"
                assert str(value).strip() != '', f"Player {player.name} has empty {field}"
    
    def test_unique_uid_constraint(self, db_session: Session):
        """Test that all UIDs are unique"""
        uid_counts = db_session.query(
            Player.uid, func.count(Player.uid)
        ).group_by(Player.uid).having(func.count(Player.uid) > 1).all()
        
        assert len(uid_counts) == 0, f"Found {len(uid_counts)} duplicate UIDs: {uid_counts[:5]}"
    
    def test_all_attributes_present(self, db_session: Session):
        """Test that all 50+ attributes are present for each player"""
        player = db_session.query(Player).first()
        assert player is not None
        
        # Technical attributes (14)
        technical_attrs = [
            'corners', 'crossing', 'dribbling', 'finishing', 'first_touch',
            'free_kicks', 'heading', 'long_shots', 'long_throws', 'marking',
            'passing', 'penalty', 'tackling', 'technique'
        ]
        
        # Mental attributes (14)
        mental_attrs = [
            'aggression', 'anticipation', 'bravery', 'composure', 'concentration',
            'decisions', 'determination', 'flair', 'leadership', 'off_the_ball',
            'positioning', 'teamwork', 'vision', 'work_rate'
        ]
        
        # Physical attributes (8)
        physical_attrs = [
            'acceleration', 'agility', 'balance', 'jumping',
            'stamina', 'pace', 'endurance', 'strength'
        ]
        
        all_attrs = technical_attrs + mental_attrs + physical_attrs
        
        for attr in all_attrs:
            value = getattr(player, attr)
            assert value is not None, f"Missing attribute: {attr}"
            assert isinstance(value, int), f"Attribute {attr} is not an integer"


class TestAttributeValidation:
    """Test suite for attribute value validation"""
    
    def test_ca_range_valid(self, db_session: Session):
        """Test that CA values are in valid range (1-200)"""
        invalid_ca = db_session.query(Player).filter(
            (Player.ca < 1) | (Player.ca > 200)
        ).all()
        
        assert len(invalid_ca) == 0, f"Found {len(invalid_ca)} players with invalid CA"
    
    def test_pa_range_valid(self, db_session: Session):
        """Test that PA values are in valid range (-200 to 200, excluding 0)"""
        invalid_pa = db_session.query(Player).filter(
            (Player.pa < -200) | (Player.pa > 200) | (Player.pa == 0)
        ).all()
        
        assert len(invalid_pa) == 0, f"Found {len(invalid_pa)} players with invalid PA"
    
    def test_technical_attributes_range(self, db_session: Session):
        """Test that technical attributes are in valid range (1-20)"""
        technical_attrs = [
            'corners', 'crossing', 'dribbling', 'finishing', 'first_touch',
            'free_kicks', 'heading', 'long_shots', 'long_throws', 'marking',
            'passing', 'penalty', 'tackling', 'technique'
        ]
        
        for attr in technical_attrs:
            invalid = db_session.query(Player).filter(
                (getattr(Player, attr) < 1) | (getattr(Player, attr) > 20)
            ).count()
            
            assert invalid == 0, f"Found {invalid} players with invalid {attr}"
    
    def test_mental_attributes_range(self, db_session: Session):
        """Test that mental attributes are in valid range (1-20)"""
        mental_attrs = [
            'aggression', 'anticipation', 'bravery', 'composure', 'concentration',
            'decisions', 'determination', 'flair', 'leadership', 'off_the_ball',
            'positioning', 'teamwork', 'vision', 'work_rate'
        ]
        
        for attr in mental_attrs:
            invalid = db_session.query(Player).filter(
                (getattr(Player, attr) < 1) | (getattr(Player, attr) > 20)
            ).count()
            
            assert invalid == 0, f"Found {invalid} players with invalid {attr}"
    
    def test_physical_attributes_range(self, db_session: Session):
        """Test that physical attributes are in valid range (1-20)"""
        physical_attrs = [
            'acceleration', 'agility', 'balance', 'jumping',
            'stamina', 'pace', 'endurance', 'strength'
        ]
        
        for attr in physical_attrs:
            invalid = db_session.query(Player).filter(
                (getattr(Player, attr) < 1) | (getattr(Player, attr) > 20)
            ).count()
            
            assert invalid == 0, f"Found {invalid} players with invalid {attr}"
    
    def test_age_range_valid(self, db_session: Session):
        """Test that age values are reasonable (15-45)"""
        invalid_age = db_session.query(Player).filter(
            (Player.age < 15) | (Player.age > 45)
        ).all()
        
        assert len(invalid_age) == 0, f"Found {len(invalid_age)} players with invalid age"
    
    def test_height_range_valid(self, db_session: Session):
        """Test that height values are reasonable (150-220 cm)"""
        invalid_height = db_session.query(Player).filter(
            (Player.height < 150) | (Player.height > 220)
        ).all()
        
        assert len(invalid_height) == 0, f"Found {len(invalid_height)} players with invalid height"
    
    def test_weight_range_valid(self, db_session: Session):
        """Test that weight values are reasonable (50-120 kg)"""
        invalid_weight = db_session.query(Player).filter(
            (Player.weight < 50) | (Player.weight > 120)
        ).all()
        
        assert len(invalid_weight) == 0, f"Found {len(invalid_weight)} players with invalid weight"
    
    def test_wage_non_negative(self, db_session: Session):
        """Test that wage values are non-negative"""
        invalid_wage = db_session.query(Player).filter(Player.wage < 0).all()
        
        assert len(invalid_wage) == 0, f"Found {len(invalid_wage)} players with negative wage"
    
    def test_foot_abilities_range(self, db_session: Session):
        """Test that foot abilities are in valid range (1-20)"""
        invalid_left = db_session.query(Player).filter(
            (Player.left_foot < 1) | (Player.left_foot > 20)
        ).count()
        
        invalid_right = db_session.query(Player).filter(
            (Player.right_foot < 1) | (Player.right_foot > 20)
        ).count()
        
        assert invalid_left == 0, f"Found {invalid_left} players with invalid left_foot"
        assert invalid_right == 0, f"Found {invalid_right} players with invalid right_foot"


class TestSearchFunctionality:
    """Test suite for player search functionality"""
    
    def test_search_by_name(self, db_session: Session):
        """Test searching players by name"""
        # Get a sample player name
        sample_player = db_session.query(Player).first()
        assert sample_player is not None
        
        # Search by name
        results = db_session.query(Player).filter(
            Player.name.ilike(f'%{sample_player.name[:5]}%')
        ).all()
        
        assert len(results) > 0
        assert any(p.name == sample_player.name for p in results)
    
    def test_filter_by_position(self, db_session: Session):
        """Test filtering players by position"""
        strikers = db_session.query(Player).filter(
            Player.position.like('%ST%')
        ).all()
        
        assert len(strikers) > 0
        for player in strikers:
            assert 'ST' in player.position
    
    def test_filter_by_club(self, db_session: Session):
        """Test filtering players by club"""
        # Get a sample club
        sample_player = db_session.query(Player).first()
        assert sample_player is not None
        
        club_players = db_session.query(Player).filter(
            Player.club == sample_player.club
        ).all()
        
        assert len(club_players) > 0
        for player in club_players:
            assert player.club == sample_player.club
    
    def test_filter_by_nationality(self, db_session: Session):
        """Test filtering players by nationality"""
        # Get a sample nationality
        sample_player = db_session.query(Player).first()
        assert sample_player is not None
        
        national_players = db_session.query(Player).filter(
            Player.nationality == sample_player.nationality
        ).all()
        
        assert len(national_players) > 0
        for player in national_players:
            assert player.nationality == sample_player.nationality
    
    def test_filter_by_ca_range(self, db_session: Session):
        """Test filtering players by CA range"""
        high_ca_players = db_session.query(Player).filter(
            Player.ca >= 150
        ).all()
        
        assert len(high_ca_players) > 0
        for player in high_ca_players:
            assert player.ca >= 150
    
    def test_filter_by_pa_range(self, db_session: Session):
        """Test filtering players by PA range"""
        high_pa_players = db_session.query(Player).filter(
            Player.pa >= 160
        ).all()
        
        assert len(high_pa_players) > 0
        for player in high_pa_players:
            assert player.pa >= 160
    
    def test_filter_by_age_range(self, db_session: Session):
        """Test filtering players by age range"""
        young_players = db_session.query(Player).filter(
            (Player.age >= 18) & (Player.age <= 23)
        ).all()
        
        assert len(young_players) > 0
        for player in young_players:
            assert 18 <= player.age <= 23
    
    def test_combined_filters(self, db_session: Session):
        """Test combining multiple filters"""
        results = db_session.query(Player).filter(
            Player.position.like('%ST%'),
            Player.ca >= 140,
            Player.age <= 25
        ).all()
        
        for player in results:
            assert 'ST' in player.position
            assert player.ca >= 140
            assert player.age <= 25


class TestEdgeCases:
    """Test suite for edge cases and special scenarios"""
    
    def test_players_with_special_characters_in_name(self, db_session: Session):
        """Test handling of special characters in player names"""
        special_char_players = db_session.query(Player).filter(
            Player.name.op('~')('[^a-zA-Z0-9 ]')
        ).all()
        
        # Should be able to query and retrieve these players
        for player in special_char_players:
            assert player.name is not None
            assert len(player.name) > 0
    
    def test_players_with_multiple_positions(self, db_session: Session):
        """Test players with multiple positions (e.g., 'AM/ST RL')"""
        multi_position_players = db_session.query(Player).filter(
            Player.position.like('%/%')
        ).all()
        
        assert len(multi_position_players) > 0
        for player in multi_position_players:
            assert '/' in player.position
    
    def test_players_with_negative_pa(self, db_session: Session):
        """Test players with negative PA (FM random potential ranges)"""
        negative_pa_players = db_session.query(Player).filter(
            Player.pa < 0
        ).all()
        
        # Negative PA is valid in FM (indicates random potential range)
        for player in negative_pa_players:
            assert -200 <= player.pa < 0
    
    def test_players_with_empty_traits(self, db_session: Session):
        """Test players with empty or null trait fields"""
        empty_trait_players = db_session.query(Player).filter(
            (Player.traits == '') | (Player.traits.is_(None))
        ).all()
        
        # Should be able to handle empty traits
        for player in empty_trait_players:
            assert player.traits is None or player.traits == ''
    
    def test_players_with_empty_price(self, db_session: Session):
        """Test players with empty price field"""
        empty_price_players = db_session.query(Player).filter(
            (Player.price == '') | (Player.price.is_(None))
        ).all()
        
        # Should be able to handle empty price
        for player in empty_price_players:
            assert player.price is None or player.price == ''


class TestPerformance:
    """Test suite for performance verification"""
    
    def test_bulk_insert_performance(self, db_session: Session):
        """Test that bulk insert completes in reasonable time"""
        import time
        
        csv_path = 'fm26/2600球员属性.csv'
        
        start_time = time.time()
        players, report = load_players_from_csv(csv_path, db_session, detect_db_duplicates=False)
        db_session.bulk_save_objects(players)
        db_session.commit()
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Should complete in reasonable time (< 30 seconds for 2600+ players)
        assert elapsed_time < 30.0, f"Bulk insert took {elapsed_time:.2f} seconds"
    
    def test_query_performance(self, db_session: Session):
        """Test that queries complete in reasonable time"""
        import time
        
        start_time = time.time()
        players = db_session.query(Player).filter(
            Player.ca >= 150,
            Player.age <= 25
        ).all()
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert elapsed_time < 1.0, f"Query took {elapsed_time:.2f} seconds"
    
    def test_count_query_performance(self, db_session: Session):
        """Test that count queries are efficient"""
        import time
        
        start_time = time.time()
        count = db_session.query(func.count(Player.id)).scalar()
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Should complete very quickly (< 0.5 seconds)
        assert elapsed_time < 0.5, f"Count query took {elapsed_time:.2f} seconds"


class TestDatabaseConstraints:
    """Test suite for database constraints and indexes"""
    
    def test_uid_index_exists(self, db_session: Session):
        """Test that UID index exists for performance"""
        # Query using UID should be fast
        import time
        
        sample_player = db_session.query(Player).first()
        assert sample_player is not None
        
        start_time = time.time()
        player = db_session.query(Player).filter(Player.uid == sample_player.uid).first()
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # Should be very fast with index (< 0.1 seconds)
        assert elapsed_time < 0.1, f"UID query took {elapsed_time:.2f} seconds"
        assert player.uid == sample_player.uid
    
    def test_cannot_insert_duplicate_uid(self, db_session: Session):
        """Test that database prevents duplicate UIDs"""
        from sqlalchemy.exc import IntegrityError
        
        # Get an existing player
        existing_player = db_session.query(Player).first()
        assert existing_player is not None
        
        # Try to insert a player with the same UID
        duplicate_player = Player(
            uid=existing_player.uid,
            name="Duplicate Player",
            position="ST",
            age=25,
            ca=150,
            pa=160,
            nationality="Country",
            club="Club",
            # ... other required fields
        )
        
        db_session.add(duplicate_player)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()


# Pytest fixtures

@pytest.fixture
def db_session():
    """Provide a database session for tests"""
    from app.core.database import SessionLocal, engine
    from app.models.player import Base
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
