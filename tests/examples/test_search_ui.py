"""Test script to demonstrate the enhanced search UI."""

import asyncio

from rich.console import Console

from coda.cli.search_display import (
    IndexingProgress,
    SearchResultDisplay,
    create_search_stats_display,
)
from coda.semantic_search import SearchResult


async def main():
    console = Console()
    display = SearchResultDisplay(console)

    # Test 1: Display search results with various scores
    console.print("\n[bold cyan]Test 1: Search Results Display[/bold cyan]")
    console.print("[dim]Searching for 'python programming'...[/dim]\n")

    test_results = [
        SearchResult(
            id="doc-001",
            text="Python is a high-level programming language known for its clear syntax and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            score=0.92,
            metadata={
                "source": "docs/intro.md",
                "type": "documentation",
                "last_modified": "2025-07-07",
            },
        ),
        SearchResult(
            id="code-001",
            text="def calculate_fibonacci(n):\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)\n\n# Example usage\nfor i in range(10):\n    print(f'F({i}) = {calculate_fibonacci(i)}')",
            score=0.85,
            metadata={
                "source": "examples/fibonacci.py",
                "type": "code",
                "language": "python",
                "lines": "10-18",
            },
        ),
        SearchResult(
            id="blog-001",
            text="JavaScript and Python are both popular programming languages but serve different purposes. Python excels in data science, machine learning, and backend development, while JavaScript dominates web development.",
            score=0.73,
            metadata={
                "source": "blog/python-vs-javascript.md",
                "type": "article",
                "author": "Jane Doe",
            },
        ),
        SearchResult(
            id="doc-002",
            text="The Python Package Index (PyPI) is the official repository for Python packages. You can install packages using pip: pip install package_name",
            score=0.65,
            metadata={"source": "docs/package-management.md", "type": "documentation"},
        ),
        SearchResult(
            id="tutorial-001",
            text="Python's asyncio library provides a foundation for writing concurrent code using the async/await syntax. This is particularly useful for I/O-bound and high-level structured network code.",
            score=0.58,
            metadata={
                "source": "tutorials/async-python.md",
                "type": "tutorial",
                "difficulty": "intermediate",
            },
        ),
    ]

    display.display_results(test_results, "python programming")

    # Test 2: No results found
    console.print("\n[bold cyan]Test 2: No Results Found[/bold cyan]")
    console.print("[dim]Searching for 'quantum blockchain AI'...[/dim]\n")
    display.display_results([], "quantum blockchain AI")

    # Test 3: Progress indicator for indexing
    console.print("\n[bold cyan]Test 3: Indexing Progress[/bold cyan]")

    progress = IndexingProgress(console)
    files = [
        "src/main.py",
        "src/utils.py",
        "src/models/user.py",
        "src/models/product.py",
        "tests/test_main.py",
    ]

    with progress.start_indexing(len(files)) as prog:
        for _i, file in enumerate(files):
            await asyncio.sleep(0.5)  # Simulate indexing time
            prog.update(1, f"Indexing {file}")

    console.print("[green]✓ Indexing complete![/green]")

    # Test 4: Index statistics display
    console.print("\n[bold cyan]Test 4: Index Statistics[/bold cyan]")

    stats = {
        "vector_count": 1542,
        "embedding_model": "cohere.embed-multilingual-v3.0",
        "embedding_dimension": 1024,
        "vector_store_type": "FAISS",
        "index_type": "IVF",
        "memory_usage": 6291456,  # 6MB
    }

    create_search_stats_display(stats, console)

    # Test 5: Code search results with syntax highlighting
    console.print("\n[bold cyan]Test 5: Code Search Results[/bold cyan]")
    console.print("[dim]Searching for 'async function'...[/dim]\n")

    code_results = [
        SearchResult(
            id="js-001",
            text="async function fetchUserData(userId) {\n  try {\n    const response = await fetch(`/api/users/${userId}`);\n    const data = await response.json();\n    return data;\n  } catch (error) {\n    console.error('Error fetching user:', error);\n    throw error;\n  }\n}",
            score=0.95,
            metadata={
                "source": "src/api/users.js",
                "type": "code",
                "language": "javascript",
                "lines": "45-54",
            },
        ),
        SearchResult(
            id="py-001",
            text="async def fetch_data(url: str) -> dict:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()",
            score=0.88,
            metadata={
                "source": "utils/http.py",
                "type": "code",
                "language": "python",
                "lines": "12-15",
            },
        ),
    ]

    display.display_results(code_results, "async function", show_metadata=True)


if __name__ == "__main__":
    asyncio.run(main())
