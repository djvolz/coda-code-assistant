"""
Semantic search tools for AI agents to use.

These tools expose semantic search functionality to AI agents,
allowing them to search indexed content, index new files, and
query code with language-aware formatting.
"""

from pathlib import Path
from typing import Any

from .base import (
    BaseTool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolSchema,
    tool_registry,
)
from .search_manager_mixin import SearchManagerMixin


class SemanticSearchTool(BaseTool, SearchManagerMixin):
    """Search indexed content using semantic similarity."""

    def __init__(self):
        BaseTool.__init__(self)
        SearchManagerMixin.__init__(self)
        # Don't initialize at construction time to avoid import errors

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="semantic_search",
            description="Search indexed content using semantic similarity to find relevant code and documentation",
            category="intelligence",
            parameters={
                "query": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="The search query to find semantically similar content",
                ),
                "top_k": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Number of top results to return",
                    required=False,
                    default=5,
                ),
                "threshold": ToolParameter(
                    type=ToolParameterType.NUMBER,
                    description="Minimum similarity score threshold (0.0 to 1.0)",
                    required=False,
                    default=0.5,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the semantic search."""
        # Initialize manager if needed
        if self._search_manager is None:
            self._initialize_manager()

        query = arguments["query"]
        top_k = int(arguments.get("top_k", 5))
        threshold = float(arguments.get("threshold", 0.5))

        try:
            # Perform search (async call with correct parameter name)
            results = await self._search_manager.search(query, k=top_k)

            # Filter by threshold and format results
            filtered_results = []
            for result in results:
                if result.score >= threshold:
                    filtered_results.append(
                        {
                            "file": result.file_path,
                            "score": round(result.score, 3),
                            "chunk_index": result.chunk_index,
                            "content": result.content[:500],  # Truncate for readability
                            "metadata": result.metadata,
                        }
                    )

            summary = f"Found {len(filtered_results)} results with similarity >= {threshold}"

            return ToolResult(
                success=True,
                result={"results": filtered_results, "query": query, "summary": summary},
                tool="semantic_search",
                metadata={
                    "result_count": len(filtered_results),
                    "query": query,
                    "top_k": top_k,
                    "threshold": threshold,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Search failed: {str(e)}",
                tool="semantic_search",
            )


class IndexContentTool(BaseTool, SearchManagerMixin):
    """Index files or directories for semantic search."""

    def __init__(self):
        BaseTool.__init__(self)
        SearchManagerMixin.__init__(self)
        # Don't initialize at construction time to avoid import errors

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="index_content",
            description="Index files or directories to make them searchable with semantic search",
            category="intelligence",
            parameters={
                "path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Path to file or directory to index",
                ),
                "recursive": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Whether to recursively index directories",
                    required=False,
                    default=True,
                ),
                "file_patterns": ToolParameter(
                    type=ToolParameterType.ARRAY,
                    description="File patterns to include (e.g., ['*.py', '*.js'])",
                    required=False,
                    default=None,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the indexing operation."""
        # Initialize manager if needed
        if self._search_manager is None:
            self._initialize_manager()

        path = arguments["path"]
        recursive = arguments.get("recursive", True)
        file_patterns = arguments.get("file_patterns")

        try:
            target_path = Path(path)
            if not target_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Path not found: {path}",
                    tool="index_content",
                )

            # Determine files to index
            files_to_index = []
            if target_path.is_file():
                files_to_index = [target_path]
            else:
                # Directory - find matching files
                if recursive:
                    if file_patterns:
                        for pattern in file_patterns:
                            files_to_index.extend(target_path.rglob(pattern))
                    else:
                        # Default patterns for code files
                        patterns = [
                            "*.py",
                            "*.js",
                            "*.ts",
                            "*.jsx",
                            "*.tsx",
                            "*.java",
                            "*.go",
                            "*.rs",
                            "*.md",
                        ]
                        for pattern in patterns:
                            files_to_index.extend(target_path.rglob(pattern))
                else:
                    if file_patterns:
                        for pattern in file_patterns:
                            files_to_index.extend(target_path.glob(pattern))
                    else:
                        files_to_index = [f for f in target_path.iterdir() if f.is_file()]

            # Remove duplicates and sort
            files_to_index = sorted(set(files_to_index))

            # Index the files using async method
            try:
                await self._search_manager.index_code_files(files_to_index)
                indexed_count = len(files_to_index)
                failed_files = []
            except Exception as e:
                # If batch indexing fails, provide error details
                indexed_count = 0
                failed_files = [{"error": str(e)}]

            # Build result
            result = {
                "indexed_count": indexed_count,
                "total_files": len(files_to_index),
                "path": str(target_path),
            }
            if failed_files:
                result["failed_files"] = failed_files

            summary = f"Indexed {indexed_count}/{len(files_to_index)} files from {path}"

            return ToolResult(
                success=True,
                result=result,
                tool="index_content",
                metadata={
                    "indexed_count": indexed_count,
                    "failed_count": len(failed_files),
                    "summary": summary,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Indexing failed: {str(e)}",
                tool="index_content",
            )


class CodeSearchTool(BaseTool, SearchManagerMixin):
    """Search code files with language-aware formatting."""

    def __init__(self):
        BaseTool.__init__(self)
        SearchManagerMixin.__init__(self)
        # Don't initialize at construction time to avoid import errors

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="code_search",
            description="Search code files with language-aware syntax highlighting and formatting",
            category="intelligence",
            parameters={
                "query": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="The code pattern or concept to search for",
                ),
                "language": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Programming language filter (e.g., 'python', 'javascript')",
                    required=False,
                    default=None,
                ),
                "top_k": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Number of top results to return",
                    required=False,
                    default=5,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the code search."""
        # Initialize manager if needed
        if self._search_manager is None:
            self._initialize_manager()

        query = arguments["query"]
        language = arguments.get("language")
        top_k = int(arguments.get("top_k", 5))

        try:
            # Perform search (async call with correct parameter name)
            results = await self._search_manager.search(query, k=top_k * 2)  # Get more to filter

            # Filter by language if specified and format results
            filtered_results = []
            for result in results:
                # Check language filter
                if language:
                    file_ext = Path(result.file_path).suffix.lower()
                    lang_map = {
                        "python": [".py"],
                        "javascript": [".js", ".jsx"],
                        "typescript": [".ts", ".tsx"],
                        "java": [".java"],
                        "go": [".go"],
                        "rust": [".rs"],
                    }
                    if language.lower() in lang_map:
                        if file_ext not in lang_map[language.lower()]:
                            continue

                filtered_results.append(
                    {
                        "file": result.file_path,
                        "score": round(result.score, 3),
                        "language": Path(result.file_path).suffix[1:],  # Remove dot
                        "chunk_index": result.chunk_index,
                        "code": result.content,
                        "metadata": result.metadata,
                    }
                )

                if len(filtered_results) >= top_k:
                    break

            summary = f"Found {len(filtered_results)} code results for '{query}'"
            if language:
                summary += f" in {language} files"

            return ToolResult(
                success=True,
                result={"results": filtered_results, "query": query, "summary": summary},
                tool="code_search",
                metadata={
                    "result_count": len(filtered_results),
                    "query": query,
                    "language": language,
                    "top_k": top_k,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Code search failed: {str(e)}",
                tool="code_search",
            )


# Register tools
tool_registry.register(SemanticSearchTool())
tool_registry.register(IndexContentTool())
tool_registry.register(CodeSearchTool())
