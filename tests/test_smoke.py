"""Smoke tests to verify basic functionality.

These tests run quickly and verify the application can start
and perform basic operations. Perfect for CI/CD pipelines.
"""

import subprocess
import sys

import pytest


@pytest.mark.smoke
@pytest.mark.fast
class TestSmoke:
    """Basic smoke tests that run in CI/CD."""

    def test_core_imports(self):
        """Test that core modules can be imported without errors."""
        try:
            import coda
            import coda.cli
            import coda.providers
            import coda.agents
            import coda.session
            
            assert coda is not None
        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")

    def test_providers_import(self):
        """Test that providers can be imported."""
        try:
            from coda.providers.base import BaseProvider
            from coda.providers.mock_provider import MockProvider
            from coda.providers.oci_genai import OCIGenAIProvider

            assert BaseProvider is not None
            assert MockProvider is not None
            assert OCIGenAIProvider is not None
        except ImportError as e:
            pytest.fail(f"Failed to import providers: {e}")

    def test_cli_help(self):
        """Test that CLI help works."""
        result = subprocess.run(
            [sys.executable, "-m", "coda.cli.cli", "--help"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Coda - Multi-provider AI code assistant" in result.stdout

    def test_cli_version(self):
        """Test that CLI version works."""
        result = subprocess.run(
            [sys.executable, "-m", "coda.cli.cli", "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "coda" in result.stdout.lower()

    @pytest.mark.smoke
    def test_mock_provider(self):
        """Test that mock provider works correctly."""
        from coda.providers.mock_provider import MockProvider
        from coda.providers.base import Message, Role
        
        provider = MockProvider()
        messages = [Message(role=Role.USER, content="test")]
        response = provider.chat(messages, "mock-echo")
        assert response.content == "You said: 'test'"

    @pytest.mark.skipif(
        not subprocess.run(["uv", "--version"], capture_output=True).returncode == 0,
        reason="uv not available",
    )
    def test_uv_run_help(self):
        """Test that 'uv run coda --help' works."""
        result = subprocess.run(["uv", "run", "coda", "--help"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Usage: coda" in result.stdout


@pytest.mark.smoke
@pytest.mark.fast
class TestSmokeConfiguration:
    """Smoke tests for configuration system."""
    
    def test_configuration_import(self):
        """Test that configuration module imports correctly."""
        try:
            from coda.configuration import get_config, CodaConfig, ConfigManager
            assert get_config is not None
            assert CodaConfig is not None
            assert ConfigManager is not None
        except ImportError as e:
            pytest.fail(f"Failed to import configuration: {e}")
    
    def test_default_configuration(self):
        """Test that default configuration loads correctly."""
        from coda.configuration import get_config
        
        config = get_config()
        assert config is not None
        assert hasattr(config, 'default_provider')
        assert hasattr(config, 'providers')


@pytest.mark.smoke
@pytest.mark.fast  
class TestSmokeSessions:
    """Smoke tests for session management."""
    
    def test_session_imports(self):
        """Test that session modules import correctly."""
        try:
            from coda.session.manager import SessionManager
            from coda.session.database import SessionDatabase
            from coda.session.context import ContextManager, ContextWindow
            
            assert SessionManager is not None
            assert SessionDatabase is not None
            assert ContextManager is not None
            assert ContextWindow is not None
        except ImportError as e:
            pytest.fail(f"Failed to import session modules: {e}")


@pytest.mark.smoke
@pytest.mark.fast
class TestSmokeTools:
    """Smoke tests for tools system."""
    
    def test_tools_import(self):
        """Test that tools modules import correctly."""
        try:
            from coda.tools.base import BaseTool
            from coda.tools.mcp_server import MCPServer
            
            assert BaseTool is not None
            assert MCPServer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import tools: {e}")


@pytest.mark.smoke
@pytest.mark.fast
class TestSmokeAgents:
    """Smoke tests for agent system."""
    
    def test_agent_imports(self):
        """Test that agent modules import correctly."""
        try:
            from coda.agents.agent import Agent
            from coda.agents.builtin_tools import get_builtin_tools
            from coda.agents.decorators import tool
            
            assert Agent is not None
            assert get_builtin_tools is not None
            assert tool is not None
        except ImportError as e:
            pytest.fail(f"Failed to import agents: {e}")
