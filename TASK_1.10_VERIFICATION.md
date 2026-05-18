# Task 1.10: Logging Configuration - Verification Guide

## Verification Steps

This document provides step-by-step instructions to verify the logging configuration is working correctly.

## 1. Unit Tests Verification

### Run All Logging Tests
```bash
pytest tests/test_logging.py -v
```

**Expected Output**:
```
========================== 21 passed, 1 warning in 0.34s ===========================
```

### Run with Coverage
```bash
pytest tests/test_logging.py --cov=app.core.logging --cov-report=term-missing
```

**Expected Output**:
```
app/core/logging.py    100%
```

## 2. Development Environment Verification

### Start Application in Development Mode
```bash
# Ensure ENVIRONMENT=development in .env.development
python -m uvicorn app.main:app --reload
```

### Expected Console Output (Human-Readable Format):
```
2024-01-15 10:30:45 - root - INFO - Logging configured successfully
2024-01-15 10:30:45 - app.main - INFO - Starting Telegram Football Manager v0.1.0
2024-01-15 10:30:45 - app.main - INFO - Environment: development
2024-01-15 10:30:45 - app.main - INFO - Initializing database connections...
2024-01-15 10:30:45 - app.main - INFO - Initializing Redis cache...
2024-01-15 10:30:45 - app.main - INFO - Application startup complete
```

### Test Request Logging
```bash
# Make a request to the health endpoint
curl http://localhost:8000/health
```

**Expected Console Output**:
```
2024-01-15 10:31:00 - app.main - INFO - Request started: GET /health
2024-01-15 10:31:00 - app.main - INFO - Request completed: GET /health
```

### Test Request ID Tracking
```bash
# Send request with custom request ID
curl -H "X-Request-ID: test-request-123" http://localhost:8000/health
```

**Expected Console Output** (should include request_id in context):
```
2024-01-15 10:31:15 - app.main - INFO - Request started: GET /health
2024-01-15 10:31:15 - app.main - INFO - Request completed: GET /health
```

**Response Headers** (should include):
```
X-Request-ID: test-request-123
X-Process-Time: 0.0123
```

## 3. Production Environment Verification

### Start Application in Production Mode
```bash
# Set environment to production
export ENVIRONMENT=production  # Linux/Mac
# or
set ENVIRONMENT=production     # Windows CMD
# or
$env:ENVIRONMENT="production"  # Windows PowerShell

python -m uvicorn app.main:app
```

### Expected Console Output (JSON Format):
```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "root",
  "message": "Logging configured successfully",
  "module": "logging",
  "function": "setup_logging",
  "line": 225,
  "environment": "production",
  "log_level": "WARNING",
  "handlers": 3
}
```

### Verify Log Files Created
```bash
# Check logs directory
ls -la logs/

# Expected files:
# - tfm_production.log
# - tfm_production_error.log
```

### Verify Log File Content
```bash
# View main log file
cat logs/tfm_production.log

# Expected: JSON formatted logs
tail -f logs/tfm_production.log
```

**Example Log Entry**:
```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "logger": "app.main",
  "message": "Request completed: GET /health",
  "module": "main",
  "function": "request_middleware",
  "line": 115,
  "environment": "production",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "process_time": 0.0123
}
```

### Verify Error Log File
```bash
# Trigger an error (e.g., access non-existent endpoint)
curl http://localhost:8000/nonexistent

# Check error log
cat logs/tfm_production_error.log
```

## 4. Log Rotation Verification

### Test Log Rotation (Manual)
```python
# Create a test script to generate large logs
# test_rotation.py

from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger("test")

# Generate 11MB of logs (exceeds 10MB rotation threshold)
for i in range(500000):
    logger.info(f"Test log message {i} with some extra data to increase size")
```

```bash
# Run the test script
ENVIRONMENT=production python test_rotation.py

# Check for rotated files
ls -la logs/
# Expected: tfm_production.log, tfm_production.log.1, etc.
```

## 5. Request ID Context Verification

### Test Request ID Propagation
```python
# test_request_id.py

from app.core.logging import setup_logging, get_logger, set_request_id, get_request_id, clear_request_id

setup_logging()
logger = get_logger("test")

# Set request ID
request_id = set_request_id("test-123")
print(f"Set request ID: {request_id}")

# Log with request ID
logger.info("This log should include request_id")

# Verify request ID
current_id = get_request_id()
print(f"Current request ID: {current_id}")

# Clear request ID
clear_request_id()
print(f"After clear: {get_request_id()}")
```

```bash
# Run the test
python test_request_id.py
```

**Expected Output**:
```
Set request ID: test-123
Current request ID: test-123
After clear: None
```

## 6. Integration with FastAPI Middleware

