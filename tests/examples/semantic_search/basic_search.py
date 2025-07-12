#!/usr/bin/env python3
"""
Basic semantic search example using OCI embeddings.

This example demonstrates how to:
- Initialize a semantic search manager
- Index text documents
- Perform semantic searches
- Get index statistics
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coda.semantic_search_coda import create_semantic_search_manager


async def main():
    """Run basic semantic search example."""
    print("🔍 Basic Semantic Search Example")
    print("=" * 40)

    try:
        # Initialize using Coda configuration
        print("Initializing semantic search...")
        manager = create_semantic_search_manager(model_id="cohere-embed")
        print("✓ Manager initialized")

        # Sample documents about programming
        documents = [
            "Python is a high-level programming language with dynamic typing",
            "JavaScript is used for web development and runs in browsers",
            "Machine learning algorithms can be implemented in Python using libraries like scikit-learn",
            "React is a popular JavaScript library for building user interfaces",
            "Deep learning models require large amounts of training data",
            "Database optimization involves indexing and query tuning",
            "Cloud computing provides scalable infrastructure for applications",
            "Version control systems like Git help manage code changes",
            "API design follows RESTful principles for web services",
            "Containerization with Docker simplifies application deployment",
        ]

        print(f"\nIndexing {len(documents)} documents...")
        doc_ids = await manager.index_content(documents)
        print(f"✓ Indexed {len(doc_ids)} documents")

        # Perform semantic searches
        queries = [
            "web development frameworks",
            "artificial intelligence and ML",
            "software deployment tools",
            "database performance",
        ]

        print("\nPerforming searches:")

        for query in queries:
            print(f"\nQuery: '{query}'")
            results = await manager.search(query, k=3)

            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result.score:.3f} | {result.text}")

        # Get index statistics
        stats = await manager.get_stats()
        print("\nIndex Statistics:")
        print(f"  • Vector count: {stats['vector_count']}")
        print(f"  • Embedding model: {stats['embedding_model']}")
        print(f"  • Embedding dimension: {stats['embedding_dimension']}")
        print(f"  • Vector store type: {stats['vector_store_type']}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure:")
        print("  • Coda is configured (~/.config/coda/config.toml)")
        print("  • OCI credentials are set up (~/.oci/config)")
        print("  • Dependencies are installed: uv sync --extra embeddings")


if __name__ == "__main__":
    asyncio.run(main())
