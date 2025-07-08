"""Enhanced search result display with rich formatting."""

from pathlib import Path

from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..semantic_search import SearchResult


class SearchHighlighter(RegexHighlighter):
    """Highlight search terms in results."""

    def __init__(self, query_terms: list[str]):
        super().__init__()
        self.query_terms = query_terms
        # Build regex patterns for each term
        for term in query_terms:
            # Case-insensitive matching
            pattern = f"(?i)\\b{term}\\b"
            self.highlights.append(pattern)


class SearchResultDisplay:
    """Enhanced display for semantic search results."""

    def __init__(self, console: Console):
        self.console = console

    def display_results(
        self,
        results: list[SearchResult],
        query: str,
        max_preview_length: int = 300,
        show_metadata: bool = True
    ) -> None:
        """Display search results with rich formatting."""
        if not results:
            self.console.print(
                Panel(
                    "[yellow]No results found[/yellow]\n\n"
                    "[dim]Try different search terms or index more content[/dim]",
                    title="[bold red]Search Results[/bold red]",
                    border_style="red"
                )
            )
            return

        # Extract query terms for highlighting
        query_terms = query.lower().split()
        highlighter = SearchHighlighter(query_terms)

        # Create header
        self.console.print()
        self.console.print(
            Panel(
                f"[bold cyan]Found {len(results)} results for:[/bold cyan] [white]{query}[/white]",
                expand=False,
                border_style="cyan"
            )
        )
        self.console.print()

        # Display each result
        for i, result in enumerate(results, 1):
            self._display_single_result(
                result, i, highlighter, max_preview_length, show_metadata
            )

            # Add separator between results (except after last)
            if i < len(results):
                self.console.print()

    def _display_single_result(
        self,
        result: SearchResult,
        index: int,
        highlighter: SearchHighlighter,
        max_preview_length: int,
        show_metadata: bool
    ) -> None:
        """Display a single search result with formatting."""
        # Create result header with score
        score_color = self._get_score_color(result.score)
        header = f"[bold]#{index}[/bold]  [dim]Score:[/dim] [{score_color}]{result.score:.3f}[/{score_color}]"

        # Add source file if available in metadata
        if result.metadata and "source" in result.metadata:
            source = result.metadata["source"]
            # Make path relative if possible
            try:
                source_path = Path(source)
                if source_path.is_absolute():
                    source = source_path.relative_to(Path.cwd())
            except (ValueError, OSError):
                pass
            header += f"  [dim]Source:[/dim] [blue]{source}[/blue]"

        # Prepare content preview
        content = self._prepare_content_preview(result.text, max_preview_length)

        # Apply highlighting
        highlighted_content = Text(content)
        for term in highlighter.query_terms:
            highlighted_content.highlight_words(term, style="bold yellow")

        # Check if content looks like code
        is_code = self._detect_code(result.text, result.metadata)

        if is_code and result.metadata and "language" in result.metadata:
            # Display as syntax-highlighted code
            lang = result.metadata["language"]
            # Use the full text for syntax highlighting, not the truncated preview
            syntax = Syntax(
                result.text[:max_preview_length],
                lang,
                theme="monokai",
                line_numbers=True,
                word_wrap=True
            )
            code_panel = Panel(
                syntax,
                title=header,
                title_align="left",
                border_style="green",
                padding=(0, 1)
            )
            self.console.print(code_panel)
        else:
            # Display as regular text with highlighting
            content_panel = Panel(
                highlighted_content,
                title=header,
                title_align="left",
                border_style="blue",
                padding=(0, 1)
            )
            self.console.print(content_panel)

        # Display metadata if requested and available
        if show_metadata and result.metadata:
            self._display_metadata(result.metadata)

    def _prepare_content_preview(self, text: str, max_length: int) -> str:
        """Prepare content for preview with smart truncation."""
        # Remove excessive whitespace
        text = " ".join(text.split())

        if len(text) <= max_length:
            return text

        # Try to find a good breaking point
        truncated = text[:max_length]

        # Look for sentence end
        last_period = truncated.rfind(".")
        last_question = truncated.rfind("?")
        last_exclaim = truncated.rfind("!")

        # Find the best breaking point
        best_break = max(last_period, last_question, last_exclaim)

        if best_break > max_length * 0.7:  # If we found a good sentence break
            return truncated[:best_break + 1]

        # Otherwise break at word boundary
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.8:
            return truncated[:last_space] + "..."

        return truncated + "..."

    def _detect_code(self, text: str, metadata: dict | None) -> bool:
        """Detect if content is likely code."""
        if metadata:
            if "type" in metadata and metadata["type"] == "code":
                return True
            if "language" in metadata:
                return True

        # Simple heuristics for code detection
        code_indicators = [
            "def ", "class ", "function ", "const ", "let ", "var ",
            "import ", "from ", "return ", "if ", "for ", "while ",
            "{", "}", "()", "[]", "=>", "==", "!=", "&&", "||"
        ]

        return any(indicator in text for indicator in code_indicators)

    def _get_score_color(self, score: float) -> str:
        """Get color based on similarity score."""
        if score >= 0.9:
            return "bright_green"
        elif score >= 0.7:
            return "green"
        elif score >= 0.5:
            return "yellow"
        else:
            return "red"

    def _display_metadata(self, metadata: dict) -> None:
        """Display metadata in a formatted table."""
        # Filter out internal metadata
        display_metadata = {
            k: v for k, v in metadata.items()
            if not k.startswith("_") and k not in ["source", "language", "type"]
        }

        if not display_metadata:
            return

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            style="dim"
        )
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for key, value in display_metadata.items():
            table.add_row(f"  {key}:", str(value))

        self.console.print(table)


