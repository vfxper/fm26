"""
Input Sanitization Utilities for Player Search

This module provides sanitization and validation utilities to prevent
SQL injection, XSS, and other security issues in user inputs.

Task 9.7: Add search query validation and sanitization
"""

import re
from typing import Optional


class InputSanitizer:
    """
    Utility class for sanitizing and validating user inputs.
    
    Provides methods to prevent SQL injection, XSS, and other security issues
    while maintaining usability for legitimate search queries.
    """
    
    # Maximum lengths for various input types
    MAX_SEARCH_TEXT_LENGTH = 200
    MAX_STRING_FILTER_LENGTH = 100
    
    # Dangerous SQL keywords and patterns (case-insensitive)
    SQL_INJECTION_PATTERNS = [
        r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b',
        r'--',  # SQL comment
        r'/\*',  # SQL comment start
        r'\*/',  # SQL comment end
        r';',   # Statement terminator
        r'\bor\b.*=.*',  # OR-based injection
        r'\band\b.*=.*',  # AND-based injection
        r'\'.*\'',  # Single quote strings (potential injection)
        r'\".*\"',  # Double quote strings (potential injection)
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'javascript:',
        r'on\w+\s*=',  # Event handlers like onclick=
        r'<\s*img[^>]*>',
        r'<\s*svg[^>]*>',
    ]
    
    @classmethod
    def sanitize_search_text(cls, search_text: Optional[str]) -> Optional[str]:
        """
        Sanitize search text input to prevent SQL injection and XSS.
        
        This method:
        1. Strips leading/trailing whitespace
        2. Limits length to prevent DoS
        3. Removes dangerous SQL patterns
        4. Removes XSS patterns
        5. Normalizes whitespace
        
        Args:
            search_text: Raw search text from user input
            
        Returns:
            Sanitized search text, or None if input is None/empty
            
        Raises:
            ValueError: If input contains dangerous patterns that cannot be sanitized
            
        Example:
            >>> InputSanitizer.sanitize_search_text("Messi Barcelona")
            'Messi Barcelona'
            >>> InputSanitizer.sanitize_search_text("  Ronaldo  ")
            'Ronaldo'
            >>> InputSanitizer.sanitize_search_text("'; DROP TABLE players; --")
            ValueError: Search text contains potentially dangerous SQL patterns
        """
        if search_text is None:
            return None
        
        # Strip whitespace
        search_text = search_text.strip()
        
        # Return None for empty strings
        if not search_text:
            return None
        
        # Check length limit
        if len(search_text) > cls.MAX_SEARCH_TEXT_LENGTH:
            raise ValueError(
                f"Search text exceeds maximum length of {cls.MAX_SEARCH_TEXT_LENGTH} characters"
            )
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, search_text, re.IGNORECASE):
                raise ValueError(
                    "Search text contains potentially dangerous SQL patterns. "
                    "Please use only alphanumeric characters, spaces, and basic punctuation."
                )
        
        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, search_text, re.IGNORECASE):
                raise ValueError(
                    "Search text contains potentially dangerous HTML/JavaScript patterns. "
                    "Please use only plain text."
                )
        
        # Normalize whitespace (replace multiple spaces with single space)
        search_text = re.sub(r'\s+', ' ', search_text)
        
        # Additional safety: only allow alphanumeric, spaces, and safe punctuation
        # This allows: letters, numbers, spaces, hyphens, apostrophes, periods, commas
        if not re.match(r'^[a-zA-Z0-9\s\-\'.,áéíóúàèìòùâêîôûäëïöüñçÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÑÇ]+$', search_text):
            raise ValueError(
                "Search text contains invalid characters. "
                "Please use only letters, numbers, spaces, and basic punctuation (- ' . ,)"
            )
        
        return search_text
    
    @classmethod
    def sanitize_string_filter(cls, value: Optional[str]) -> Optional[str]:
        """
        Sanitize string filter values (position, nationality, club).
        
        This method:
        1. Strips leading/trailing whitespace
        2. Limits length
        3. Validates against allowed characters
        
        Args:
            value: Raw filter value from user input
            
        Returns:
            Sanitized filter value, or None if input is None/empty
            
        Raises:
            ValueError: If input contains invalid characters
            
        Example:
            >>> InputSanitizer.sanitize_string_filter("ST")
            'ST'
            >>> InputSanitizer.sanitize_string_filter("Manchester United")
            'Manchester United'
        """
        if value is None:
            return None
        
        # Strip whitespace
        value = value.strip()
        
        # Return None for empty strings
        if not value:
            return None
        
        # Check length limit
        if len(value) > cls.MAX_STRING_FILTER_LENGTH:
            raise ValueError(
                f"Filter value exceeds maximum length of {cls.MAX_STRING_FILTER_LENGTH} characters"
            )
        
        # Only allow alphanumeric, spaces, and safe punctuation
        # This allows: letters, numbers, spaces, hyphens, apostrophes, slashes (for positions like "AM/ST")
        if not re.match(r'^[a-zA-Z0-9\s\-\'/áéíóúàèìòùâêîôûäëïöüñçÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÑÇ]+$', value):
            raise ValueError(
                "Filter value contains invalid characters. "
                "Please use only letters, numbers, spaces, and basic punctuation (- ' /)"
            )
        
        return value
    
    @classmethod
    def validate_integer_range(
        cls,
        value: Optional[int],
        min_value: int,
        max_value: int,
        field_name: str
    ) -> None:
        """
        Validate that an integer value is within the allowed range.
        
        Args:
            value: Integer value to validate
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            field_name: Name of the field (for error messages)
            
        Raises:
            ValueError: If value is outside the allowed range
            TypeError: If value is not an integer
            
        Example:
            >>> InputSanitizer.validate_integer_range(25, 15, 50, "age")
            # No error
            >>> InputSanitizer.validate_integer_range(100, 15, 50, "age")
            ValueError: age must be between 15 and 50
        """
        if value is None:
            return
        
        # Type check
        if not isinstance(value, int):
            raise TypeError(f"{field_name} must be an integer")
        
        # Range check
        if value < min_value or value > max_value:
            raise ValueError(f"{field_name} must be between {min_value} and {max_value}")
    
    @classmethod
    def validate_order_by(cls, order_by: str, allowed_values: list) -> None:
        """
        Validate that order_by parameter is one of the allowed values.
        
        This prevents SQL injection through ORDER BY clauses.
        
        Args:
            order_by: Order by value from user input
            allowed_values: List of allowed order_by values
            
        Raises:
            ValueError: If order_by is not in allowed values
            
        Example:
            >>> InputSanitizer.validate_order_by("ca", ["ca", "pa", "age", "name"])
            # No error
            >>> InputSanitizer.validate_order_by("DROP TABLE", ["ca", "pa"])
            ValueError: order_by must be one of: ca, pa
        """
        if order_by not in allowed_values:
            raise ValueError(f"order_by must be one of: {', '.join(allowed_values)}")


