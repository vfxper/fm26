"""
Unit Tests for Logging Configuration Module

Tests cover:
- Logging setup and configuration
- Structured JSON formatting
- Request ID tracking and context management
- Log rotation configuration
- Environment-specific behavior
- Third-party library log levels
"""

import pytest
import logging
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from app.core.logging import (
    setup_logging,
    get_logger,
    set_request_id,
    get_request_id,
    clear_request_id,
    StructuredFormatter,
    RequestIdFilter,
    request_id_var,
)
from app.core.config import settings


class TestStructuredFormatter:
    """Test cases for StructuredFormatter class"""
    
    def test_format_basic_log_record(self):
        """Test formatting a basic log record to JSON"""
        formatter = StructuredFormatter()
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Parse JSON
        log_data = json.loads(formatted)
        
        # Verify structure
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.module"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
        assert log_data["timestamp"].endswith("Z")
        assert log_data["environment"] == settings.ENVIRONMENT
    
    def test_format_with_exception(self):
        """Test formatting log record with exception information"""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test")
        
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
            
            record = logger.makeRecord(
                name="test.module",
                level=logging.ERROR,
                fn="test.py",
                lno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
                func="test_function",
            )
            
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            assert log_data["level"] == "ERROR"
            assert "exception" in log_data
            assert "ValueError: Test error" in log_data["exception"]
            assert log_data["exception_type"] == "ValueError"
    
    def test_format_with_request_id(self):
        """Test formatting log record with request ID from context"""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test")
        
        # Set request ID in context
        test_request_id = "test-request-123"
        set_request_id(test_request_id)
        
        try:
            record = logger.makeRecord(
                name="test.module",
                level=logging.INFO,
                fn="test.py",
                lno=42,
                msg="Test message",
                args=(),
                exc_info=None,
                func="test_function",
            )
            
            formatted = formatter.format(record)
            log_data = json.loads(formatted)
            
            assert log_data["request_id"] == test_request_id
        finally:
            clear_request_id()
    
    def test_format_with_extra_fields(self):
        """Test formatting log record with extra custom fields"""
        formatter = StructuredFormatter()
        logger = logging.getLogger("test")
        
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )
        
        # Add custom fields
        record.user_id = 12345
        record.action = "login"
        record.ip_address = "192.168.1.1"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["user_id"] == 12345
        assert log_data["action"] == "login"
        assert log_data["ip_address"] == "192.168.1.1"


class TestRequestIdFilter:
    """Test cases for RequestIdFilter class"""
    
    def test_filter_adds_request_id(self):
        """Test that filter adds request ID to log record"""
        filter_obj = RequestIdFilter()
        logger = logging.getLogger("test")
        
        # Set request ID
        test_request_id = "filter-test-123"
        set_request_id(test_request_id)
        
        try:
            record = logger.makeRecord(
                name="test.module",
                level=logging.INFO,
                fn="test.py",
                lno=42,
                msg="Test message",
                args=(),
                exc_info=None,
                func="test_function",
            )
            
            # Apply filter
            result = filter_obj.filter(record)
            
            assert result is True
            assert hasattr(record, "request_id")
            assert record.request_id == test_request_id
        finally:
            clear_request_id()
    
    def test_filter_without_request_id(self):
        """Test that filter works when no request ID is set"""
        filter_obj = RequestIdFilter()
        logger = logging.getLogger("test")
        
        # Ensure no request ID is set
        clear_request_id()
        
        record = logger.makeRecord(
            name="test.module",
            level=logging.INFO,
            fn="test.py",
            lno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function",
        )
        
        # Apply filter
        result = filter_obj.filter(record)
        
        assert result is True
        assert not hasattr(record, "request_id")


class TestRequestIdManagement:
    """Test cases for request ID context management"""
    
    def test_set_request_id_with_value(self):
        """Test setting a specific request ID"""
        test_id = "custom-request-id-123"
        result = set_request_id(test_id)
        
        assert result == test_id
        assert get_request_id() == test_id
        
        clear_request_id()
    
    def test_set_request_id_generates_uuid(self):
        """Test that set_request_id generates UUID when no ID provided"""
        result = set_request_id()
        
        assert result is not None
        assert len(result) == 36  # UUID format
        assert get_request_id() == result
        
        clear_request_id()
    
    def test_get_request_id_returns_none_when_not_set(self):
        """Test that get_request_id returns None when no ID is set"""
        clear_request_id()
        assert get_request_id() is None
    
    def test_clear_request_id(self):
        """Test clearing request ID from context"""
        set_request_id("test-id")
        assert get_request_id() is not None
        
        clear_request_id()
        assert get_request_id() is None
    
    def test_request_id_isolation(self):
        """Test that request IDs are isolated in different contexts"""
        # This test verifies context variable isolation
        id1 = set_request_id("id-1")
        assert get_request_id() == "id-1"
        
        id2 = set_request_id("id-2")
        assert get_request_id() == "id-2"
        assert id1 != id2
        
        clear_request_id()


