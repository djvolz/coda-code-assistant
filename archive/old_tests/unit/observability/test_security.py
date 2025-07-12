"""Unit tests for security utilities."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.observability.security import (
    PathTraversalError,
    PathValidator,
    SecureFileOperations,
    SecurityError,
)


class InvalidFilenameError(SecurityError):
    """Invalid filename error used in tests."""

    pass


class TestPathValidator:
    """Test the PathValidator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_validate_export_path_valid(self, temp_dir):
        """Test validation of valid export paths."""
        valid_paths = [
            temp_dir / "file.json",
            temp_dir / "subdir" / "file.txt",
            temp_dir / "deep" / "nested" / "path" / "file.csv",
        ]

        for path in valid_paths:
            validated = PathValidator.validate_export_path(path, temp_dir)
            assert validated.is_absolute()
            assert str(validated).startswith(str(temp_dir))

    def test_validate_export_path_traversal(self, temp_dir):
        """Test detection of path traversal attempts."""
        invalid_paths = [
            temp_dir / ".." / "etc" / "passwd",
            temp_dir / "subdir" / ".." / ".." / "etc" / "passwd",
            temp_dir / "." / ".." / "sensitive",
        ]

        for path in invalid_paths:
            with pytest.raises(PathTraversalError):
                PathValidator.validate_export_path(path, temp_dir)

    def test_validate_export_path_outside_base(self, temp_dir):
        """Test rejection of paths outside base directory."""
        other_dir = Path("/tmp/other")

        with pytest.raises(PathTraversalError):
            PathValidator.validate_export_path(other_dir / "file.json", temp_dir)

    def test_validate_export_path_relative(self, temp_dir):
        """Test handling of relative paths."""
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            relative_path = Path("subdir/file.json")
            validated = PathValidator.validate_export_path(relative_path, temp_dir)

            assert validated.is_absolute()
            assert str(validated).startswith(str(temp_dir))
        finally:
            os.chdir(original_cwd)

    def test_validate_filename_valid(self):
        """Test validation of valid filenames."""
        valid_filenames = [
            ("report.json", [".json"]),
            ("data.csv", [".csv", ".txt"]),
            ("export_2023_10_01.json", [".json"]),
            ("my-file.txt", [".txt"]),
            ("file_with_numbers_123.json", [".json"]),
        ]

        for filename, allowed_extensions in valid_filenames:
            # Should not raise
            PathValidator.validate_filename(filename, allowed_extensions)

    def test_validate_filename_invalid_extension(self):
        """Test rejection of invalid file extensions."""
        with pytest.raises(InvalidFilenameError):
            PathValidator.validate_filename("file.exe", [".json", ".txt"])

        with pytest.raises(InvalidFilenameError):
            PathValidator.validate_filename("file.sh", [".json"])

    def test_validate_filename_invalid_characters(self):
        """Test rejection of filenames with invalid characters."""
        invalid_filenames = [
            "../etc/passwd",
            "file/../secret.json",
            "file\x00.json",
            "/etc/passwd",
            "\\windows\\system32\\file.json",
            "file:with:colons.json",
            "file|with|pipes.json",
        ]

        for filename in invalid_filenames:
            with pytest.raises(InvalidFilenameError):
                PathValidator.validate_filename(filename, [".json"])

    def test_validate_filename_empty(self):
        """Test rejection of empty filenames."""
        with pytest.raises(InvalidFilenameError):
            PathValidator.validate_filename("", [".json"])

        with pytest.raises(InvalidFilenameError):
            PathValidator.validate_filename(".json", [".json"])

    def test_validate_filename_too_long(self):
        """Test rejection of filenames that are too long."""
        long_filename = "a" * 300 + ".json"

        with pytest.raises(InvalidFilenameError):
            PathValidator.validate_filename(long_filename, [".json"])

    def test_is_safe_path_valid(self):
        """Test is_safe_path with valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            safe_paths = [
                base / "file.txt",
                base / "subdir" / "file.txt",
                base / "a" / "b" / "c" / "file.txt",
            ]

            for path in safe_paths:
                assert PathValidator.is_safe_path(path, base)

    def test_is_safe_path_invalid(self):
        """Test is_safe_path with invalid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)

            unsafe_paths = [
                base / ".." / "etc",
                Path("/etc/passwd"),
                base / "subdir" / ".." / ".." / "etc",
            ]

            for path in unsafe_paths:
                assert not PathValidator.is_safe_path(path, base)


