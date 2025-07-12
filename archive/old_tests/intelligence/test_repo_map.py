"""Unit tests for RepoMap functionality."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coda.base.search.map.repo_map import FileInfo, RepoMap, RepoStats


class TestRepoMap:
    """Test suite for RepoMap."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_map = RepoMap(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_file(
        self, relative_path: str, content: str = "# test content\nprint('hello world')"
    ) -> Path:
        """Create a test file in the temp directory."""
        file_path = self.temp_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path

    def test_initialization(self):
        """Test RepoMap initialization."""
        assert self.repo_map.root_path == self.temp_dir.resolve()
        assert isinstance(self.repo_map.files, dict)
        assert self.repo_map.stats is None
        assert len(self.repo_map.ignore_patterns) > 0
        assert len(self.repo_map.language_map) > 0

    def test_language_detection(self):
        """Test language detection from file extensions."""
        assert self.repo_map.get_language_from_path(Path("test.py")) == "python"
        assert self.repo_map.get_language_from_path(Path("test.js")) == "javascript"
        assert self.repo_map.get_language_from_path(Path("test.rs")) == "rust"
        assert self.repo_map.get_language_from_path(Path("test.unknown")) is None

    def test_should_ignore(self):
        """Test file ignore logic."""
        # Should ignore common patterns
        assert self.repo_map.should_ignore(Path(".git"))
        assert self.repo_map.should_ignore(Path("__pycache__"))
        assert self.repo_map.should_ignore(Path("node_modules"))
        assert self.repo_map.should_ignore(Path(".DS_Store"))
        assert self.repo_map.should_ignore(Path(".pytest_cache"))

        # Should not ignore normal files
        assert not self.repo_map.should_ignore(Path("test.py"))
        assert not self.repo_map.should_ignore(Path("README.md"))
        assert not self.repo_map.should_ignore(Path("src/main.rs"))

    def test_scan_repository_basic(self):
        """Test basic repository scanning."""
        # Create test files
        self.create_test_file("main.py", "print('Hello')")
        self.create_test_file("utils.js", "console.log('Hello');")
        self.create_test_file("README.md", "# Project")
        self.create_test_file("src/lib.rs", "fn main() {}")

        # Create ignored files
        self.create_test_file(".git/config", "git config")
        self.create_test_file("__pycache__/module.pyc", "compiled")

        self.repo_map.scan_repository()

        assert len(self.repo_map.files) == 4  # Only non-ignored files
        assert self.repo_map.stats is not None
        assert self.repo_map.stats.total_files == 4

        # Check file info
        assert "main.py" in self.repo_map.files
        assert "utils.js" in self.repo_map.files
        assert "README.md" in self.repo_map.files
        assert "src/lib.rs" in self.repo_map.files

        # Check language detection
        assert self.repo_map.files["main.py"].language == "python"
        assert self.repo_map.files["utils.js"].language == "javascript"
        assert self.repo_map.files["src/lib.rs"].language == "rust"
        assert self.repo_map.files["README.md"].language == "markdown"

    def test_get_files_by_language(self):
        """Test filtering files by language."""
        self.create_test_file("file1.py", "python code")
        self.create_test_file("file2.py", "more python")
        self.create_test_file("file1.js", "javascript code")

        self.repo_map.scan_repository()

        python_files = self.repo_map.get_files_by_language("python")
        js_files = self.repo_map.get_files_by_language("javascript")
        rust_files = self.repo_map.get_files_by_language("rust")

        assert len(python_files) == 2
        assert len(js_files) == 1
        assert len(rust_files) == 0

        assert all(f.language == "python" for f in python_files)
        assert all(f.language == "javascript" for f in js_files)

    def test_get_repo_structure(self):
        """Test getting repository structure."""
        self.create_test_file("main.py", "code")
        self.create_test_file("src/lib.py", "code")
        self.create_test_file("src/utils/helper.py", "code")
        self.create_test_file("tests/test_main.py", "test")

        self.repo_map.scan_repository()
        structure = self.repo_map.get_repo_structure()

        assert "root" in structure
        assert "src" in structure
        assert "src/utils" in structure
        assert "tests" in structure

        assert "main.py" in structure["root"]
        assert "src/lib.py" in structure["src"]
        assert "src/utils/helper.py" in structure["src/utils"]
        assert "tests/test_main.py" in structure["tests"]

    def test_get_language_stats(self):
        """Test language statistics calculation."""
        # Create files with different sizes
        self.create_test_file("small.py", "x = 1")
        self.create_test_file("large.py", "x = 1\n" * 100)
        self.create_test_file("test.js", "console.log('hello');")

        self.repo_map.scan_repository()
        stats = self.repo_map.get_language_stats()

        assert "python" in stats
        assert "javascript" in stats

        python_stats = stats["python"]
        assert python_stats["file_count"] == 2
        assert python_stats["percentage"] > 0
        assert python_stats["average_size"] > 0
        assert python_stats["total_size"] > 0

        js_stats = stats["javascript"]
        assert js_stats["file_count"] == 1

    def test_find_files_by_pattern(self):
        """Test finding files by pattern."""
        self.create_test_file("test_unit.py", "unit test")
        self.create_test_file("test_integration.py", "integration test")
        self.create_test_file("main.py", "main code")
        self.create_test_file("utils.js", "utility")

        self.repo_map.scan_repository()

        # Find test files
        test_files = self.repo_map.find_files_by_pattern("test_*.py")
        assert len(test_files) == 2
        assert all("test_" in f.path for f in test_files)

        # Find all Python files
        py_files = self.repo_map.find_files_by_pattern("*.py")
        assert len(py_files) == 3

        # Find specific file
        main_files = self.repo_map.find_files_by_pattern("main.*")
        assert len(main_files) == 1
        assert main_files[0].path == "main.py"

    def test_get_summary(self):
        """Test getting repository summary."""
        self.create_test_file("main.py", "python code")
        self.create_test_file("utils.py", "more python")
        self.create_test_file("app.js", "javascript")
        self.create_test_file("styles.css", "css code")

        self.repo_map.scan_repository()
        summary = self.repo_map.get_summary()

        assert "total_files" in summary
        assert "total_size" in summary
        assert "languages" in summary
        assert "top_languages" in summary
        assert "file_extensions" in summary

        assert summary["total_files"] == 4
        assert summary["total_size"] > 0
        assert "python" in summary["languages"]
        assert "javascript" in summary["languages"]
        assert summary["languages"]["python"] == 2
        assert summary["languages"]["javascript"] == 1

    def test_empty_repository(self):
        """Test scanning an empty repository."""
        self.repo_map.scan_repository()

        assert len(self.repo_map.files) == 0
        assert self.repo_map.stats.total_files == 0
        assert self.repo_map.stats.total_size == 0
        assert len(self.repo_map.stats.languages) == 0

    def test_binary_file_filtering(self):
        """Test that binary files are filtered out."""
        # Create a binary-like file (with null bytes)
        binary_file = self.temp_dir / "binary.exe"
        binary_file.write_bytes(b"binary\x00content\x00here")

        # Create normal text file
        self.create_test_file("text.py", "print('hello')")

        self.repo_map.scan_repository()

        # Should only have the text file
        assert len(self.repo_map.files) == 1
        assert "text.py" in self.repo_map.files
        assert "binary.exe" not in self.repo_map.files

    def test_large_file_filtering(self):
        """Test that very large files are filtered out."""
        # Create a large file (> 1MB)
        large_content = "x" * (1024 * 1024 + 1)  # Just over 1MB
        self.create_test_file("large.py", large_content)

        # Create normal file
        self.create_test_file("normal.py", "print('hello')")

        self.repo_map.scan_repository()

        # Should only have the normal file
        assert len(self.repo_map.files) == 1
        assert "normal.py" in self.repo_map.files
        assert "large.py" not in self.repo_map.files

    @patch("subprocess.run")
    def test_is_git_repository(self, mock_run):
        """Test git repository detection."""
        # Test non-git directory
        assert not self.repo_map.is_git_repository()

        # Create .git directory
        git_dir = self.temp_dir / ".git"
        git_dir.mkdir()

        # Now it should be detected as git repo
        assert self.repo_map.is_git_repository()

    @patch("subprocess.run")
    def test_get_git_info_success(self, mock_run):
        """Test successful git info extraction."""
        # Create .git directory
        (self.temp_dir / ".git").mkdir()

        # Mock git commands
        mock_run.side_effect = [
            MagicMock(stdout="main\n", returncode=0),  # current branch
            MagicMock(stdout="abc123\n", returncode=0),  # current commit
            MagicMock(stdout="git@github.com:user/repo.git\n", returncode=0),  # remote URL
        ]

        git_info = self.repo_map.get_git_info()

        assert git_info is not None
        assert git_info["branch"] == "main"
        assert git_info["commit"] == "abc123"
        assert git_info["remote_url"] == "git@github.com:user/repo.git"

        # Verify git commands were called
        assert mock_run.call_count == 3

    @patch("subprocess.run")
    def test_get_git_info_failure(self, mock_run):
        """Test git info extraction failure."""
        # Create .git directory
        (self.temp_dir / ".git").mkdir()

        # Mock failed git command
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        git_info = self.repo_map.get_git_info()
        assert git_info is None

    def test_get_git_info_no_git(self):
        """Test git info when not a git repository."""
        git_info = self.repo_map.get_git_info()
        assert git_info is None


