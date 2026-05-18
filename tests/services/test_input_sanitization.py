"""
Unit tests for Input Sanitization

Tests the sanitization and validation utilities to ensure they prevent
SQL injection, XSS, and other security issues.

Task 9.7: Add search query validation and sanitization
"""

import pytest
from app.services.input_sanitization import InputSanitizer, SearchQueryValidator


class TestInputSanitizer:
    """Test suite for InputSanitizer class"""
    
    def test_sanitize_search_text_valid(self):
        """Test sanitization of valid search text"""
        # Normal search text
        assert InputSanitizer.sanitize_search_text("Messi") == "Messi"
        assert InputSanitizer.sanitize_search_text("Lionel Messi") == "Lionel Messi"
        assert InputSanitizer.sanitize_search_text("Barcelona") == "Barcelona"
        
        # With extra whitespace
        assert InputSanitizer.sanitize_search_text("  Ronaldo  ") == "Ronaldo"
        assert InputSanitizer.sanitize_search_text("Cristiano   Ronaldo") == "Cristiano Ronaldo"
        
        # With safe punctuation
        assert InputSanitizer.sanitize_search_text("O'Neill") == "O'Neill"
        assert InputSanitizer.sanitize_search_text("Jean-Pierre") == "Jean-Pierre"
        assert InputSanitizer.sanitize_search_text("St. Louis") == "St. Louis"
        assert InputSanitizer.sanitize_search_text("Müller") == "Müller"
        assert InputSanitizer.sanitize_search_text("São Paulo") == "São Paulo"
    
    def test_sanitize_search_text_none_empty(self):
        """Test sanitization of None and empty strings"""
        assert InputSanitizer.sanitize_search_text(None) is None
        assert InputSanitizer.sanitize_search_text("") is None
        assert InputSanitizer.sanitize_search_text("   ") is None
    
    def test_sanitize_search_text_sql_injection(self):
        """Test that SQL injection attempts are blocked"""
        # SQL keywords
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            InputSanitizer.sanitize_search_text("'; DROP TABLE players; --")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            InputSanitizer.sanitize_search_text("1' OR '1'='1")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            InputSanitizer.sanitize_search_text("admin'--")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            InputSanitizer.sanitize_search_text("1; DELETE FROM users")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            InputSanitizer.sanitize_search_text("UNION SELECT * FROM passwords")
        
        with pytest.raises(ValueError, match="dangerous SQL patterns"):
            InputSanitizer.sanitize_search_text("/* comment */ SELECT")
    
    def test_sanitize_search_text_xss(self):
        """Test that XSS attempts are blocked"""
        with pytest.raises(ValueError, match="dangerous HTML/JavaScript patterns"):
            InputSanitizer.sanitize_search_text("<script>alert('XSS')</script>")
        
        with pytest.raises(ValueError, match="dangerous HTML/JavaScript patterns"):
            InputSanitizer.sanitize_search_text("<iframe src='evil.com'></iframe>")
        
        with pytest.raises(ValueError, match="dangerous HTML/JavaScript patterns"):
            InputSanitizer.sanitize_search_text("javascript:alert(1)")
        
        with pytest.raises(ValueError, match="dangerous HTML/JavaScript patterns"):
            InputSanitizer.sanitize_search_text("<img src=x onerror=alert(1)>")
    
    def test_sanitize_search_text_invalid_characters(self):
        """Test that invalid characters are blocked"""
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_search_text("test@example.com")
        
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_search_text("test#hashtag")
        
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_search_text("test$money")
        
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_search_text("test%percent")
        
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_search_text("test&ampersand")
    
    def test_sanitize_search_text_length_limit(self):
        """Test that excessively long search text is rejected"""
        long_text = "a" * 201
        with pytest.raises(ValueError, match="exceeds maximum length"):
            InputSanitizer.sanitize_search_text(long_text)
        
        # Just under the limit should work
        ok_text = "a" * 200
        assert InputSanitizer.sanitize_search_text(ok_text) == ok_text
    
    def test_sanitize_string_filter_valid(self):
        """Test sanitization of valid string filters"""
        assert InputSanitizer.sanitize_string_filter("ST") == "ST"
        assert InputSanitizer.sanitize_string_filter("AM/ST RL") == "AM/ST RL"
        assert InputSanitizer.sanitize_string_filter("Manchester United") == "Manchester United"
        assert InputSanitizer.sanitize_string_filter("Argentina") == "Argentina"
        assert InputSanitizer.sanitize_string_filter("O'Neill") == "O'Neill"
    
    def test_sanitize_string_filter_none_empty(self):
        """Test sanitization of None and empty strings for filters"""
        assert InputSanitizer.sanitize_string_filter(None) is None
        assert InputSanitizer.sanitize_string_filter("") is None
        assert InputSanitizer.sanitize_string_filter("   ") is None
    
    def test_sanitize_string_filter_length_limit(self):
        """Test that excessively long filter values are rejected"""
        long_text = "a" * 101
        with pytest.raises(ValueError, match="exceeds maximum length"):
            InputSanitizer.sanitize_string_filter(long_text)
        
        # Just under the limit should work
        ok_text = "a" * 100
        assert InputSanitizer.sanitize_string_filter(ok_text) == ok_text
    
    def test_sanitize_string_filter_invalid_characters(self):
        """Test that invalid characters in filters are blocked"""
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_string_filter("test@example")
        
        with pytest.raises(ValueError, match="invalid characters"):
            InputSanitizer.sanitize_string_filter("test#tag")
    
    def test_validate_integer_range_valid(self):
        """Test validation of valid integer ranges"""
        # Should not raise
        InputSanitizer.validate_integer_range(25, 15, 50, "age")
        InputSanitizer.validate_integer_range(15, 15, 50, "age")  # Min boundary
        InputSanitizer.validate_integer_range(50, 15, 50, "age")  # Max boundary
        InputSanitizer.validate_integer_range(None, 15, 50, "age")  # None is ok
    
    def test_validate_integer_range_invalid(self):
        """Test validation of invalid integer ranges"""
        # Below minimum
        with pytest.raises(ValueError, match="age must be between 15 and 50"):
            InputSanitizer.validate_integer_range(10, 15, 50, "age")
        
        # Above maximum
        with pytest.raises(ValueError, match="age must be between 15 and 50"):
            InputSanitizer.validate_integer_range(60, 15, 50, "age")
        
        # Wrong type
        with pytest.raises(TypeError, match="age must be an integer"):
            InputSanitizer.validate_integer_range("25", 15, 50, "age")
        
        with pytest.raises(TypeError, match="age must be an integer"):
            InputSanitizer.validate_integer_range(25.5, 15, 50, "age")
    
    def test_validate_order_by_valid(self):
        """Test validation of valid order_by values"""
        allowed = ["ca", "pa", "age", "name", "relevance"]
        
        # Should not raise
        InputSanitizer.validate_order_by("ca", allowed)
        InputSanitizer.validate_order_by("pa", allowed)
        InputSanitizer.validate_order_by("age", allowed)
        InputSanitizer.validate_order_by("name", allowed)
        InputSanitizer.validate_order_by("relevance", allowed)
    
    def test_validate_order_by_invalid(self):
        """Test validation of invalid order_by values"""
        allowed = ["ca", "pa", "age", "name"]
        
        with pytest.raises(ValueError, match="order_by must be one of"):
            InputSanitizer.validate_order_by("invalid", allowed)
        
        # SQL injection attempt
        with pytest.raises(ValueError, match="order_by must be one of"):
            InputSanitizer.validate_order_by("ca; DROP TABLE players", allowed)
        
        with pytest.raises(ValueError, match="order_by must be one of"):
            InputSanitizer.validate_order_by("ca DESC, (SELECT * FROM users)", allowed)


