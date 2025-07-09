#!/usr/bin/env python3
"""
Code file indexing example.

This example demonstrates how to:
- Index source code files
- Search for code patterns semantically
- Extract relevant code snippets
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coda.semantic_search_coda import create_semantic_search_manager


async def main():
    """Run code indexing example."""
    print("📁 Code File Indexing Example")
    print("=" * 40)

    try:
        # Initialize semantic search
        print("Initializing semantic search...")
        manager = create_semantic_search_manager(model_id="cohere-embed")
        print("✓ Manager initialized")

        # Find Python files in the project
        python_files = list(Path("coda").glob("**/*.py"))[:10]  # Limit to first 10 files

        if not python_files:
            print("❌ No Python files found in coda/ directory")
            return

        print(f"\nFound {len(python_files)} Python files")

        # Index the code files
        print("Indexing code files...")
        file_ids = await manager.index_code_files(python_files)
        print(f"✓ Indexed {len(file_ids)} code files")

        # Search for specific code patterns
        code_queries = [
            "async function or method",
            "configuration management",
            "error handling and exceptions",
            "database or storage operations",
            "API endpoints or routes",
        ]

        print("\nSearching code files:")

        for query in code_queries:
            print(f"\nQuery: '{query}'")
            results = await manager.search(query, k=3)

            for i, result in enumerate(results, 1):
                file_path = result.metadata.get("file_path", "unknown")
                file_name = Path(file_path).name
                # Truncate long code snippets
                snippet = result.text[:150] + "..." if len(result.text) > 150 else result.text
                snippet = snippet.replace("\n", " ")
                print(f"  {i}. {file_name} (Score: {result.score:.3f})")
                print(f"     {snippet}")

        print("\n✓ Code indexing completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("  • You're running from the project root directory")
        print("  • Coda configuration is set up")
        print("  • Dependencies are installed")


if __name__ == "__main__":
    asyncio.run(main())