@pytest.mark.unit
class TestFileInfo:
    """Test suite for FileInfo dataclass."""

    def test_file_info_creation(self):
        """Test creating FileInfo."""
        file_info = FileInfo(path="src/main.py", size=1024, language="python")

        assert file_info.path == "src/main.py"
        assert file_info.size == 1024
        assert file_info.language == "python"
        assert file_info.definitions == []
        assert file_info.references == []

    def test_file_info_with_definitions(self):
        """Test FileInfo with definitions and references."""
        file_info = FileInfo(
            path="test.py",
            size=500,
            language="python",
            definitions=["func1", "func2"],
            references=["import1", "import2"],
        )

        assert file_info.definitions == ["func1", "func2"]
        assert file_info.references == ["import1", "import2"]


@pytest.mark.unit
class TestRepoStats:
    """Test suite for RepoStats dataclass."""

    def test_repo_stats_creation(self):
        """Test creating RepoStats."""
        stats = RepoStats(
            total_files=10,
            total_size=50000,
            languages={"python": 5, "javascript": 3, "rust": 2},
            file_extensions={".py": 5, ".js": 3, ".rs": 2},
        )

        assert stats.total_files == 10
        assert stats.total_size == 50000
        assert stats.languages["python"] == 5
        assert stats.file_extensions[".py"] == 5
