"""
Tree-sitter analyzer for code structure analysis.

This module provides tree-sitter based code parsing and analysis capabilities,
using query files (.scm) following aider's approach.
"""

# Re-export the query-based analyzer as the main analyzer
from .tree_sitter_query_analyzer import (
    TREE_SITTER_AVAILABLE,
    CodeElement,
    DefinitionKind,
    FileAnalysis,
)
from .tree_sitter_query_analyzer import (
    TreeSitterQueryAnalyzer as TreeSitterAnalyzer,
)

__all__ = [
    "TreeSitterAnalyzer",
    "CodeElement",
    "FileAnalysis",
    "DefinitionKind",
    "TREE_SITTER_AVAILABLE",
]
