"""
Pytest configuration and fixtures.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Mock database modules to allow tests to run without DB
sys.modules['db'] = MagicMock()
sys.modules['db.connectToAlarmSystem'] = MagicMock()
sys.modules['db.connectMCtoAlarmSystem'] = MagicMock()
sys.modules['db.insertIntoDB'] = MagicMock()
sys.modules['db.googleAuth'] = MagicMock()
sys.modules['db.getUserAndAlarm'] = MagicMock()


@pytest.fixture
def test_client():
    """FastAPI test client"""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
    """
    Mock database connections for testing without a real database.
    """
    def mock_connect(*args, **kwargs):
        return None
    
    # You can expand this fixture to mock specific database operations
    return mock_connect
