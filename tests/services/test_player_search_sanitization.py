"""
Unit tests for Player Search Service with Sanitization

Tests the integration of sanitization into PlayerSearchFilters to ensure
all user inputs are properly validated and sanitized.

Task 9.7: Add search query validation and sanitization
"""

import pytest
from app.services.player_search import PlayerSearchFilters


class TestPlayerSearchFiltersSanitization:
    """Test suite for PlayerSearchFilters with sanitization"""
    
    def test_search_text_sanitization(self):
        """Test that search_text is automatically sanitized"""
        # Valid search text
        filters = PlayerSearchFilters(search_text="Messi", order_by="relevance")
        assert filters.search_text == "Messi"
        
        # Whitespace trimming
        filters = PlayerSearchFilters(search_text="  Ronaldo  ", order_by="relevance")
        assert filters.search_text == "Ronaldo"
        
        # Multiple spaces normalized
        filters = PlayerSearchFilters(search_text="Lionel   Messi", order_by="relevance")
        assert filters.search_text == "Lionel Messi"
        
        # Empty string becomes None
        filters = PlayerSearchFilters(search_text="", order_by="ca")
        assert filters.search_text is None
    
    def test_search_text_sql_injection_blocked(self):
        """Test that SQL injection in search_text is blocked"""
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            PlayerSearchFilters(search_text="'; DROP TABLE players; --")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            PlayerSearchFilters(search_text="1' OR '1'='1")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            PlayerSearchFilters(search_text="UNION SELECT * FROM users")
    
    def test_search_text_xss_blocked(self):
        """Test that XSS in search_text is blocked"""
        with pytest.raises(ValueError, match="dangerous HTML/JavaScript patterns"):
            PlayerSearchFilters(search_text="<script>alert('XSS')</script>")
        
        with pytest.raises(ValueError, match="dangerous HTML/JavaScript patterns"):
            PlayerSearchFilters(search_text="<img src=x onerror=alert(1)>")
    
    def test_position_sanitization(self):
        """Test that position filter is sanitized"""
        # Valid positions
        filters = PlayerSearchFilters(position="ST")
        assert filters.position == "ST"
        
        filters = PlayerSearchFilters(position="AM/ST RL")
        assert filters.position == "AM/ST RL"
        
        # Whitespace trimming
        filters = PlayerSearchFilters(position="  D C  ")
        assert filters.position == "D C"
        
        # Empty becomes None
        filters = PlayerSearchFilters(position="")
        assert filters.position is None
    
    def test_position_invalid_characters_blocked(self):
        """Test that invalid characters in position are blocked"""
        with pytest.raises(ValueError, match="invalid characters"):
            PlayerSearchFilters(position="ST'; DROP TABLE")
        
        with pytest.raises(ValueError, match="invalid characters"):
            PlayerSearchFilters(position="ST@#$")
    
    def test_nationality_sanitization(self):
        """Test that nationality filter is sanitized"""
        filters = PlayerSearchFilters(nationality="Argentina")
        assert filters.nationality == "Argentina"
        
        filters = PlayerSearchFilters(nationality="  Brazil  ")
        assert filters.nationality == "Brazil"
        
        filters = PlayerSearchFilters(nationality="")
        assert filters.nationality is None
    
    def test_nationality_invalid_characters_blocked(self):
        """Test that invalid characters in nationality are blocked"""
        with pytest.raises(ValueError, match="invalid characters"):
            PlayerSearchFilters(nationality="Argentina'; DROP TABLE")
    
    def test_club_sanitization(self):
        """Test that club filter is sanitized"""
        filters = PlayerSearchFilters(club="Manchester United")
        assert filters.club == "Manchester United"
        
        filters = PlayerSearchFilters(club="  Barcelona  ")
        assert filters.club == "Barcelona"
        
        filters = PlayerSearchFilters(club="")
        assert filters.club is None
    
    def test_club_invalid_characters_blocked(self):
        """Test that invalid characters in club are blocked"""
        with pytest.raises(ValueError, match="invalid characters"):
            PlayerSearchFilters(club="Barcelona<script>alert(1)</script>")
    
    def test_numeric_filters_type_validation(self):
        """Test that numeric filters are type-checked"""
        # Valid integers
        filters = PlayerSearchFilters(min_age=18, max_age=30)
        filters.validate()  # Should not raise
        
        # Invalid types should raise TypeError during validation
        filters = PlayerSearchFilters(min_age="18")  # String instead of int
        with pytest.raises(TypeError, match="min_age must be an integer"):
            filters.validate()
        
        filters = PlayerSearchFilters(min_ca=150.5)  # Float instead of int
        with pytest.raises(TypeError, match="min_ca must be an integer"):
            filters.validate()
    
    def test_age_range_validation(self):
        """Test age range validation"""
        # Valid ranges
        filters = PlayerSearchFilters(min_age=18, max_age=30)
        filters.validate()  # Should not raise
        
        # Invalid: min > max
        filters = PlayerSearchFilters(min_age=30, max_age=18)
        with pytest.raises(ValueError, match="min_age cannot be greater than max_age"):
            filters.validate()
        
        # Invalid: below minimum
        filters = PlayerSearchFilters(min_age=10)
        with pytest.raises(ValueError, match="min_age must be between 15 and 50"):
            filters.validate()
        
        # Invalid: above maximum
        filters = PlayerSearchFilters(max_age=60)
        with pytest.raises(ValueError, match="max_age must be between 15 and 50"):
            filters.validate()
    
    def test_ca_range_validation(self):
        """Test CA range validation"""
        # Valid ranges
        filters = PlayerSearchFilters(min_ca=100, max_ca=200)
        filters.validate()  # Should not raise
        
        # Invalid: min > max
        filters = PlayerSearchFilters(min_ca=200, max_ca=100)
        with pytest.raises(ValueError, match="min_ca cannot be greater than max_ca"):
            filters.validate()
        
        # Invalid: below minimum
        filters = PlayerSearchFilters(min_ca=0)
        with pytest.raises(ValueError, match="min_ca must be between 1 and 200"):
            filters.validate()
        
        # Invalid: above maximum
        filters = PlayerSearchFilters(max_ca=250)
        with pytest.raises(ValueError, match="max_ca must be between 1 and 200"):
            filters.validate()
    
    def test_pa_range_validation(self):
        """Test PA range validation"""
        # Valid ranges
        filters = PlayerSearchFilters(min_pa=-200, max_pa=200)
        filters.validate()  # Should not raise
        
        # Invalid: min > max
        filters = PlayerSearchFilters(min_pa=200, max_pa=-100)
        with pytest.raises(ValueError, match="min_pa cannot be greater than max_pa"):
            filters.validate()
        
        # Invalid: below minimum
        filters = PlayerSearchFilters(min_pa=-250)
        with pytest.raises(ValueError, match="min_pa must be between -200 and 200"):
            filters.validate()
        
        # Invalid: above maximum
        filters = PlayerSearchFilters(max_pa=250)
        with pytest.raises(ValueError, match="max_pa must be between -200 and 200"):
            filters.validate()
    
    def test_pagination_validation(self):
        """Test pagination validation"""
        # Valid pagination
        filters = PlayerSearchFilters(limit=50, offset=0)
        filters.validate()  # Should not raise
        
        # Invalid: limit too small
        filters = PlayerSearchFilters(limit=0)
        with pytest.raises(ValueError, match="limit must be between 1 and 200"):
            filters.validate()
        
        # Invalid: limit too large
        filters = PlayerSearchFilters(limit=300)
        with pytest.raises(ValueError, match="limit must be between 1 and 200"):
            filters.validate()
        
        # Invalid: negative offset
        filters = PlayerSearchFilters(offset=-1)
        with pytest.raises(ValueError, match="offset must be non-negative"):
            filters.validate()
        
        # Invalid: excessive offset (DoS prevention)
        filters = PlayerSearchFilters(offset=10001)
        with pytest.raises(ValueError, match="offset cannot exceed 10000"):
            filters.validate()
    
    def test_order_by_validation(self):
        """Test order_by validation"""
        # Valid order_by values
        for order in ["ca", "pa", "age", "name"]:
            filters = PlayerSearchFilters(order_by=order)
            filters.validate()  # Should not raise
        
        # Invalid order_by
        filters = PlayerSearchFilters(order_by="invalid")
        with pytest.raises(ValueError, match="order_by must be one of"):
            filters.validate()
        
        # SQL injection attempt in order_by
        filters = PlayerSearchFilters(order_by="ca; DROP TABLE players")
        with pytest.raises(ValueError, match="order_by must be one of"):
            filters.validate()
    
    def test_relevance_sorting_validation(self):
        """Test relevance sorting requires search_text"""
        # Valid: relevance with search_text
        filters = PlayerSearchFilters(search_text="Messi", order_by="relevance")
        filters.validate()  # Should not raise
        
        # Invalid: relevance without search_text
        filters = PlayerSearchFilters(order_by="relevance")
        with pytest.raises(ValueError, match="order_by='relevance' requires search_text"):
            filters.validate()
    
    def test_combined_filters_sanitization(self):
        """Test sanitization with multiple filters combined"""
        filters = PlayerSearchFilters(
            search_text="  Messi  ",
            position="  ST  ",
            min_age=25,
            max_age=40,
            min_ca=150,
            nationality="  Argentina  ",
            club="  Barcelona  ",
            order_by="relevance"
        )
        
        # Check sanitization
        assert filters.search_text == "Messi"
        assert filters.position == "ST"
        assert filters.nationality == "Argentina"
        assert filters.club == "Barcelona"
        
        # Validate should pass
        filters.validate()
    
    def test_realistic_valid_queries(self):
        """Test realistic valid search queries"""
        valid_scenarios = [
            # Simple name search
            {"search_text": "Lionel Messi", "order_by": "relevance"},
            
            # Position filter
            {"position": "ST", "min_ca": 150, "order_by": "ca"},
            
            # Age range
            {"min_age": 18, "max_age": 25, "order_by": "age"},
            
            # Nationality and club
            {"nationality": "Brazil", "club": "Santos", "order_by": "name"},
            
            # Complex filter
            {
                "search_text": "midfielder",
                "position": "M C",
                "min_age": 20,
                "max_age": 30,
                "min_ca": 140,
                "max_ca": 180,
                "order_by": "relevance"
            },
        ]
        
        for scenario in valid_scenarios:
            filters = PlayerSearchFilters(**scenario)
            filters.validate()  # Should not raise
    
    def test_realistic_attack_scenarios(self):
        """Test realistic attack scenarios are blocked"""
        attack_scenarios = [
            # SQL injection in search
            {"search_text": "'; DROP TABLE players; --"},
            
            # SQL injection in position
            {"position": "ST'; DELETE FROM users; --"},
            
            # XSS in search
            {"search_text": "<script>alert('XSS')</script>"},
            
            # XSS in club
            {"club": "Barcelona<img src=x onerror=alert(1)>"},
            
            # Command injection
            {"search_text": "; rm -rf /"},
            
            # Path traversal
            {"nationality": "../../../etc/passwd"},
        ]
        
        for scenario in attack_scenarios:
            with pytest.raises(ValueError):
                PlayerSearchFilters(**scenario)
    
    def test_length_limits(self):
        """Test that length limits are enforced"""
        # Search text too long
        with pytest.raises(ValueError, match="exceeds maximum length"):
            PlayerSearchFilters(search_text="a" * 201)
        
        # Position too long
        with pytest.raises(ValueError, match="exceeds maximum length"):
            PlayerSearchFilters(position="a" * 101)
        
        # Nationality too long
        with pytest.raises(ValueError, match="exceeds maximum length"):
            PlayerSearchFilters(nationality="a" * 101)
        
        # Club too long
        with pytest.raises(ValueError, match="exceeds maximum length"):
            PlayerSearchFilters(club="a" * 101)
    
    def test_unicode_support(self):
        """Test that Unicode characters are properly supported"""
        # Should work with international characters
        filters = PlayerSearchFilters(
            search_text="Müller",
            nationality="España",
            club="São Paulo"
        )
        
        assert filters.search_text == "Müller"
        assert filters.nationality == "España"
        assert filters.club == "São Paulo"
        
        filters.validate()  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
