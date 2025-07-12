"""
Pytest configuration for Coda test suite.
"""

import sys
from pathlib import Path

# Add project root to path so we can import coda modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Basic pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "independence: Tests that verify module independence")
    config.addinivalue_line("markers", "integration: Integration tests that span multiple modules")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
