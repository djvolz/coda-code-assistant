"""Security utilities for observability components.

This module provides security utilities including path validation,
permission checks, and secure file operations.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Base exception for security-related errors."""

    pass


class PathTraversalError(SecurityError):
    """Raised when path traversal is detected."""

    pass


class PermissionError(SecurityError):
    """Raised when file permissions are insecure."""

    pass


class PathValidator:
    """Validate file paths for security."""

    @staticmethod
    def validate_export_path(path: Path, allowed_base: Path) -> Path:
        """Validate export path is within allowed directory.

        Args:
            path: Path to validate
            allowed_base: Base directory that path must be within

        Returns:
            Resolved absolute path

        Raises:
            PathTraversalError: If path traversal is detected
        """
        try:
            # Resolve to absolute paths
            resolved_path = path.resolve()
            allowed_base_resolved = allowed_base.resolve()

            # Check if path is within allowed directory
            resolved_path.relative_to(allowed_base_resolved)

            # Additional checks for common traversal patterns
            path_str = str(path)
            if ".." in path_str:
                # Check if it's a legitimate use (e.g., in filename)
                parts = path_str.split(os.sep)
                if ".." in parts:
                    raise PathTraversalError(f"Path traversal detected in: {path}")

            # Check for null bytes
            if "\x00" in path_str:
                raise PathTraversalError(f"Null byte in path: {path}")

            return resolved_path

        except ValueError:
            # relative_to raises ValueError if path is not relative to base
            raise PathTraversalError(
                f"Path '{path}' is not within allowed directory '{allowed_base}'"
            ) from None

    @staticmethod
    def validate_filename(filename: str, allowed_extensions: list[str] | None = None) -> str:
        """Validate a filename for security.

        Args:
            filename: Filename to validate
            allowed_extensions: Optional list of allowed file extensions

        Returns:
            Validated filename

        Raises:
            SecurityError: If filename is invalid
        """
        # Check for empty filename
        if not filename or filename.strip() == "":
            raise SecurityError("Empty filename")

        # Check for path separators in filename
        if os.sep in filename or "/" in filename or "\\" in filename:
            raise SecurityError(f"Path separators not allowed in filename: {filename}")

        # Check for null bytes
        if "\x00" in filename:
            raise SecurityError(f"Null byte in filename: {filename}")

        # Check for special filenames
        base_name = filename.lower()
        if base_name in {
            ".",
            "..",
            "con",
            "prn",
            "aux",
            "nul",
            "com1",
            "com2",
            "com3",
            "com4",
            "com5",
            "com6",
            "com7",
            "com8",
            "com9",
            "lpt1",
            "lpt2",
            "lpt3",
            "lpt4",
            "lpt5",
            "lpt6",
            "lpt7",
            "lpt8",
            "lpt9",
        }:
            raise SecurityError(f"Reserved filename: {filename}")

        # Check extension if required
        if allowed_extensions:
            ext = Path(filename).suffix.lower()
            if ext not in allowed_extensions:
                raise SecurityError(
                    f"File extension '{ext}' not allowed. "
                    f"Allowed extensions: {', '.join(allowed_extensions)}"
                )

        return filename

    @staticmethod
    def ensure_secure_permissions(path: Path, required_mode: int = 0o600) -> None:
        """Ensure file has secure permissions.

        Args:
            path: Path to check/update
            required_mode: Required permission mode (default: 0o600 - owner read/write only)

        Raises:
            PermissionError: If permissions cannot be set
        """
        if not path.exists():
            return

        try:
            current_stat = os.stat(path)
            current_mode = current_stat.st_mode & 0o777

            # Check if others have any permissions
            if current_mode & 0o077:
                logger.warning(
                    f"Insecure permissions detected on {path}: "
                    f"{oct(current_mode)} (others have access)"
                )

                # Try to fix permissions
                try:
                    os.chmod(path, required_mode)
                    logger.info(f"Fixed permissions on {path} to {oct(required_mode)}")
                except OSError as e:
                    raise PermissionError(f"Failed to set secure permissions on {path}: {e}") from e

        except OSError as e:
            logger.error(f"Failed to check permissions on {path}: {e}")

    @staticmethod
    def validate_json_size(json_str: str, max_size_mb: float = 10.0) -> None:
        """Validate JSON string size to prevent DoS.

        Args:
            json_str: JSON string to validate
            max_size_mb: Maximum allowed size in megabytes

        Raises:
            SecurityError: If JSON is too large
        """
        size_bytes = len(json_str.encode("utf-8"))
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > max_size_mb:
            raise SecurityError(
                f"JSON size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
            )


class SecureFileOperations:
    """Secure file operations with validation and atomic writes."""

    @staticmethod
    def secure_write(path: Path, content: str, mode: int = 0o600) -> None:
        """Write file securely with atomic operation and permission setting.

        Args:
            path: Path to write to
            content: Content to write
            mode: File permission mode
        """
        import tempfile

        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )

        try:
            # Write content
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # Set permissions before rename
            os.chmod(temp_path, mode)

            # Atomic rename
            os.replace(temp_path, path)

        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def secure_read(path: Path, max_size_mb: float = 10.0) -> str:
        """Read file securely with size validation.

        Args:
            path: Path to read from
            max_size_mb: Maximum file size to read

        Returns:
            File contents

        Raises:
            SecurityError: If file is too large
        """
        # Check file size first
        stat = os.stat(path)
        size_mb = stat.st_size / (1024 * 1024)

        if size_mb > max_size_mb:
            raise SecurityError(
                f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
            )

        # Read file
        with open(path, encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def secure_delete(path: Path, overwrite: bool = False) -> None:
        """Securely delete a file.

        Args:
            path: Path to delete
            overwrite: Whether to overwrite file contents before deletion
        """
        if not path.exists():
            return

        try:
            if overwrite and path.is_file():
                # Overwrite with random data
                size = path.stat().st_size
                with open(path, "wb") as f:
                    import secrets

                    # Write random data in chunks
                    chunk_size = 4096
                    for _ in range(0, size, chunk_size):
                        chunk = secrets.token_bytes(min(chunk_size, size))
                        f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())

            # Delete the file
            path.unlink()

        except Exception as e:
            logger.error(f"Failed to securely delete {path}: {e}")
            raise