class TestSearchQueryValidator:
    """Test suite for SearchQueryValidator class"""
    
    def test_validate_age_range_valid(self):
        """Test validation of valid age ranges"""
        # Should not raise
        SearchQueryValidator.validate_age_range(18, 30)
        SearchQueryValidator.validate_age_range(18, 18)  # Equal is ok
        SearchQueryValidator.validate_age_range(None, 30)  # One-sided is ok
        SearchQueryValidator.validate_age_range(18, None)  # One-sided is ok
        SearchQueryValidator.validate_age_range(None, None)  # Both None is ok
    
    def test_validate_age_range_invalid(self):
        """Test validation of invalid age ranges"""
        with pytest.raises(ValueError, match="min_age cannot be greater than max_age"):
            SearchQueryValidator.validate_age_range(30, 18)
    
    def test_validate_ca_range_valid(self):
        """Test validation of valid CA ranges"""
        # Should not raise
        SearchQueryValidator.validate_ca_range(100, 200)
        SearchQueryValidator.validate_ca_range(150, 150)
        SearchQueryValidator.validate_ca_range(None, 200)
        SearchQueryValidator.validate_ca_range(100, None)
    
    def test_validate_ca_range_invalid(self):
        """Test validation of invalid CA ranges"""
        with pytest.raises(ValueError, match="min_ca cannot be greater than max_ca"):
            SearchQueryValidator.validate_ca_range(200, 100)
    
    def test_validate_pa_range_valid(self):
        """Test validation of valid PA ranges"""
        # Should not raise
        SearchQueryValidator.validate_pa_range(-200, 200)
        SearchQueryValidator.validate_pa_range(150, 150)
        SearchQueryValidator.validate_pa_range(None, 200)
        SearchQueryValidator.validate_pa_range(-100, None)
    
    def test_validate_pa_range_invalid(self):
        """Test validation of invalid PA ranges"""
        with pytest.raises(ValueError, match="min_pa cannot be greater than max_pa"):
            SearchQueryValidator.validate_pa_range(200, -100)
    
    def test_validate_pagination_valid(self):
        """Test validation of valid pagination parameters"""
        # Should not raise
        SearchQueryValidator.validate_pagination(50, 0)
        SearchQueryValidator.validate_pagination(1, 0)  # Min limit
        SearchQueryValidator.validate_pagination(200, 0)  # Max limit
        SearchQueryValidator.validate_pagination(50, 100)  # Some offset
        SearchQueryValidator.validate_pagination(50, 10000)  # Max offset
    
    def test_validate_pagination_invalid_limit(self):
        """Test validation of invalid limit values"""
        # Limit too small
        with pytest.raises(ValueError, match="limit must be between 1 and 200"):
            SearchQueryValidator.validate_pagination(0, 0)
        
        # Limit too large
        with pytest.raises(ValueError, match="limit must be between 1 and 200"):
            SearchQueryValidator.validate_pagination(201, 0)
        
        # Negative limit
        with pytest.raises(ValueError, match="limit must be between 1 and 200"):
            SearchQueryValidator.validate_pagination(-1, 0)
    
    def test_validate_pagination_invalid_offset(self):
        """Test validation of invalid offset values"""
        # Negative offset
        with pytest.raises(ValueError, match="offset must be non-negative"):
            SearchQueryValidator.validate_pagination(50, -1)
        
        # Excessive offset (DoS prevention)
        with pytest.raises(ValueError, match="offset cannot exceed 10000"):
            SearchQueryValidator.validate_pagination(50, 10001)
    
    def test_validate_relevance_sorting_valid(self):
        """Test validation of valid relevance sorting"""
        # Should not raise
        SearchQueryValidator.validate_relevance_sorting("relevance", "Messi")
        SearchQueryValidator.validate_relevance_sorting("ca", None)  # Other sorts don't need search_text
        SearchQueryValidator.validate_relevance_sorting("pa", None)
    
    def test_validate_relevance_sorting_invalid(self):
        """Test validation of invalid relevance sorting"""
        with pytest.raises(ValueError, match="order_by='relevance' requires search_text"):
            SearchQueryValidator.validate_relevance_sorting("relevance", None)
        
        with pytest.raises(ValueError, match="order_by='relevance' requires search_text"):
            SearchQueryValidator.validate_relevance_sorting("relevance", "")


