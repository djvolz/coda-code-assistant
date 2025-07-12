"""
Repository Mapping and Code Analysis Module

This module provides repository structure analysis and code understanding capabilities:
- Repository mapping and structure analysis
- Tree-sitter integration for code parsing
- Multi-language support
- Dependency graph generation

The mapping module focuses on static code analysis and structure understanding,
while the parent intelligence module also includes semantic search capabilities.
"""

from .dependency_graph import DependencyGraph
from .repo_map import RepoMap
from .tree_sitter_analyzer import TreeSitterAnalyzer
from .tree_sitter_query_analyzer import (
    TREE_SITTER_AVAILABLE,
    CodeElement,
    DefinitionKind,
    FileAnalysis,
    TreeSitterQueryAnalyzer,
)

__all__ = [
    "RepoMap",
    "TreeSitterAnalyzer",
    "TreeSitterQueryAnalyzer",
    "DependencyGraph",
    "CodeElement",
    "FileAnalysis",
    "DefinitionKind",
    "TREE_SITTER_AVAILABLE",
]
