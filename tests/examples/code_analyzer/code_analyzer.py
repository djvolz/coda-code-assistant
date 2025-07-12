#!/usr/bin/env python3
"""
Code analysis assistant using search and AI.

This example demonstrates:
- Semantic code search
- Context-aware responses
- Code explanation and review
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path so we can import coda modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from coda.base.config import Config
from coda.base.providers import ProviderFactory
from coda.base.search import SearchManager


class CodeAnalyzer:
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path).resolve()

        # Initialize configuration
        self.config = Config()

        # Create provider
        self.factory = ProviderFactory(self.config.to_dict())
        available = self.factory.list_available()

        if not available:
            raise RuntimeError("No providers available")

        self.provider_name = available[0]
        self.provider = self.factory.create(self.provider_name)
        self.model_id = self.provider.list_models()[0].id

        # Initialize search manager
        self.search = SearchManager(self.config.to_dict())
        self._indexed = False

        print("Code Analyzer initialized")
        print(f"Repository: {self.repo_path}")
        print(f"Provider: {self.provider_name}")
        print(f"Model: {self.model_id}\n")

    async def index_repository(self, force: bool = False):
        """Index the repository for searching."""
        if self._indexed and not force:
            print("Repository already indexed. Use force=True to re-index.")
            return

        print(f"Indexing {self.repo_path}...")
        print("This may take a while for large repositories...")

        try:
            file_count = await self.search.index_directory(str(self.repo_path))
            self._indexed = True
            print(f"Indexing complete! Indexed {file_count} files.\n")
        except Exception as e:
            print(f"Indexing failed: {e}\n")
            raise

    async def analyze_code(self, query: str):
        """Analyze code based on a query."""
        if not self._indexed:
            await self.index_repository()

        # Search for relevant code
        print(f"\nSearching for: {query}")

        try:
            results = await self.search.search(query, limit=5)
        except Exception as e:
            print(f"Search failed: {e}")
            return

        if not results:
            print("No relevant code found.")
            return

        print(f"Found {len(results)} relevant code sections\n")

        # Build context from results
        context_parts = []
        for i, result in enumerate(results, 1):
            file_path = result.get("file", "unknown")
            line_num = result.get("line", 0)
            content = result.get("content", "")
            language = result.get("language", "text")

            # Make path relative to repo
            try:
                rel_path = Path(file_path).relative_to(self.repo_path)
            except ValueError:
                rel_path = file_path

            context_parts.append(
                f"### Result {i} - {rel_path}:{line_num}\n```{language}\n{content}\n```"
            )

        context = "\n\n".join(context_parts)

        # Create analysis prompt
        prompt = f"""Analyze the following code related to: "{query}"

{context}

Please provide:
1. A summary of how this code works
2. Any potential issues or improvements
3. Best practices that apply
4. Suggestions for better implementation

Keep your analysis concise and actionable."""

        # Get AI analysis
        print("Analyzing code with AI...\n")

        try:
            response = self.provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_id,
                temperature=0.3,  # Lower temperature for more focused analysis
            )

            print("=== Analysis ===")
            print(response["content"])
            print("\n=== End Analysis ===\n")

            # Show token usage
            if "usage" in response:
                tokens = response["usage"].get("total_tokens", 0)
                print(f"[Tokens used: {tokens}]\n")

        except Exception as e:
            print(f"Analysis failed: {e}\n")

    async def explain_function(self, function_name: str):
        """Explain a specific function."""
        if not self._indexed:
            await self.index_repository()

        # Search for function definition
        search_queries = [
            f"def {function_name}",
            f"function {function_name}",
            f"func {function_name}",
            f"const {function_name} =",
            f"let {function_name} =",
            f"var {function_name} =",
        ]

        results = []
        for query in search_queries:
            try:
                found = await self.search.search(query, limit=3)
                results.extend(found)
            except Exception:
                continue

        if not results:
            print(f"Function '{function_name}' not found.")
            return

        # Get the most relevant result
        func_result = results[0]
        func_code = func_result["content"]
        file_path = func_result.get("file", "unknown")

        # Make path relative
        try:
            rel_path = Path(file_path).relative_to(self.repo_path)
        except ValueError:
            rel_path = file_path

        print(f"\nFound '{function_name}' in {rel_path}\n")

        prompt = f"""Explain this function in detail:

```{func_result.get("language", "text")}
{func_code}
```