class TestIntegrationSanitization:
    """Integration tests for sanitization with realistic scenarios"""
    
    def test_realistic_search_queries(self):
        """Test realistic search queries that should work"""
        valid_queries = [
            "Lionel Messi",
            "Cristiano Ronaldo",
            "Manchester United",
            "Real Madrid",
            "São Paulo",
            "Müller",
            "O'Neill",
            "Jean-Pierre",
            "St. Louis",
            "FC Barcelona",
            "Bayern München",
            "Atlético Madrid",
        ]
        
        for query in valid_queries:
            result = InputSanitizer.sanitize_search_text(query)
            assert result is not None
            assert len(result) > 0
    
    def test_realistic_position_filters(self):
        """Test realistic position filters"""
        valid_positions = [
            "ST",
            "AM",
            "D C",
            "GK",
            "AM/ST RL",
            "D/M C",
            "M/AM RL",
        ]
        
        for position in valid_positions:
            result = InputSanitizer.sanitize_string_filter(position)
            assert result is not None
    
    def test_attack_vectors(self):
        """Test common attack vectors are blocked"""
        attack_vectors = [
            # SQL injection
            "'; DROP TABLE players; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM users",
            "UNION SELECT * FROM passwords",
            
            # XSS
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<iframe src='evil.com'></iframe>",
            
            # Command injection
            "; rm -rf /",
            "| cat /etc/passwd",
            
            # Path traversal
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
        ]
        
        for attack in attack_vectors:
            with pytest.raises(ValueError):
                InputSanitizer.sanitize_search_text(attack)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
