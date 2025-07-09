#!/usr/bin/env python3
"""
Mock provider example for testing without external dependencies.

This example demonstrates how to:
- Use the mock embedding provider
- Test semantic search functionality without OCI
- Develop and debug search features locally
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from coda.embeddings import MockEmbeddingProvider
from coda.semantic_search import SemanticSearchManager


async def main():
    """Run mock provider example."""
    print("🧪 Mock Provider Example (No OCI Required)")
    print("=" * 40)

    try:
        # Use mock embedding provider
        print("Initializing mock embedding provider...")
        embedding_provider = MockEmbeddingProvider(dimension=768, delay=0.1)  # Simulate API latency
        manager = SemanticSearchManager(embedding_provider=embedding_provider)
        print("✓ Mock manager initialized")

        # Sample documents from different domains
        documents = [
            # Programming languages
            "Python is great for data science and machine learning applications",
            "JavaScript is the primary language for web frontend development",
            "Rust provides memory safety without garbage collection overhead",
            "Go is designed for efficient concurrent programming",
            "TypeScript adds static typing to JavaScript for better tooling",
            # Data science
            "Machine learning models learn patterns from training data",
            "Neural networks consist of interconnected layers of neurons",
            "Data preprocessing is crucial for model performance",
            "Feature engineering transforms raw data into useful features",
            "Cross-validation helps prevent overfitting in ML models",
            # DevOps
            "Docker containers package applications with dependencies",
            "Kubernetes orchestrates containerized applications at scale",
            "CI/CD pipelines automate software delivery processes",
            "Infrastructure as Code manages resources declaratively",
            "Monitoring and logging are essential for production systems",
        ]

        print(f"\nIndexing {len(documents)} documents...")
        doc_ids = await manager.index_content(documents)
        print(f"✓ Indexed {len(doc_ids)} documents")

        # Test various search queries
        test_queries = [
            # Programming queries
            ("web development", "Should find JavaScript/TypeScript docs"),
            ("memory management", "Should find Rust/GC related docs"),
            ("concurrent programming", "Should find Go related docs"),
            # Data science queries
            ("neural networks training", "Should find ML/NN docs"),
            ("prevent overfitting", "Should find cross-validation doc"),
            # DevOps queries
            ("container orchestration", "Should find Kubernetes doc"),
            ("automated deployment", "Should find CI/CD doc"),
        ]

        print("\nTesting semantic searches:")

        for query, expected in test_queries:
            print(f"\nQuery: '{query}'")
            print(f"Expected: {expected}")
            results = await manager.search(query, k=3)

            print("Results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result.score:.3f} | {result.text[:80]}...")

        # Test persistence
        print("\nTesting index persistence...")

        # Save index
        index_path = Path("/tmp/mock_search_index")
        await manager.save_index(index_path)
        print(f"✓ Index saved to {index_path}")

        # Create new manager and load index
        new_manager = SemanticSearchManager(embedding_provider=embedding_provider)
        await new_manager.load_index(index_path)
        print("✓ Index loaded successfully")

        # Verify loaded index works
        results = await new_manager.search("Python programming", k=1)
        print(f"✓ Loaded index search works: Found {len(results)} results")

        print("\n✓ Mock provider example completed successfully!")
        print("\nNote: Mock embeddings are deterministic but not semantically meaningful.")
        print("Use real embedding providers for production use cases.")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
