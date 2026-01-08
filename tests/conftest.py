"""
Pytest configuration and fixtures.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests"""
    return tmp_path


@pytest.fixture
def sample_metadata():
    """Provide sample metadata for tests"""
    from services.srt_service import VideoFrameMetadata

    return VideoFrameMetadata(altitude=100.5, longitude=34.5, latitude=31.2, time="12:30:45", date="2025-01-08")


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow")
