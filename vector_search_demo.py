#!/usr/bin/env python3
"""
Demo script for Phase 8 Vector Search and Semantic Search functionality.

This script demonstrates how to use the newly implemented vector search features.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from coda.semantic_search_coda import create_semantic_search_manager
from coda.semantic_search import SemanticSearchManager
from coda.embeddings.mock import MockEmbeddingProvider


async def demo_basic_semantic_search():
    """Demonstrate basic semantic search functionality."""
    print("=== Demo: Basic Semantic Search ===")
    
    try:
        # Initialize using Coda configuration
        print("🔄 Initializing semantic search from Coda config...")
        # Try cohere-embed instead of multilingual-e5
        manager = create_semantic_search_manager(model_id="cohere-embed")
        
        print("✅ Semantic search manager initialized")
        
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
            "Containerization with Docker simplifies application deployment"
        ]
        
        print(f"📚 Indexing {len(documents)} documents...")
        
        # Index the documents
        doc_ids = await manager.index_content(documents)
        print(f"✅ Indexed {len(doc_ids)} documents")
        
        # Perform semantic searches
        queries = [
            "web development frameworks",
            "artificial intelligence and ML",
            "software deployment tools",
            "database performance"
        ]
        
        print("\n🔍 Performing semantic searches:")
        
        for query in queries:
            print(f"\n🔎 Query: '{query}'")
            results = await manager.search(query, k=3)
            
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result.score:.3f} | {result.text}")
        
        # Get index statistics
        stats = await manager.get_stats()
        print(f"\n📊 Index Statistics:")
        print(f"  • Vector count: {stats['vector_count']}")
        print(f"  • Embedding model: {stats['embedding_model']}")
        print(f"  • Embedding dimension: {stats['embedding_dimension']}")
        print(f"  • Vector store type: {stats['vector_store_type']}")
        
        print("\n✅ Basic semantic search demo completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Make sure Coda is configured properly (~/.config/coda/config.toml and ~/.oci/config)")


async def demo_code_indexing():
    """Demonstrate code file indexing functionality."""
    print("\n=== Demo: Code File Indexing ===")
    
    try:
        # Initialize using Coda configuration
        print("🔄 Initializing semantic search from Coda config...")
        # Try cohere-embed instead of multilingual-e5
        manager = create_semantic_search_manager(model_id="cohere-embed")
        
        # Find Python files in the project
        python_files = list(Path("coda").glob("**/*.py"))[:5]  # Limit to first 5 files
        
        if not python_files:
            print("❌ No Python files found in coda/ directory")
            return
        
        print(f"📁 Found {len(python_files)} Python files to index")
        
        # Index the code files
        print("🔄 Indexing code files...")
        file_ids = await manager.index_code_files(python_files)
        print(f"✅ Indexed {len(file_ids)} code files")
        
        # Search for specific code patterns
        code_queries = [
            "async function or method",
            "configuration management",
            "error handling",
            "database operations"
        ]
        
        print("\n🔍 Searching code files:")
        
        for query in code_queries:
            print(f"\n🔎 Query: '{query}'")
            results = await manager.search(query, k=2)
            
            for i, result in enumerate(results, 1):
                file_path = result.metadata.get("file_path", "unknown")
                file_name = Path(file_path).name
                print(f"  {i}. {file_name} (Score: {result.score:.3f})")
        
        print("\n✅ Code indexing demo completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def demo_without_oci():
    """Demonstrate using mock/test provider for those without OCI."""
    print("\n=== Demo: Mock Provider (No OCI Required) ===")
    
    try:
        # Use mock embedding provider
        print("🔄 Initializing mock embedding provider...")
        embedding_provider = MockEmbeddingProvider(dimension=768)
        manager = SemanticSearchManager(embedding_provider=embedding_provider)
        
        print("✅ Mock semantic search manager initialized")
        
        # Sample documents
        documents = [
            "Python is great for data science and machine learning",
            "JavaScript is the language of the web",
            "Rust provides memory safety without garbage collection",
            "Go is designed for concurrent programming",
            "TypeScript adds static typing to JavaScript"
        ]
        
        print(f"📚 Indexing {len(documents)} documents with mock embeddings...")
        doc_ids = await manager.index_content(documents)
        print(f"✅ Indexed {len(doc_ids)} documents")
        
        # Search queries
        queries = [
            "web development",
            "memory management",
            "data analysis"
        ]
        
        print("\n🔍 Performing semantic searches with mock provider:")
        
        for query in queries:
            print(f"\n🔎 Query: '{query}'")
            results = await manager.search(query, k=2)
            
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result.score:.3f} | {result.text}")
        
        print("\n✅ Mock provider demo completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def main():
    """Run all demonstrations."""
    print("🚀 Coda Phase 8 Vector Search Demo")
    print("=" * 50)
    
    await demo_basic_semantic_search()
    await demo_code_indexing()
    await demo_without_oci()
    
    print("\n" + "=" * 50)
    print("🎉 All demos completed!")
    print("")
    print("📚 To learn more:")
    print("  • Read docs/phase8_summary.md")
    print("  • Check tests/test_semantic_search.py")
    print("  • Explore coda/semantic_search.py")
    print("")
    print("⚙️  To install dependencies:")
    print("  uv sync --extra embeddings")


if __name__ == "__main__":
    asyncio.run(main())