class IndexingProgress:
    """Display progress for indexing operations."""

    def __init__(self, console: Console):
        self.console = console
        self.progress = None

    def start_indexing(self, total_items: int | None = None) -> "IndexingProgressContext":
        """Start an indexing progress display."""
        return IndexingProgressContext(self.console, total_items)


class IndexingProgressContext:
    """Context manager for indexing progress."""

    def __init__(self, console: Console, total_items: int | None = None):
        self.console = console
        self.total_items = total_items
        self.progress = None
        self.task_id = None

    def __enter__(self):
        """Start progress display."""
        if self.total_items:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            )
        else:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console
            )

        self.progress.start()

        if self.total_items:
            self.task_id = self.progress.add_task(
                "[cyan]Indexing content...", total=self.total_items
            )
        else:
            self.task_id = self.progress.add_task("[cyan]Indexing content...")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop progress display."""
        if self.progress:
            self.progress.stop()

    def update(self, advance: int = 1, description: str | None = None):
        """Update progress."""
        if self.progress and self.task_id is not None:
            if description:
                self.progress.update(self.task_id, description=description)
            if self.total_items:
                self.progress.advance(self.task_id, advance)

    def set_total(self, total: int):
        """Set total items after creation."""
        if self.progress and self.task_id is not None:
            self.total_items = total
            self.progress.update(self.task_id, total=total)


def create_search_stats_display(stats: dict, console: Console) -> None:
    """Display search index statistics with rich formatting."""
    # Create stats table
    table = Table(
        title="[bold cyan]Semantic Search Index Statistics[/bold cyan]",
        show_header=True,
        header_style="bold magenta"
    )

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    # Add rows
    table.add_row("Vector Count", f"{stats.get('vector_count', 0):,}")
    table.add_row("Embedding Model", stats.get('embedding_model', 'N/A'))
    table.add_row("Embedding Dimension", str(stats.get('embedding_dimension', 'N/A')))
    table.add_row("Vector Store Type", stats.get('vector_store_type', 'N/A'))

    if 'index_type' in stats:
        table.add_row("Index Type", stats['index_type'])

    if 'memory_usage' in stats:
        mb = stats['memory_usage'] / (1024 * 1024)
        table.add_row("Memory Usage", f"{mb:.2f} MB")

    console.print()
    console.print(table)
    console.print()
