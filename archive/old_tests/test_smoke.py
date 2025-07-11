"""Smoke tests to verify basic functionality.

These tests run quickly and verify the application can start
and perform basic operations. Perfect for CI/CD pipelines.
"""

import subprocess
import sys

import pytest


@pytest.mark.unit
class TestSmoke:
    """Basic smoke tests that run in CI/CD."""

    def test_cli_imports(self):
        """Test that the CLI can be imported without errors."""
        try:
            from coda.cli.main import main

            assert main is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CLI: {e}")

    def test_providers_import(self):
        """Test that providers can be imported."""
        try:
            from coda.providers.base import BaseProvider
            from coda.providers.oci_genai import OCIGenAIProvider

            assert BaseProvider is not None
            assert OCIGenAIProvider is not None
        except ImportError as e:
            pytest.fail(f"Failed to import providers: {e}")

    def test_cli_help(self):
        """Test that CLI help works."""
        result = subprocess.run(
            [sys.executable, "-m", "coda.cli.main", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Coda - A multi-provider code assistant" in result.stdout

    def test_cli_version(self):
        """Test that CLI version works."""
        result = subprocess.run(
            [sys.executable, "-m", "coda.cli.main", "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "coda" in result.stdout.lower()

    @pytest.mark.skipif(
        not subprocess.run(["uv", "--version"], capture_output=True).returncode == 0,
        reason="uv not available",
    )
    def test_uv_run_help(self):
        """Test that 'uv run coda --help' works."""
        result = subprocess.run(["uv", "run", "coda", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Usage: coda" in result.stdout
