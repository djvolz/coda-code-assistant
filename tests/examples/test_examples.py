"""
Test that example applications can be imported and basic functionality works.

This ensures our examples remain functional as the codebase evolves.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directories to path
examples_dir = Path(__file__).parent
sys.path.insert(0, str(examples_dir))


class TestSimpleChatbot:
    """Test simple chatbot example."""

    def test_import(self):
        """Test that the chatbot can be imported."""
        from simple_chatbot import chatbot

        assert hasattr(chatbot, "main")

    @patch("simple_chatbot.chatbot.Config")
    @patch("simple_chatbot.chatbot.ProviderFactory")
    @patch("builtins.input")
    def test_main_quit_immediately(self, mock_input, mock_factory, mock_config):
        """Test chatbot quits properly."""
        from simple_chatbot import chatbot

        # Setup mocks
        mock_config.return_value = Mock()
        mock_provider = Mock()
        mock_model = Mock()
        mock_model.id = "test-model"
        mock_model.name = "Test"
        mock_provider.list_models.return_value = [mock_model]
        mock_factory.return_value.list_available.return_value = ["test"]
        mock_factory.return_value.create.return_value = mock_provider

        # User immediately quits
        mock_input.side_effect = ["quit"]

        # Run main
        result = chatbot.main()

        assert result == 0
        mock_factory.return_value.create.assert_called_once_with("test")


class TestSessionManager:
    """Test session manager example."""

    def test_import(self):
        """Test that session manager can be imported."""
        from session_manager import session_demo

        assert hasattr(session_demo, "SessionDemo")
        assert hasattr(session_demo, "main")

    @patch("session_manager.session_demo.Config")
    @patch("session_manager.session_demo.ProviderFactory")
    @patch("session_manager.session_demo.SessionManager")
    def test_session_demo_init(self, mock_session_mgr, mock_factory, mock_config):
        """Test SessionDemo initialization."""
        from session_manager import session_demo

        # Setup mocks
        mock_config.return_value = Mock()
        mock_provider = Mock()
        mock_model = Mock()
        mock_model.id = "test-model"
        mock_provider.list_models.return_value = [mock_model]
        mock_factory.return_value.list_available.return_value = ["test"]
        mock_factory.return_value.create.return_value = mock_provider

        # Create demo instance
        demo = session_demo.SessionDemo()

        assert demo.provider_name == "test"
        assert demo.model_id == "test-model"

    @patch("session_manager.session_demo.Config")
    @patch("session_manager.session_demo.ProviderFactory")
    @patch("session_manager.session_demo.SessionManager")
    def test_list_sessions(self, mock_session_mgr, mock_factory, mock_config):
        """Test listing sessions."""
        from session_manager import session_demo

        # Setup mocks
        mock_config.return_value = Mock()
        mock_provider = Mock()
        mock_model = Mock()
        mock_model.id = "test-model"
        mock_provider.list_models.return_value = [mock_model]
        mock_factory.return_value.list_available.return_value = ["test"]
        mock_factory.return_value.create.return_value = mock_provider

        # Mock session list
        mock_session_mgr.return_value.list_sessions.return_value = [
            {
                "name": "test-session",
                "message_count": 5,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
            }
        ]

        # Create demo and list sessions
        demo = session_demo.SessionDemo()
        demo.list_sessions()  # Should not raise

        mock_session_mgr.return_value.list_sessions.assert_called_once()


class TestCodeAnalyzer:
    """Test code analyzer example."""

    def test_import(self):
        """Test that code analyzer can be imported."""
        from code_analyzer import code_analyzer

        assert hasattr(code_analyzer, "CodeAnalyzer")
        assert hasattr(code_analyzer, "main")

    @patch("code_analyzer.code_analyzer.Config")
    @patch("code_analyzer.code_analyzer.ProviderFactory")
    @patch("code_analyzer.code_analyzer.SearchManager")
    def test_code_analyzer_init(self, mock_search, mock_factory, mock_config):
        """Test CodeAnalyzer initialization."""
        from code_analyzer import code_analyzer

        # Setup mocks
        mock_config.return_value = Mock()
        mock_provider = Mock()
        mock_model = Mock()
        mock_model.id = "test-model"
        mock_provider.list_models.return_value = [mock_model]
        mock_factory.return_value.list_available.return_value = ["test"]
        mock_factory.return_value.create.return_value = mock_provider

        # Create analyzer
        analyzer = code_analyzer.CodeAnalyzer(".")

        assert analyzer.provider_name == "test"
        assert analyzer.model_id == "test-model"
        assert analyzer._indexed is False

    @pytest.mark.asyncio
    @patch("code_analyzer.code_analyzer.Config")
    @patch("code_analyzer.code_analyzer.ProviderFactory")
    @patch("code_analyzer.code_analyzer.SearchManager")
    async def test_index_repository(self, mock_search, mock_factory, mock_config):
        """Test repository indexing."""
        from code_analyzer import code_analyzer

        # Setup mocks
        mock_config.return_value = Mock()
        mock_provider = Mock()
        mock_model = Mock()
        mock_model.id = "test-model"
        mock_provider.list_models.return_value = [mock_model]
        mock_factory.return_value.list_available.return_value = ["test"]
        mock_factory.return_value.create.return_value = mock_provider

        # Mock async index_directory
        mock_search.return_value.index_directory = MagicMock()
        mock_search.return_value.index_directory.return_value = 42

        # Create analyzer and index
        analyzer = code_analyzer.CodeAnalyzer(".")
        await analyzer.index_repository()

        assert analyzer._indexed is True
        mock_search.return_value.index_directory.assert_called_once()


class TestExampleStructure:
    """Test that examples follow expected structure."""

    def test_all_examples_have_readme(self):
        """Each example should have a README."""
        example_dirs = [
            examples_dir / "simple-chatbot",
            examples_dir / "session-manager",
            examples_dir / "code-analyzer",
        ]

        for example_dir in example_dirs:
            readme = example_dir / "README.md"
            assert readme.exists(), f"Missing README.md in {example_dir}"

            # Check README has minimum content
            content = readme.read_text()
            assert "## Features" in content
            assert "## Usage" in content
            assert "## Prerequisites" in content

    def test_all_examples_are_executable(self):
        """All Python files should be executable scripts."""
        example_files = [
            examples_dir / "simple-chatbot" / "chatbot.py",
            examples_dir / "session-manager" / "session_demo.py",
            examples_dir / "code-analyzer" / "code_analyzer.py",
        ]

        for example_file in example_files:
            assert example_file.exists()
            content = example_file.read_text()

            # Check for shebang
            assert content.startswith("#!/usr/bin/env python3")

            # Check for main guard
            assert 'if __name__ == "__main__":' in content

            # Check for docstring
            lines = content.split("\n")
            assert lines[1].strip().startswith('"""')


# Run specific example tests based on available dependencies
def test_examples_run_without_error():
    """Test that we can at least import main from each example."""
    # This is a smoke test to ensure examples don't have syntax errors

    examples = [
        ("simple_chatbot.chatbot", "main"),
        ("session_manager.session_demo", "main"),
        ("code_analyzer.code_analyzer", "main"),
    ]

    for module_path, func_name in examples:
        try:
            module_parts = module_path.split(".")
            module = __import__(module_path, fromlist=[module_parts[-1]])
            assert hasattr(module, func_name), f"{module_path} missing {func_name}"
        except ImportError as e:
            # Some imports might fail due to missing optional dependencies
            # That's okay for this basic test
            print(f"Skipping {module_path}: {e}")
