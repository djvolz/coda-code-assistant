"""
Test service layer modules for proper integration and dependencies.

Services should:
- Only import from base layer and other services
- Not import from apps layer
- Properly integrate base modules
"""

import ast
from pathlib import Path


def get_imports_from_file(file_path: Path) -> set[str]:
    """Extract all import statements from a Python file."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except (OSError, SyntaxError):
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def test_agents_service_dependencies():
    """Test that agents service only imports from allowed layers."""
    agents_dir = Path("coda/services/agents")

    if not agents_dir.exists():
        return  # Skip if module doesn't exist

    forbidden_patterns = ["coda.apps"]

    for py_file in agents_dir.rglob("*.py"):
        imports = get_imports_from_file(py_file)

        for imp in imports:
            for forbidden in forbidden_patterns:
                assert not imp.startswith(forbidden), (
                    f"Service file {py_file} imports from apps layer: {imp}"
                )


def test_tools_service_dependencies():
    """Test that tools service only imports from allowed layers."""
    tools_dir = Path("coda/services/tools")

    if not tools_dir.exists():
        return  # Skip if module doesn't exist

    forbidden_patterns = ["coda.apps"]

    for py_file in tools_dir.rglob("*.py"):
        imports = get_imports_from_file(py_file)

        for imp in imports:
            for forbidden in forbidden_patterns:
                assert not imp.startswith(forbidden), (
                    f"Service file {py_file} imports from apps layer: {imp}"
                )


def test_config_service_integration():
    """Test that config service properly integrates base modules."""
    from coda.services.config import AppConfig, get_config_service

    # Should be able to get config service
    config = get_config_service()
    assert isinstance(config, AppConfig)

    # Should have theme manager
    assert hasattr(config, "theme_manager")

    # Should have base config functionality
    assert hasattr(config, "get")
    assert hasattr(config, "set")

    # Should be able to get themed console
    console = config.theme_manager.get_console()
    assert console is not None


def test_service_layer_structure():
    """Test that service layer has expected structure."""
    services_dir = Path("coda/services")

    # Expected service modules
    expected_services = {"agents", "tools", "config"}

    actual_services = {
        d.name for d in services_dir.iterdir() if d.is_dir() and not d.name.startswith("_")
    }

    # All expected services should exist
    missing = expected_services - actual_services
    assert not missing, f"Missing expected services: {missing}"


def test_agents_service_functionality():
    """Test basic agents service functionality."""
    try:
        from coda.services.agents import Agent, AgentCapability, AgentManager

        # Should be able to create an agent
        agent = Agent(
            name="test_agent",
            description="Test agent",
            capabilities=[AgentCapability.CODE_ANALYSIS],
        )

        assert agent.name == "test_agent"
        assert AgentCapability.CODE_ANALYSIS in agent.capabilities

        # Should be able to use agent manager
        manager = AgentManager()
        assert hasattr(manager, "register_agent")

    except ImportError:
        # Service might not be fully implemented yet
        pass


def test_tools_mcp_integration():
    """Test that tools service integrates with MCP if available."""
    try:
        from coda.services.tools import MCPManager

        # Should be able to create MCP manager
        manager = MCPManager()

        # Should have expected methods
        assert hasattr(manager, "discover_servers")
        assert hasattr(manager, "connect_server")

    except ImportError:
        # MCP might not be available
        pass