class SearchQueryValidator:
    """
    Validator for complete search query parameters.
    
    Provides comprehensive validation for all search parameters including
    cross-field validation (e.g., min_age <= max_age).
    """
    
    @staticmethod
    def validate_age_range(min_age: Optional[int], max_age: Optional[int]) -> None:
        """
        Validate age range parameters.
        
        Args:
            min_age: Minimum age filter
            max_age: Maximum age filter
            
        Raises:
            ValueError: If age range is invalid
        """
        if min_age is not None and max_age is not None:
            if min_age > max_age:
                raise ValueError("min_age cannot be greater than max_age")
    
    @staticmethod
    def validate_ca_range(min_ca: Optional[int], max_ca: Optional[int]) -> None:
        """
        Validate Current Ability range parameters.
        
        Args:
            min_ca: Minimum CA filter
            max_ca: Maximum CA filter
            
        Raises:
            ValueError: If CA range is invalid
        """
        if min_ca is not None and max_ca is not None:
            if min_ca > max_ca:
                raise ValueError("min_ca cannot be greater than max_ca")
    
    @staticmethod
    def validate_pa_range(min_pa: Optional[int], max_pa: Optional[int]) -> None:
        """
        Validate Potential Ability range parameters.
        
        Args:
            min_pa: Minimum PA filter
            max_pa: Maximum PA filter
            
        Raises:
            ValueError: If PA range is invalid
        """
        if min_pa is not None and max_pa is not None:
            if min_pa > max_pa:
                raise ValueError("min_pa cannot be greater than max_pa")
    
    @staticmethod
    def validate_pagination(limit: int, offset: int) -> None:
        """
        Validate pagination parameters.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Raises:
            ValueError: If pagination parameters are invalid
        """
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        
        if offset < 0:
            raise ValueError("offset must be non-negative")
        
        # Prevent excessive offset values (potential DoS)
        if offset > 10000:
            raise ValueError("offset cannot exceed 10000 (use more specific filters instead)")
    
    @staticmethod
    def validate_relevance_sorting(order_by: str, search_text: Optional[str]) -> None:
        """
        Validate that relevance sorting has required search_text.
        
        Args:
            order_by: Sort order
            search_text: Search text query
            
        Raises:
            ValueError: If relevance sorting is used without search_text
        """
        if order_by == "relevance" and not search_text:
            raise ValueError("order_by='relevance' requires search_text to be provided")
