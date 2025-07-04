"""Test versioning functionality."""

import re
from datetime import UTC, datetime

import pytest

from coda.__version__ import __version__, get_current_version


@pytest.mark.unit
class TestVersioning:
    """Test version formatting and generation."""

    def test_version_format(self):
        """Test that version follows year.month.day.HHMM format."""
        pattern = r"^\d{4}\.\d{1,2}\.\d{1,2}\.\d{4}$"
        assert re.match(pattern, __version__), f"Version {__version__} doesn't match format"

    def test_version_components(self):
        """Test that version components are valid."""
        parts = __version__.split(".")
        assert len(parts) == 4

        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        time = parts[3]

        # Check ranges
        assert 2025 <= year <= 2100
        assert 1 <= month <= 12
        assert 1 <= day <= 31
        assert len(time) == 4
        assert 0 <= int(time[:2]) <= 23  # hours
        assert 0 <= int(time[2:]) <= 59  # minutes

    def test_get_current_version(self):
        """Test that get_current_version returns valid format."""
        version = get_current_version()
        pattern = r"^\d{4}\.\d{1,2}\.\d{1,2}\.\d{4}$"
        assert re.match(pattern, version)

        # Should be based on current UTC time
        now = datetime.now(UTC)
        assert version.startswith(f"{now.year}.{now.month}.{now.day}.")

    def test_cli_version(self):
        """Test that CLI shows version correctly."""
        import subprocess

        result = subprocess.run(["uv", "run", "coda", "--version"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "coda, version" in result.stdout
        assert __version__ in result.stdout
