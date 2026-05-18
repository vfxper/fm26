"""
Simple test runner for AI bid generation tests
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the test module
from tests.services.test_transfer_service_ai_bids import *

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([
        "tests/services/test_transfer_service_ai_bids.py",
        "-v",
        "--tb=short"
    ]))
