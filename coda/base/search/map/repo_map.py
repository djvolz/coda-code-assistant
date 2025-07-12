"""
Repository mapping implementation for codebase intelligence.

This module provides repository analysis and structure mapping capabilities
similar to aider's approach, using tree-sitter for code parsing and analysis.
"""

import logging
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """Information about a file in the repository."""

    path: str
    size: int
    language: str | None = None
    definitions: list[str] = None
    references: list[str] = None

    def __post_init__(self):
        if self.definitions is None:
            self.definitions = []
        if self.references is None:
            self.references = []


@dataclass
class RepoStats:
    """Statistics about the repository."""

    total_files: int
    total_size: int
    languages: dict[str, int]
    file_extensions: dict[str, int]


class RepoMap:
    """
    Repository mapping and analysis tool.

    Provides functionality to map and analyze code repositories,
    extracting structure, dependencies, and metadata.
    """

    def __init__(self, root_path: str | Path):
        """
        Initialize the repository mapper.

        Args:
            root_path: Path to the root of the repository
        """
        self.root_path = Path(root_path).resolve()
        self.files: dict[str, FileInfo] = {}
        self.stats: RepoStats | None = None

        # Common patterns to ignore
        self.ignore_patterns = {
            ".git",
            ".gitignore",
            ".github",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "node_modules",
            ".npm",
            ".yarn",
            "venv",
            ".venv",
            "env",
            ".env",
            "build",
            "dist",
            ".build",
            ".dist",
            ".DS_Store",
            "Thumbs.db",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "*.so",
            "*.egg-info",
            ".eggs",
            ".coverage",
            ".nyc_output",
            ".cache",
            ".tmp",
            "tmp",
            "logs",
            "*.log",
        }

        # Language mappings based on file extensions
        self.language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".clj": "clojure",
            ".hs": "haskell",
            ".ml": "ocaml",
            ".fs": "fsharp",
            ".elm": "elm",
            ".ex": "elixir",
            ".exs": "elixir",
            ".erl": "erlang",
            ".hrl": "erlang",
            ".lua": "lua",
            ".r": "r",
            ".R": "r",
            ".m": "matlab",
            ".sol": "solidity",
            ".dart": "dart",
            ".vim": "vim",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "zsh",
            ".fish": "fish",
            ".ps1": "powershell",
            ".dockerfile": "dockerfile",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".xml": "xml",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".less": "less",
            ".md": "markdown",
            ".rst": "rst",
            ".tex": "latex",
            ".sql": "sql",
            ".proto": "protobuf",
            ".thrift": "thrift",
            ".graphql": "graphql",
            ".gql": "graphql",
        }

    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            True if the path should be ignored
        """
        str(path)
        name = path.name

        # Check if it's a hidden file (starts with .)
        if name.startswith("."):
            return True

        # Check if any part of the path matches ignore patterns
        path_parts = path.parts
        for pattern in self.ignore_patterns:
            # Check for exact directory name matches
            if pattern in path_parts:
                return True
            # Check for pattern matches in filename
            if pattern.startswith("*") and name.endswith(pattern[1:]):
                return True
            # Check for exact filename match
            if pattern == name:
                return True

        # Check if it's a binary file (simple heuristic)
        if path.is_file():
            try:
                with open(path, "rb") as f:
                    chunk = f.read(1024)
                    if b"\x00" in chunk:
                        return True
            except OSError:
                return True

        return False

    def get_language_from_path(self, path: Path) -> str | None:
        """
        Determine the programming language from file extension.

        Args:
            path: Path to the file

        Returns:
            Language name or None if not recognized
        """
        suffix = path.suffix.lower()
        return self.language_map.get(suffix)

    def scan_repository(self) -> None:
        """
        Scan the repository and collect file information.
        """
        logger.info(f"Scanning repository at {self.root_path}")

        self.files.clear()
        file_count = 0
        total_size = 0
        languages = defaultdict(int)
        extensions = defaultdict(int)

        for root, dirs, files in os.walk(self.root_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]

            for file in files:
                file_path = Path(root) / file

                if self.should_ignore(file_path):
                    continue

                try:
                    stat = file_path.stat()
                    file_size = stat.st_size

                    # Skip empty files and very large files (> 1MB)
                    if file_size == 0 or file_size > 1024 * 1024:
                        continue

                    relative_path = str(file_path.relative_to(self.root_path))
                    language = self.get_language_from_path(file_path)

                    file_info = FileInfo(path=relative_path, size=file_size, language=language)

                    self.files[relative_path] = file_info

                    file_count += 1
                    total_size += file_size

                    if language:
                        languages[language] += 1

                    extension = file_path.suffix.lower()
                    if extension:
                        extensions[extension] += 1

                except OSError as e:
                    logger.warning(f"Error accessing {file_path}: {e}")
                    continue

        self.stats = RepoStats(
            total_files=file_count,
            total_size=total_size,
            languages=dict(languages),
            file_extensions=dict(extensions),
        )

        logger.info(f"Scanned {file_count} files, total size: {total_size} bytes")

    def get_files_by_language(self, language: str) -> list[FileInfo]:
        """
        Get all files for a specific language.

        Args:
            language: Programming language name

        Returns:
            List of FileInfo objects for the language
        """
        return [info for info in self.files.values() if info.language == language]

    def get_repo_structure(self) -> dict[str, list[str]]:
        """
        Get the repository structure organized by directory.

        Returns:
            Dictionary mapping directory paths to lists of files
        """
        structure = defaultdict(list)

        for file_path in self.files.keys():
            dir_path = str(Path(file_path).parent)
            if dir_path == ".":
                dir_path = "root"
            structure[dir_path].append(file_path)

        return dict(structure)

    def get_language_stats(self) -> dict[str, dict[str, int | float]]:
        """
        Get detailed statistics by language.

        Returns:
            Dictionary with language statistics
        """
        if not self.stats:
            return {}

        result = {}
        total_files = self.stats.total_files

        for language, count in self.stats.languages.items():
            files = self.get_files_by_language(language)
            total_size = sum(f.size for f in files)

            result[language] = {
                "file_count": count,
                "total_size": total_size,
                "percentage": (count / total_files) * 100 if total_files > 0 else 0,
                "average_size": total_size / count if count > 0 else 0,
            }

        return result

    def find_files_by_pattern(self, pattern: str) -> list[FileInfo]:
        """
        Find files matching a pattern.

        Args:
            pattern: File pattern to match (supports wildcards)

        Returns:
            List of matching FileInfo objects
        """
        import fnmatch

        matches = []
        for file_info in self.files.values():
            if fnmatch.fnmatch(file_info.path, pattern):
                matches.append(file_info)

        return matches

    def get_summary(self) -> dict[str, int | dict[str, int]]:
        """
        Get a summary of the repository.

        Returns:
            Dictionary with repository summary
        """
        if not self.stats:
            self.scan_repository()

        return {
            "total_files": self.stats.total_files,
            "total_size": self.stats.total_size,
            "languages": self.stats.languages,
            "top_languages": dict(
                sorted(self.stats.languages.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "file_extensions": dict(
                sorted(self.stats.file_extensions.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }

    def is_git_repository(self) -> bool:
        """
        Check if the path is a git repository.

        Returns:
            True if it's a git repository
        """
        return (self.root_path / ".git").exists()

    def get_git_info(self) -> dict[str, str] | None:
        """
        Get git repository information.

        Returns:
            Dictionary with git information or None if not a git repo
        """
        if not self.is_git_repository():
            return None

        try:
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = result.stdout.strip()

            # Get current commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_commit = result.stdout.strip()

            # Get remote URL
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.root_path,
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = result.stdout.strip()

            return {"branch": current_branch, "commit": current_commit, "remote_url": remote_url}

        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
