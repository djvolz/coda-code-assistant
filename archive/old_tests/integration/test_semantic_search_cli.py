"""Integration tests for semantic search CLI commands."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from coda.cli.command_registry import CommandRegistry
from coda.semantic_search import SemanticSearchManager


@pytest.mark.integration
class TestSemanticSearchCLI:
    """Test semantic search CLI integration."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        console = Mock()
        console.print = Mock()
        return console

    @pytest.fixture
    def command_registry(self, mock_console):
        """Create command registry with mock console."""
        return CommandRegistry(mock_console)

    @pytest.mark.asyncio
    async def test_search_semantic_command(self, command_registry, mock_console):
        """Test semantic search command execution."""
        # Mock the semantic search manager creation
        mock_manager = Mock(spec=SemanticSearchManager)
        mock_manager.search = AsyncMock(return_value=[])

        with patch(
            "coda.semantic_search_coda.create_semantic_search_manager", return_value=mock_manager
        ):
            # Run semantic search command
            await command_registry.run_command("search", ["semantic", "test", "query"])

            # Should create manager and perform search
            mock_manager.search.assert_called_once_with("test query", k=5)

            # Should print no results message
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("No results found" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_search_code_command(self, command_registry, mock_console):
        """Test code search command execution."""
        # Mock the semantic search manager
        mock_manager = Mock(spec=SemanticSearchManager)
        mock_manager.search = AsyncMock(return_value=[])

        with patch(
            "coda.semantic_search_coda.create_semantic_search_manager", return_value=mock_manager
        ):
            # Run code search command
            await command_registry.run_command("search", ["code", "async", "function"])

            # Should perform search with code-specific formatting
            mock_manager.search.assert_called_once_with("async function", k=10)

    @pytest.mark.asyncio
    async def test_search_index_command(self, command_registry, mock_console):
        """Test index command execution."""
        # Mock the semantic search manager
        mock_manager = Mock(spec=SemanticSearchManager)
        mock_manager.index_session_messages = AsyncMock(return_value=["id1", "id2"])

        with patch(
            "coda.semantic_search_coda.create_semantic_search_manager", return_value=mock_manager
        ):
            with patch(
                "coda.session.get_session_messages",
                return_value=[{"content": "message 1"}, {"content": "message 2"}],
            ):
                # Run index command
                await command_registry.run_command("search", ["index", "session"])

                # Should index session messages
                mock_manager.index_session_messages.assert_called_once()

                # Should print success message
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Indexed 2 session messages" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_search_status_command(self, command_registry, mock_console):
        """Test status command execution."""
        # Mock the semantic search manager
        mock_manager = Mock(spec=SemanticSearchManager)
        mock_manager.get_stats = AsyncMock(
            return_value={
                "vector_count": 100,
                "embedding_model": "mock-768d",
                "embedding_dimension": 768,
                "vector_store_type": "faiss",
            }
        )

        with patch(
            "coda.semantic_search_coda.create_semantic_search_manager", return_value=mock_manager
        ):
            # Run status command
            await command_registry.run_command("search", ["status"])

            # Should get stats
            mock_manager.get_stats.assert_called_once()

            # Should print stats
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Vector count: 100" in str(call) for call in calls)
            assert any("Embedding model: mock-768d" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_search_command_error_handling(self, command_registry, mock_console):
        """Test error handling in search commands."""
        # Mock manager creation to fail
        with patch(
            "coda.semantic_search_coda.create_semantic_search_manager",
            side_effect=ValueError("No embedding provider configured"),
        ):
            # Run semantic search command
            await command_registry.run_command("search", ["semantic", "test"])

            # Should print error message
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Error initializing semantic search" in str(call) for call in calls)
            assert any("No embedding provider configured" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_search_invalid_subcommand(self, command_registry, mock_console):
        """Test invalid search subcommand."""
        # Run invalid subcommand
        await command_registry.run_command("search", ["invalid"])

        # Should print error
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Unknown subcommand: invalid" in str(call) for call in calls)
        assert any("Available subcommands" in str(call) for call in calls)