Include:
1. Purpose and functionality
2. Parameters and return values
3. Example usage
4. Any side effects or dependencies
5. Potential edge cases or error conditions

Be thorough but clear."""

        try:
            response = self.provider.chat(
                messages=[{"role": "user", "content": prompt}], model=self.model_id, temperature=0.3
            )

            print(f"=== Explanation of {function_name} ===")
            print(response["content"])
            print("\n=== End Explanation ===\n")

        except Exception as e:
            print(f"Explanation failed: {e}\n")

    async def find_similar_code(self, code_snippet: str):
        """Find code similar to a given snippet."""
        if not self._indexed:
            await self.index_repository()

        print(f"\nSearching for code similar to:\n{code_snippet}\n")

        try:
            results = await self.search.search(code_snippet, limit=5)
        except Exception as e:
            print(f"Search failed: {e}")
            return

        if not results:
            print("No similar code found.")
            return

        print(f"=== Found {len(results)} Similar Code Sections ===\n")

        for i, result in enumerate(results, 1):
            file_path = result.get("file", "unknown")
            line_num = result.get("line", 0)
            content = result.get("content", "")
            score = result.get("score", 0.0)

            # Make path relative
            try:
                rel_path = Path(file_path).relative_to(self.repo_path)
            except ValueError:
                rel_path = file_path

            print(f"{i}. {rel_path}:{line_num} (similarity: {score:.2f})")
            print(f"```{result.get('language', '')}")
            print(content)
            print("```\n")

    async def code_review(self, file_path: str):
        """Review a specific file."""
        full_path = self.repo_path / file_path

        if not full_path.exists():
            print(f"File not found: {file_path}")
            return

        try:
            with open(full_path) as f:
                code_content = f.read()
        except Exception as e:
            print(f"Failed to read file: {e}")
            return

        # Determine language from extension
        language = full_path.suffix.lstrip(".") or "text"

        prompt = f"""Please review the following {language} code and provide feedback:

```{language}
{code_content}
```

Focus on:
1. Code quality and readability
2. Potential bugs or issues
3. Security concerns
4. Performance optimizations
5. Best practices and conventions
6. Suggestions for improvement

Provide specific, actionable feedback."""

        print(f"\nReviewing {file_path}...\n")

        try:
            response = self.provider.chat(
                messages=[{"role": "user", "content": prompt}], model=self.model_id, temperature=0.3
            )

            print("=== Code Review ===")
            print(response["content"])
            print("\n=== End Review ===\n")

        except Exception as e:
            print(f"Review failed: {e}\n")


async def main():
    print("=== Code Analyzer Example ===\n")

    # Get repository path
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
    else:
        repo_path = input("Enter repository path (or . for current directory): ").strip()

    if not repo_path:
        repo_path = "."

    repo_path = Path(repo_path).resolve()

    if not repo_path.exists():
        print(f"Path '{repo_path}' does not exist.")
        return 1

    if not repo_path.is_dir():
        print(f"Path '{repo_path}' is not a directory.")
        return 1

    # Create analyzer
    try:
        analyzer = CodeAnalyzer(str(repo_path))
    except Exception as e:
        print(f"Failed to initialize analyzer: {e}")
        return 1

    # Index the repository
    await analyzer.index_repository()

    # Interactive analysis loop
    while True:
        print("\n=== Code Analyzer Menu ===")
        print("1. Analyze code by query")
        print("2. Explain a function")
        print("3. Find similar code")
        print("4. Review a file")
        print("5. Re-index repository")
        print("6. Quit")

        try:
            choice = input("\nChoice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if choice == "1":
            query = input("Enter search query: ").strip()
            if query:
                await analyzer.analyze_code(query)

        elif choice == "2":
            func_name = input("Enter function name: ").strip()
            if func_name:
                await analyzer.explain_function(func_name)

        elif choice == "3":
            print("Enter code snippet (end with '---' on a new line):")
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "---":
                        break
                    lines.append(line)
                except (EOFError, KeyboardInterrupt):
                    break

            snippet = "\n".join(lines)
            if snippet:
                await analyzer.find_similar_code(snippet)

        elif choice == "4":
            file_path = input("Enter file path (relative to repository): ").strip()
            if file_path:
                await analyzer.code_review(file_path)

        elif choice == "5":
            await analyzer.index_repository(force=True)

        elif choice == "6":
            print("Goodbye!")
            break

        else:
            print("Invalid choice")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
