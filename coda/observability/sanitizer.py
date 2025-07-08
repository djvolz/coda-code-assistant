"""Data sanitization utilities for observability.

This module provides utilities to sanitize sensitive data from logs,
errors, and other observability outputs.
"""

import logging
import re
from re import Pattern
from typing import Any

logger = logging.getLogger(__name__)


class DataSanitizer:
    """Sanitize sensitive data from logs and errors."""

    # Common patterns for sensitive data
    DEFAULT_PATTERNS: list[Pattern] = [
        # API keys and tokens
        re.compile(
            r'(api[-_]?key|apikey|access[-_]?token|auth[-_]?token|authentication[-_]?token|private[-_]?key)\s*[:=]\s*["\']?([A-Za-z0-9+/=_\-]{20,})["\']?',
            re.IGNORECASE,
        ),
        re.compile(r"(Bearer|Authorization)\s+([A-Za-z0-9+/=_\-]{20,})", re.IGNORECASE),
        # Passwords and secrets
        re.compile(
            r'(password|passwd|pwd|secret|pass)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', re.IGNORECASE
        ),
        # Email addresses
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        # Credit card numbers (basic patterns)
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),  # 16 digits
        re.compile(r"\b\d{15}\b"),  # Amex
        # Social Security Numbers
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        # AWS credentials
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
        re.compile(r'aws_secret_access_key\s*=\s*["\']?([A-Za-z0-9+/]{40})["\']?', re.IGNORECASE),
        # Database connection strings
        re.compile(
            r"(mongodb|postgres|postgresql|mysql|redis|mssql)://[^:\s]+:[^@\s]+@[^\s]+",
            re.IGNORECASE,
        ),
        # JWT tokens
        re.compile(r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*"),
        # Private keys
        re.compile(
            r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----[\s\S]+?-----END\s+(RSA\s+)?PRIVATE\s+KEY-----"
        ),
    ]

    # Sensitive key names to redact
    SENSITIVE_KEYS = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "key",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "private",
        "access_token",
        "refresh_token",
        "client_secret",
        "client_id",
        "database_url",
        "db_url",
        "connection_string",
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_session_token",
    }

    def __init__(
        self,
        custom_patterns: list[Pattern] | None = None,
        additional_sensitive_keys: list[str] | None = None,
    ):
        """Initialize the sanitizer.

        Args:
            custom_patterns: Additional regex patterns to match sensitive data
            additional_sensitive_keys: Additional key names to consider sensitive
        """
        self.patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            self.patterns.extend(custom_patterns)

        self.sensitive_keys = self.SENSITIVE_KEYS.copy()
        if additional_sensitive_keys:
            self.sensitive_keys.update(k.lower() for k in additional_sensitive_keys)

    def sanitize_string(self, text: str, placeholder: str = "***REDACTED***") -> str:
        """Sanitize a string by replacing sensitive patterns.

        Args:
            text: String to sanitize
            placeholder: Replacement text for sensitive data

        Returns:
            Sanitized string
        """
        if not isinstance(text, str):
            return text

        sanitized = text

        for pattern in self.patterns:
            try:
                # Handle patterns with groups
                if pattern.groups > 0:

                    def replace_func(match):
                        groups = match.groups()
                        if len(groups) >= 2:
                            # Keep the key/label, redact the value
                            return f"{groups[0]}={placeholder}"
                        else:
                            return placeholder

                    sanitized = pattern.sub(replace_func, sanitized)
                else:
                    # Simple replacement for patterns without groups
                    sanitized = pattern.sub(placeholder, sanitized)
            except Exception as e:
                logger.warning(f"Error applying sanitization pattern: {e}")

        return sanitized

    def sanitize_dict(
        self, data: dict[str, Any], placeholder: str = "***REDACTED***"
    ) -> dict[str, Any]:
        """Recursively sanitize a dictionary.

        Args:
            data: Dictionary to sanitize
            placeholder: Replacement text for sensitive data

        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            return data

        sanitized = {}

        for key, value in data.items():
            # Check if key name suggests sensitive data
            if any(sensitive in key.lower() for sensitive in self.sensitive_keys):
                sanitized[key] = placeholder
            elif isinstance(value, str):
                sanitized[key] = self.sanitize_string(value, placeholder)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value, placeholder)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value, placeholder)
            else:
                sanitized[key] = value

        return sanitized

    def sanitize_list(self, data: list[Any], placeholder: str = "***REDACTED***") -> list[Any]:
        """Recursively sanitize a list.

        Args:
            data: List to sanitize
            placeholder: Replacement text for sensitive data

        Returns:
            Sanitized list
        """
        if not isinstance(data, list):
            return data

        sanitized = []

        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_string(item, placeholder))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item, placeholder))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item, placeholder))
            else:
                sanitized.append(item)

        return sanitized

    def sanitize_stack_trace(self, stack_trace: str, placeholder: str = "***REDACTED***") -> str:
        """Sanitize a stack trace while preserving structure.

        Args:
            stack_trace: Stack trace string
            placeholder: Replacement text for sensitive data

        Returns:
            Sanitized stack trace
        """
        if not isinstance(stack_trace, str):
            return stack_trace

        # Split by lines to preserve structure
        lines = stack_trace.split("\n")
        sanitized_lines = []

        for line in lines:
            # Sanitize each line individually
            sanitized_line = self.sanitize_string(line, placeholder)
            sanitized_lines.append(sanitized_line)

        return "\n".join(sanitized_lines)

    def sanitize(
        self, data: str | dict | list | Any, placeholder: str = "***REDACTED***"
    ) -> str | dict | list | Any:
        """Sanitize any supported data type.

        Args:
            data: Data to sanitize
            placeholder: Replacement text for sensitive data

        Returns:
            Sanitized data
        """
        if isinstance(data, str):
            return self.sanitize_string(data, placeholder)
        elif isinstance(data, dict):
            return self.sanitize_dict(data, placeholder)
        elif isinstance(data, list):
            return self.sanitize_list(data, placeholder)
        else:
            # For other types, convert to string and sanitize
            return self.sanitize_string(str(data), placeholder)

    def add_pattern(self, pattern: str | Pattern) -> None:
        """Add a custom pattern for sanitization.

        Args:
            pattern: Regex pattern (string or compiled pattern)
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        self.patterns.append(pattern)

    def add_sensitive_key(self, key: str) -> None:
        """Add a key name to be considered sensitive.

        Args:
            key: Key name to add
        """
        self.sensitive_keys.add(key.lower())