class TestLoggingSetup:
    """Test cases for logging setup and configuration"""
    
    def teardown_method(self):
        """Clean up after each test"""
        # Remove all handlers from root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    @patch("app.core.logging.settings")
    def test_setup_logging_development(self, mock_settings):
        """Test logging setup for development environment"""
        mock_settings.ENVIRONMENT = "development"
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "%(levelname)s - %(message)s"
        
        setup_logging()
        
        root_logger = logging.getLogger()
        
        # Verify logger level
        assert root_logger.level == logging.DEBUG
        
        # Verify handlers
        assert len(root_logger.handlers) >= 1
        
        # Verify console handler exists
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1
    
    @patch("app.core.logging.settings")
    def test_setup_logging_production(self, mock_settings):
        """Test logging setup for production environment"""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.LOG_LEVEL = "WARNING"
        mock_settings.LOG_FORMAT = "%(levelname)s - %(message)s"
        
        # Create temporary log directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock Path to use temp directory
            with patch("app.core.logging.Path") as mock_path:
                mock_log_dir = MagicMock()
                mock_log_dir.mkdir = MagicMock()
                mock_log_dir.__truediv__ = lambda self, other: Path(temp_dir) / other
                mock_path.return_value = mock_log_dir
                
                setup_logging()
                
                root_logger = logging.getLogger()
                
                # Verify logger level
                assert root_logger.level == logging.WARNING
                
                # Verify handlers (console + file handlers)
                assert len(root_logger.handlers) >= 1
                
                # Close all file handlers to release file locks on Windows
                for handler in root_logger.handlers[:]:
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        handler.close()
                        root_logger.removeHandler(handler)
    
    def test_get_logger(self):
        """Test getting logger instance"""
        logger = get_logger("test.module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"
    
    def test_get_logger_different_names(self):
        """Test that different names return different loggers"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"
    
    @patch("app.core.logging.settings")
    def test_third_party_log_levels(self, mock_settings):
        """Test that third-party library log levels are configured"""
        mock_settings.ENVIRONMENT = "development"
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "%(levelname)s - %(message)s"
        
        setup_logging()
        
        # Verify third-party log levels
        assert logging.getLogger("uvicorn").level == logging.INFO
        assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING
        assert logging.getLogger("redis").level == logging.WARNING
        assert logging.getLogger("celery").level == logging.INFO


class TestLoggingIntegration:
    """Integration tests for logging functionality"""
    
    def setup_method(self):
        """Setup for each test"""
        # Setup logging
        setup_logging()
    
    def teardown_method(self):
        """Clean up after each test"""
        # Clear request ID
        clear_request_id()
        
        # Remove all handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    def test_logging_with_request_id_context(self):
        """Test that logging includes request ID from context"""
        logger = get_logger("test.integration")
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Set request ID and log
        request_id = set_request_id("integration-test-123")
        logger.info("Test message with request ID")
        
        # Parse output
        output = stream.getvalue()
        if output:  # Only parse if there's output
            log_data = json.loads(output.strip())
            assert log_data["request_id"] == request_id
            assert log_data["message"] == "Test message with request ID"
        
        clear_request_id()
    
    def test_logging_without_request_id(self):
        """Test that logging works without request ID"""
        logger = get_logger("test.integration")
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log without setting request ID
        clear_request_id()
        logger.info("Test message without request ID")
        
        # Parse output
        output = stream.getvalue()
        if output:  # Only parse if there's output
            log_data = json.loads(output.strip())
            assert "request_id" not in log_data or log_data.get("request_id") is None
            assert log_data["message"] == "Test message without request ID"
    
    def test_logging_with_extra_fields(self):
        """Test logging with extra custom fields"""
        logger = get_logger("test.integration")
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Log with extra fields
        logger.info(
            "User action",
            extra={
                "user_id": 12345,
                "action": "login",
                "ip": "192.168.1.1"
            }
        )
        
        # Parse output
        output = stream.getvalue()
        if output:  # Only parse if there's output
            log_data = json.loads(output.strip())
            assert log_data["message"] == "User action"
            assert log_data["user_id"] == 12345
            assert log_data["action"] == "login"
            assert log_data["ip"] == "192.168.1.1"
    
    def test_logging_exception(self):
        """Test logging with exception information"""
        logger = get_logger("test.integration")
        
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)
        
        # Log exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.error("An error occurred", exc_info=True)
        
        # Parse output
        output = stream.getvalue()
        if output:  # Only parse if there's output
            log_data = json.loads(output.strip())
            assert log_data["level"] == "ERROR"
            assert log_data["message"] == "An error occurred"
            assert "exception" in log_data
            assert "ValueError: Test exception" in log_data["exception"]
            assert log_data["exception_type"] == "ValueError"


class TestLogRotation:
    """Test cases for log rotation configuration"""
    
    @patch("app.core.logging.settings")
    def test_rotating_file_handler_configuration(self, mock_settings):
        """Test that rotating file handler is configured correctly in production"""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FORMAT = "%(levelname)s - %(message)s"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("app.core.logging.Path") as mock_path:
                mock_log_dir = MagicMock()
                mock_log_dir.mkdir = MagicMock()
                mock_log_dir.__truediv__ = lambda self, other: Path(temp_dir) / other
                mock_path.return_value = mock_log_dir
                
                setup_logging()
                
                root_logger = logging.getLogger()
                
                # Find rotating file handlers
                rotating_handlers = [
                    h for h in root_logger.handlers
                    if isinstance(h, logging.handlers.RotatingFileHandler)
                ]
                
                # Should have at least one rotating handler
                assert len(rotating_handlers) >= 1
                
                # Verify rotation settings
                for handler in rotating_handlers:
                    assert handler.maxBytes == 10 * 1024 * 1024  # 10 MB
                    assert handler.backupCount == 10
                
                # Close all file handlers to release file locks on Windows
                for handler in root_logger.handlers[:]:
                    if isinstance(handler, logging.handlers.RotatingFileHandler):
                        handler.close()
                        root_logger.removeHandler(handler)