class TestSecureFileOperations:
    """Test the SecureFileOperations class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_safe_write_json(self, temp_dir):
        """Test safe JSON writing."""
        file_path = temp_dir / "test.json"
        data = {"key": "value", "number": 42}

        SecureFileOperations.safe_write_json(file_path, data, temp_dir)

        assert file_path.exists()

        import json

        with open(file_path) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_safe_write_json_traversal(self, temp_dir):
        """Test that path traversal is blocked in safe_write_json."""
        bad_path = temp_dir / ".." / "bad.json"

        with pytest.raises(PathTraversalError):
            SecureFileOperations.safe_write_json(bad_path, {}, temp_dir)

    def test_safe_write_json_atomic(self, temp_dir):
        """Test atomic write behavior."""
        file_path = temp_dir / "atomic.json"

        # Write initial data
        SecureFileOperations.safe_write_json(file_path, {"v": 1}, temp_dir)

        # Simulate a write failure during the atomic operation
        with patch("pathlib.Path.rename", side_effect=OSError("Rename failed")):
            with pytest.raises(OSError):
                SecureFileOperations.safe_write_json(file_path, {"v": 2}, temp_dir)

        # Original file should still have old data
        import json

        with open(file_path) as f:
            data = json.load(f)
        assert data == {"v": 1}

    def test_safe_read_json(self, temp_dir):
        """Test safe JSON reading."""
        file_path = temp_dir / "test.json"
        data = {"key": "value", "list": [1, 2, 3]}

        import json

        with open(file_path, "w") as f:
            json.dump(data, f)

        loaded = SecureFileOperations.safe_read_json(file_path, temp_dir)
        assert loaded == data

    def test_safe_read_json_nonexistent(self, temp_dir):
        """Test reading nonexistent file."""
        file_path = temp_dir / "nonexistent.json"

        result = SecureFileOperations.safe_read_json(file_path, temp_dir)
        assert result is None

    def test_safe_read_json_invalid(self, temp_dir):
        """Test reading invalid JSON."""
        file_path = temp_dir / "invalid.json"
        file_path.write_text("not valid json")

        result = SecureFileOperations.safe_read_json(file_path, temp_dir)
        assert result is None

    def test_safe_read_json_traversal(self, temp_dir):
        """Test that path traversal is blocked in safe_read_json."""
        bad_path = temp_dir / ".." / "etc" / "passwd"

        with pytest.raises(PathTraversalError):
            SecureFileOperations.safe_read_json(bad_path, temp_dir)

    def test_safe_delete(self, temp_dir):
        """Test safe file deletion."""
        file_path = temp_dir / "delete_me.json"
        file_path.write_text("delete this")

        assert file_path.exists()

        SecureFileOperations.safe_delete(file_path, temp_dir)

        assert not file_path.exists()

    def test_safe_delete_nonexistent(self, temp_dir):
        """Test deleting nonexistent file."""
        file_path = temp_dir / "nonexistent.json"

        # Should not raise
        SecureFileOperations.safe_delete(file_path, temp_dir)

    def test_safe_delete_traversal(self, temp_dir):
        """Test that path traversal is blocked in safe_delete."""
        bad_path = temp_dir / ".." / "important.conf"

        with pytest.raises(PathTraversalError):
            SecureFileOperations.safe_delete(bad_path, temp_dir)

    def test_safe_list_files(self, temp_dir):
        """Test safe file listing."""
        # Create some files
        (temp_dir / "file1.json").write_text("{}")
        (temp_dir / "file2.json").write_text("{}")
        (temp_dir / "file3.txt").write_text("text")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file4.json").write_text("{}")

        # List JSON files
        json_files = SecureFileOperations.safe_list_files(temp_dir, temp_dir, pattern="*.json")
        json_names = [f.name for f in json_files]

        assert "file1.json" in json_names
        assert "file2.json" in json_names
        assert "file3.txt" not in json_names
        assert len(json_names) == 2  # Not recursive by default

    def test_safe_list_files_pattern(self, temp_dir):
        """Test file listing with different patterns."""
        (temp_dir / "test1.json").write_text("{}")
        (temp_dir / "test2.json").write_text("{}")
        (temp_dir / "other.json").write_text("{}")

        test_files = SecureFileOperations.safe_list_files(temp_dir, temp_dir, pattern="test*.json")
        test_names = [f.name for f in test_files]

        assert "test1.json" in test_names
        assert "test2.json" in test_names
        assert "other.json" not in test_names

    def test_safe_list_files_traversal(self, temp_dir):
        """Test that path traversal is blocked in safe_list_files."""
        bad_path = temp_dir / ".."

        with pytest.raises(PathTraversalError):
            SecureFileOperations.safe_list_files(bad_path, temp_dir)

    def test_ensure_directory(self, temp_dir):
        """Test directory creation."""
        new_dir = temp_dir / "new" / "nested" / "directory"

        SecureFileOperations.ensure_directory(new_dir, temp_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_directory_exists(self, temp_dir):
        """Test ensure_directory with existing directory."""
        existing = temp_dir / "existing"
        existing.mkdir()

        # Should not raise
        SecureFileOperations.ensure_directory(existing, temp_dir)

        assert existing.exists()

    def test_ensure_directory_traversal(self, temp_dir):
        """Test that path traversal is blocked in ensure_directory."""
        bad_path = temp_dir / ".." / "bad_dir"

        with pytest.raises(PathTraversalError):
            SecureFileOperations.ensure_directory(bad_path, temp_dir)

    def test_get_file_size_safe(self, temp_dir):
        """Test safe file size retrieval."""
        file_path = temp_dir / "test.txt"
        content = "x" * 1000
        file_path.write_text(content)

        size = SecureFileOperations.get_file_size_safe(file_path, temp_dir)
        assert size == len(content.encode())

    def test_get_file_size_safe_nonexistent(self, temp_dir):
        """Test file size for nonexistent file."""
        file_path = temp_dir / "nonexistent.txt"

        size = SecureFileOperations.get_file_size_safe(file_path, temp_dir)
        assert size == 0

    def test_get_file_size_safe_traversal(self, temp_dir):
        """Test that path traversal is blocked in get_file_size_safe."""
        bad_path = temp_dir / ".." / "file.txt"

        with pytest.raises(PathTraversalError):
            SecureFileOperations.get_file_size_safe(bad_path, temp_dir)