### Test Middleware Request Tracking
```bash
# Make multiple requests
for i in {1..5}; do
  curl http://localhost:8000/health
done
```

**Expected Behavior**:
- Each request gets a unique request ID
- Request start and completion are logged
- Process time is measured and logged
- Response headers include X-Request-ID and X-Process-Time

### Test Custom Request ID
```bash
# Send request with custom ID
curl -v -H "X-Request-ID: custom-id-456" http://localhost:8000/health
```

**Expected Response Headers**:
```
X-Request-ID: custom-id-456
X-Process-Time: 0.0123
```

## 7. Third-Party Library Log Levels

### Verify Library Log Levels
```python
# test_library_levels.py

import logging
from app.core.logging import setup_logging

setup_logging()

# Check third-party library log levels
libraries = [
    "uvicorn",
    "uvicorn.access",
    "fastapi",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "redis",
    "celery",
    "telegram",
    "httpx",
    "asyncio"
]

for lib in libraries:
    logger = logging.getLogger(lib)
    print(f"{lib}: {logging.getLevelName(logger.level)}")
```

```bash
python test_library_levels.py
```

**Expected Output**:
```
uvicorn: INFO
uvicorn.access: WARNING
fastapi: INFO
sqlalchemy.engine: WARNING
sqlalchemy.pool: WARNING
redis: WARNING
celery: INFO
telegram: INFO
httpx: WARNING
asyncio: WARNING
```

## 8. Exception Logging Verification

### Test Exception Capture
```python
# test_exception.py

from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger("test")

try:
    raise ValueError("Test exception for logging")
except ValueError:
    logger.error("An error occurred", exc_info=True)
```

```bash
ENVIRONMENT=production python test_exception.py
```

**Expected Log Output** (JSON):
```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "ERROR",
  "logger": "test",
  "message": "An error occurred",
  "module": "test_exception",
  "function": "<module>",
  "line": 10,
  "environment": "production",
  "exception": "Traceback (most recent call last):\n  File \"test_exception.py\", line 8, in <module>\n    raise ValueError(\"Test exception for logging\")\nValueError: Test exception for logging",
  "exception_type": "ValueError"
}
```

## 9. Performance Verification

### Test Logging Performance
```python
# test_performance.py

import time
from app.core.logging import setup_logging, get_logger, set_request_id

setup_logging()
logger = get_logger("test")

# Test without request ID
start = time.time()
for i in range(10000):
    logger.info(f"Test message {i}")
duration_without_id = time.time() - start

# Test with request ID
set_request_id("perf-test")
start = time.time()
for i in range(10000):
    logger.info(f"Test message {i}")
duration_with_id = time.time() - start

print(f"Without request ID: {duration_without_id:.3f}s")
print(f"With request ID: {duration_with_id:.3f}s")
print(f"Overhead: {(duration_with_id - duration_without_id) / duration_without_id * 100:.2f}%")
```

**Expected**: Minimal overhead (< 5%)

## 10. Checklist

- [ ] All 21 unit tests pass
- [ ] Development mode shows human-readable logs
- [ ] Production mode shows JSON formatted logs
- [ ] Log files are created in logs/ directory
- [ ] Log rotation works (files rotate at 10MB)
- [ ] Request ID is tracked across requests
- [ ] Custom request IDs are preserved
- [ ] Response headers include X-Request-ID and X-Process-Time
- [ ] Exception tracebacks are captured
- [ ] Third-party library log levels are configured
- [ ] Error logs are written to separate file
- [ ] Performance overhead is minimal

## Troubleshooting

### Issue: Tests fail with "No module named 'pytest'"
**Solution**: Install test dependencies
```bash
pip install -r requirements.txt
```

### Issue: Log files not created
**Solution**: Check ENVIRONMENT variable is set to "production" or "staging"
```bash
echo $ENVIRONMENT  # Linux/Mac
echo %ENVIRONMENT%  # Windows CMD
$env:ENVIRONMENT   # Windows PowerShell
```

### Issue: Permission denied when creating logs directory
**Solution**: Ensure write permissions
```bash
mkdir -p logs
chmod 755 logs
```

### Issue: Log rotation not working
**Solution**: Check log file size and rotation settings
```bash
ls -lh logs/
# Files should rotate when exceeding 10MB
```

### Issue: Request ID not appearing in logs
**Solution**: Verify middleware is configured in main.py
```python
# Check that request_middleware is registered
# Should be in app.main.py
```

## Conclusion

If all verification steps pass, the logging configuration is working correctly and ready for production use.

For any issues, refer to:
- `app/core/logging.py` - Logging implementation
- `tests/test_logging.py` - Test cases
- `TASK_1.10_SUMMARY.md` - Implementation details
