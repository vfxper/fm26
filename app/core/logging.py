"""
Logging Configuration - Structured logging setup with rotation and request tracking

This module provides comprehensive logging configuration for the Telegram Football Manager
application, including:
- Structured JSON logging for production environments
- Human-readable logging for development
- Log rotation to prevent disk space issues
- Request ID tracking for API request tracing
- Configurable log levels per environment
- Third-party library log level management

Usage:
    # At application startup (in main.py)
    from app.core.logging import setup_logging
    setup_logging()
    
    # In any module
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Application started")
    
    # With request context
    logger.info("Processing request", extra={"request_id": request_id})
"""

import logging
import logging.handlers
import sys
import os
from typing import Any, Optional
import json
from datetime import datetime
from pathlib import Path
import uuid
from contextvars import ContextVar

from app.core.config import settings


# Context variable for request ID tracking across async contexts
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging in production environments.
    
    Outputs log records as JSON objects with consistent structure including:
    - timestamp: ISO 8601 formatted UTC timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name (typically module path)
    - message: Log message
    - module: Source module name
    - function: Source function name
    - line: Source line number
    - request_id: Request ID if available (for request tracing)
    - exception: Exception traceback if present
    - Additional custom fields from extra parameter
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            str: JSON formatted log message
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": settings.ENVIRONMENT,
        }
        
        # Add request ID if available from context
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        
        # Add extra fields from record
        # Filter out standard LogRecord attributes to avoid duplication
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
            'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname', 'process',
            'processName', 'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info', 'getMessage', 'extra'
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith('_'):
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


class RequestIdFilter(logging.Filter):
    """
    Logging filter that adds request ID to log records.
    
    This filter retrieves the request ID from the context variable and adds it
    to the log record, enabling request tracing across the application.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add request ID to log record if available.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: Always True (filter doesn't exclude records)
        """
        request_id = request_id_var.get()
        if request_id:
            record.request_id = request_id
        return True


def setup_logging() -> None:
    """
    Configure application logging with environment-specific settings.
    
    This function should be called once at application startup (in main.py).
    It configures:
    - Console handler for stdout
    - File handler with rotation (production/staging only)
    - Appropriate formatters based on environment
    - Log levels for application and third-party libraries
    - Request ID tracking filter
    
    Log Rotation:
    - Production/Staging: Rotates at 10MB, keeps 10 backup files
    - Development: Console only, no file logging
    
    Log Formats:
    - Production/Staging: Structured JSON format
    - Development: Human-readable format with colors
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create request ID filter
    request_filter = RequestIdFilter()
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    console_handler.addFilter(request_filter)
    
    # Use structured logging in production/staging, simple format in development
    if settings.ENVIRONMENT in ["production", "staging"]:
        formatter = StructuredFormatter()
    else:
        # Development: human-readable format
        formatter = logging.Formatter(
            fmt=settings.LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler with rotation for production and staging
    if settings.ENVIRONMENT in ["production", "staging"]:
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure rotating file handler
        # Rotates when file reaches 10MB, keeps 10 backup files
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / f"tfm_{settings.ENVIRONMENT}.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
        file_handler.setFormatter(StructuredFormatter())
        file_handler.addFilter(request_filter)
        root_logger.addHandler(file_handler)
        
        # Add separate error log file for ERROR and CRITICAL levels
        error_file_handler = logging.handlers.RotatingFileHandler(
            filename=log_dir / f"tfm_{settings.ENVIRONMENT}_error.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8"
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(StructuredFormatter())
        error_file_handler.addFilter(request_filter)
        root_logger.addHandler(error_file_handler)
    
    # Set log levels for third-party libraries to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    root_logger.info(
        f"Logging configured successfully",
        extra={
            "log_level": settings.LOG_LEVEL,
            "environment": settings.ENVIRONMENT,
            "handlers": len(root_logger.handlers)
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance for a module.
    
    This is the recommended way to get a logger in application code.
    Typically called with __name__ to create a logger named after the module.
    
    Args:
        name: Logger name (typically __name__ for module-level logging)
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
        logger.error("An error occurred", exc_info=True)
    """
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID in context for request tracing.
    
    This function should be called at the start of each API request to enable
    request tracing across all log messages generated during that request.
    If no request_id is provided, a new UUID will be generated.
    
    Args:
        request_id: Optional request ID. If None, generates a new UUID.
        
    Returns:
        str: The request ID that was set
        
    Example:
        # In FastAPI middleware or dependency
        request_id = set_request_id()
        logger.info("Request started")  # Will include request_id
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.
    
    Returns:
        Optional[str]: Current request ID or None if not set
        
    Example:
        request_id = get_request_id()
        if request_id:
            logger.info(f"Current request: {request_id}")
    """
    return request_id_var.get()


def clear_request_id() -> None:
    """
    Clear request ID from context.
    
    This should be called at the end of request processing to clean up context.
    
    Example:
        # In FastAPI middleware finally block
        clear_request_id()
    """
    request_id_var.set(None)
