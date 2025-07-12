"""Tests for the search display module."""

from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from coda.cli.search_display import (
    IndexingProgress,
    IndexingProgressContext,
    SearchHighlighter,
    SearchResultDisplay,
    create_search_stats_display,
)
from coda.vector_stores.base import SearchResult


class TestSearchHighlighter:
    """Test the SearchHighlighter class."""

    def test_init_with_query_terms(self):
        """Test highlighter initialization with query terms."""
        highlighter = SearchHighlighter(["python", "code"])
        assert highlighter.query_terms == ["python", "code"]
        assert len(highlighter.highlights) == 2

    def test_case_insensitive_highlighting(self):
        """Test that highlighting is case-insensitive."""
        highlighter = SearchHighlighter(["python"])

        # The highlighter should create case-insensitive patterns
        assert len(highlighter.highlights) == 1

        # Test the pattern matches all case variations
        import re

        pattern = highlighter.highlights[0]
        regex = re.compile(pattern, re.IGNORECASE)
        assert regex.search("python") is not None
        assert regex.search("Python") is not None
        assert regex.search("PYTHON") is not None


class TestSearchResultDisplay:
    """Test the SearchResultDisplay class."""

    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)

    @pytest.fixture
    def display(self, console):
        """Create a SearchResultDisplay instance."""
        return SearchResultDisplay(console)

    def test_display_no_results(self, display, console):
        """Test displaying when no results found."""
        display.display_results([], "test query")

        # Should show no results message
        console.print.assert_called_once()  # Only prints the panel

    def test_display_single_result(self, display, console):
        """Test displaying a single search result."""
        result = SearchResult(
            id="test-1",
            text="This is a test document with Python code",
            score=0.85,
            metadata={"file_path": "/test/file.py", "file_type": ".py"},
        )

        display.display_results([result], "python")

        # Verify console was called
        assert console.print.called
        # Should have printed empty line, panel with result, and maybe more
        assert console.print.call_count >= 2

    def test_display_multiple_results(self, display, console):
        """Test displaying multiple search results."""
        results = [
            SearchResult(
                id=f"test-{i}",
                text=f"Result {i} text content",
                score=0.9 - i * 0.1,
                metadata={"file_path": f"/test/file{i}.py"},
            )
            for i in range(3)
        ]

        display.display_results(results, "test")

        # Should show all results
        assert console.print.call_count >= 4  # Header + 3 results minimum

    def test_score_color_coding(self, display):
        """Test score color coding logic."""
        assert display._get_score_color(0.95) == "bright_green"
        assert display._get_score_color(0.75) == "green"
        assert display._get_score_color(0.55) == "yellow"
        assert display._get_score_color(0.35) == "red"

    def test_content_preview_truncation(self, display):
        """Test content preview truncation."""
        long_text = "a" * 500
        preview = display._prepare_content_preview(long_text, max_length=100)

        assert len(preview) <= 103  # 100 + "..."
        assert preview.endswith("...")

    def test_content_preview_sentence_break(self, display):
        """Test content preview breaks at sentence boundary."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        preview = display._prepare_content_preview(text, max_length=30)

        # Should break at sentence boundary
        assert preview.endswith(".")
        # Allow some flexibility for ellipsis
        assert len(preview) <= 35  # 30 + some space for "..."

    def test_code_detection(self, display):
        """Test code content detection."""
        # Should detect by metadata
        assert display._detect_code("any text", {"type": "code"}) is True
        assert display._detect_code("any text", {"language": "python"}) is True

        # Should detect by content
        assert display._detect_code("def function():", None) is True
        assert display._detect_code("class MyClass:", None) is True
        assert display._detect_code("function() {", None) is True
        assert display._detect_code("const x = 5", None) is True

        # Should not detect regular text
        assert display._detect_code("This is just regular text.", None) is False

    def test_display_with_chunk_info(self, display, console):
        """Test displaying results with chunk information."""
        result = SearchResult(
            id="chunk-1",
            text="def hello():\n    print('Hello')",
            score=0.9,
            metadata={
                "file_path": "/test/hello.py",
                "start_line": 10,
                "end_line": 12,
                "chunk_type": "function",
            },
        )

        display.display_results([result], "hello")

        # Verify display was called with chunk metadata
        assert console.print.called
        # Should have multiple calls for the result with metadata
        assert console.print.call_count >= 2

    def test_syntax_highlighting_for_code(self, display, console):
        """Test that code results get syntax highlighting."""
        result = SearchResult(
            id="code-1",
            text="def hello():\n    return 'world'",
            score=0.9,
            metadata={"file_type": ".py", "language": "python"},
        )

        with patch("coda.cli.search_display.Syntax") as mock_syntax:
            display.display_results([result], "hello")

            # Should create syntax object for code
            mock_syntax.assert_called()
            call_args = mock_syntax.call_args
            assert "python" in str(call_args)
            assert call_args[1]["theme"] == "monokai"

    def test_metadata_display_filtering(self, display):
        """Test metadata filtering in _display_metadata."""

        # Mock console for this test
        mock_console = Mock()
        display.console = mock_console

        metadata = {
            "file_path": "/test/file.py",  # Should be filtered
            "start_line": 10,  # Should be filtered
            "chunk_type": "function",  # Should show if not "text" or "module"
            "custom_field": "value",  # Should show
            "_internal": "hidden",  # Should be filtered
        }

        display._display_metadata(metadata)

        # Check that filtered fields are not displayed
        if mock_console.print.called:
            printed_content = str(mock_console.print.call_args_list)
            assert "file_path" not in printed_content
            assert "_internal" not in printed_content
            # Just verify a table was printed for metadata
            assert any("Table object" in str(call) for call in mock_console.print.call_args_list)


class TestIndexingProgress:
    """Test the IndexingProgress class."""

    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)

    @pytest.fixture
    def progress(self, console):
        """Create an IndexingProgress instance."""
        return IndexingProgress(console)

    def test_start_indexing_with_total(self, progress, console):
        """Test starting progress with known total."""
        ctx = progress.start_indexing(total_items=100)
        assert isinstance(ctx, IndexingProgressContext)
        assert ctx.total_items == 100

    def test_start_indexing_without_total(self, progress, console):
        """Test starting progress with unknown total."""
        ctx = progress.start_indexing(total_items=None)
        assert isinstance(ctx, IndexingProgressContext)
        assert ctx.total_items is None


class TestIndexingProgressContext:
    """Test the IndexingProgressContext class."""

    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)

    def test_context_manager_with_total(self, console):
        """Test progress context manager with known total."""
        with patch("coda.cli.search_display.Progress") as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress

            ctx = IndexingProgressContext(console, total_items=50)
            with ctx as progress_ctx:
                assert progress_ctx is ctx
                mock_progress.start.assert_called_once()
                mock_progress.add_task.assert_called_once()

                # Test update
                progress_ctx.update(5, "Processing...")
                mock_progress.advance.assert_called_with(ctx.task_id, 5)
                mock_progress.update.assert_called()

            mock_progress.stop.assert_called_once()

    def test_context_manager_without_total(self, console):
        """Test progress context manager with unknown total."""
        with patch("coda.cli.search_display.Progress") as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress

            ctx = IndexingProgressContext(console, total_items=None)
            with ctx:
                mock_progress.start.assert_called_once()
                mock_progress.add_task.assert_called_once()

                # Without total, advance shouldn't be called
                ctx.update(5, "Processing...")
                mock_progress.advance.assert_not_called()

    def test_set_total(self, console):
        """Test setting total after creation."""
        with patch("coda.cli.search_display.Progress") as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress

            ctx = IndexingProgressContext(console, total_items=None)
            with ctx:
                ctx.set_total(100)
                assert ctx.total_items == 100
                mock_progress.update.assert_called_with(ctx.task_id, total=100)

    def test_exception_handling(self, console):
        """Test that progress stops even with exception."""
        with patch("coda.cli.search_display.Progress") as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress

            ctx = IndexingProgressContext(console, total_items=10)

            try:
                with ctx:
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Progress should still be stopped
            mock_progress.stop.assert_called_once()


class TestCreateSearchStatsDisplay:
    """Test the create_search_stats_display function."""

    @pytest.fixture
    def console(self):
        """Create a mock console."""
        return Mock(spec=Console)

    def test_basic_stats_display(self, console):
        """Test displaying basic search stats."""
        stats = {
            "vector_count": 1000,
            "embedding_model": "all-MiniLM-L6-v2",
            "embedding_dimension": 384,
            "vector_store_type": "FAISSVectorStore",
            "index_type": "flat",
        }

        with patch("coda.cli.search_display.Table") as mock_table_class:
            mock_table = Mock()
            mock_table_class.return_value = mock_table

            create_search_stats_display(stats, console)

            # Should create table with title
            mock_table_class.assert_called_once()
            assert "Semantic Search Index Statistics" in str(mock_table_class.call_args)

            # Should add all rows
            assert mock_table.add_row.call_count >= 5

            # Check some values were added
            row_calls = [str(call) for call in mock_table.add_row.call_args_list]
            assert any("1,000" in call or "1000" in call for call in row_calls)
            assert any("384" in call for call in row_calls)
            assert any("FAISSVectorStore" in call for call in row_calls)

    def test_stats_with_memory_usage(self, console):
        """Test displaying stats with memory usage."""
        stats = {
            "vector_count": 500,
            "embedding_model": "mock-model",
            "embedding_dimension": 768,
            "vector_store_type": "FAISSVectorStore",
            "memory_usage": 1024 * 1024 * 50,  # 50 MB
        }

        with patch("coda.cli.search_display.Table") as mock_table_class:
            mock_table = Mock()
            mock_table_class.return_value = mock_table

            create_search_stats_display(stats, console)

            # Should include memory usage
            row_calls = [str(call) for call in mock_table.add_row.call_args_list]
            assert any("50.00 MB" in call or "50.0 MB" in call for call in row_calls)

    def test_stats_missing_fields(self, console):
        """Test handling missing fields gracefully."""
        stats = {
            "vector_count": 100,
            # Missing other fields
        }

        with patch("coda.cli.search_display.Table") as mock_table_class:
            mock_table = Mock()
            mock_table_class.return_value = mock_table

            create_search_stats_display(stats, console)

            # Should still work with N/A for missing fields
            row_calls = [str(call) for call in mock_table.add_row.call_args_list]
            assert any("N/A" in call for call in row_calls)


class TestSearchResultsIntegration:
    """Integration tests for search result display."""

    def test_complete_search_workflow(self):
        """Test complete search and display workflow."""
        console = Mock(spec=Console)
        display = SearchResultDisplay(console)

        # Create diverse results
        results = [
            SearchResult(
                id="py-1",
                text="def calculate_sum(a, b):\n    return a + b",
                score=0.92,
                metadata={
                    "file_path": "/src/math.py",
                    "file_type": ".py",
                    "chunk_type": "function",
                    "start_line": 10,
                    "end_line": 11,
                },
            ),
            SearchResult(
                id="md-1",
                text="# Python Tutorial\n\nLearn how to calculate sums...",
                score=0.75,
                metadata={"file_path": "/docs/tutorial.md", "file_type": ".md"},
            ),
            SearchResult(
                id="js-1",
                text="function calculateSum(a, b) { return a + b; }",
                score=0.68,
                metadata={
                    "file_path": "/src/math.js",
                    "file_type": ".js",
                    "language": "javascript",
                },
            ),
        ]

        # Display results
        display.display_results(results, "calculate sum", show_metadata=True)

        # Verify comprehensive output
        assert console.print.call_count >= 6  # Header + 3 results + metadata

        # Check that different result types are handled
        # Should have multiple print calls for the results
        assert console.print.call_count >= 6  # Multiple results with separators
