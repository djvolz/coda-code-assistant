"""
Common error handling for services layer.

This module provides standardized error types and handling patterns
for both the agents and tools services.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better handling."""

    VALIDATION = "validation"
    EXECUTION = "execution"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    PROVIDER = "provider"
    TOOL = "tool"
    SYSTEM = "system"


@dataclass
class ServiceError(Exception):
    """
    Base error class for all service layer errors.

    Provides structured error information that can be:
    - Logged consistently
    - Converted to user-friendly messages
    - Used for error recovery strategies
    """

    message: str
    category: ErrorCategory
    severity: ErrorSeverity = ErrorSeverity.ERROR
    details: dict[str, Any] = None
    cause: Exception = None
    recoverable: bool = True

    def __post_init__(self):
        """Initialize the exception message."""
        super().__init__(self.message)
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "recoverable": self.recoverable,
            "cause": str(self.cause) if self.cause else None,
        }

    def user_message(self) -> str:
        """Get user-friendly error message."""
        # Map technical errors to user-friendly messages
        user_messages = {
            ErrorCategory.VALIDATION: "Invalid input provided",
            ErrorCategory.PERMISSION: "Permission denied for this operation",
            ErrorCategory.NOT_FOUND: "Requested resource not found",
            ErrorCategory.TIMEOUT: "Operation timed out",
            ErrorCategory.PROVIDER: "AI provider error",
            ErrorCategory.TOOL: "Tool execution failed",
        }

        base_msg = user_messages.get(self.category, "An error occurred")

        # Add specific context if available
        if self.category == ErrorCategory.VALIDATION and "field" in self.details:
            return f"{base_msg}: {self.details['field']}"
        elif self.category == ErrorCategory.NOT_FOUND and "resource" in self.details:
            return f"{base_msg}: {self.details['resource']}"
        elif self.category == ErrorCategory.TOOL and "tool_name" in self.details:
            return f"{base_msg}: {self.details['tool_name']}"

        return f"{base_msg}: {self.message}"


# Specific error types for common scenarios


class ValidationError(ServiceError):
    """Input validation error."""

    def __init__(self, message: str, field: str = None, **kwargs):
        details = {"field": field} if field else {}
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details=details,
            **kwargs,
        )


class ToolExecutionError(ServiceError):
    """Tool execution failed."""

    def __init__(self, message: str, tool_name: str, **kwargs):
        super().__init__(
            message=message, category=ErrorCategory.TOOL, details={"tool_name": tool_name}, **kwargs
        )


class ToolNotFoundError(ServiceError):
    """Tool not found in registry."""

    def __init__(self, tool_name: str, **kwargs):
        super().__init__(
            message=f"Tool '{tool_name}' not found",
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.WARNING,
            details={"resource": "tool", "tool_name": tool_name},
            **kwargs,
        )


class PermissionError(ServiceError):
    """Permission denied for operation."""

    def __init__(self, message: str, operation: str = None, resource: str = None, **kwargs):
        details = {}
        if operation:
            details["operation"] = operation
        if resource:
            details["resource"] = resource

        super().__init__(
            message=message,
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.ERROR,
            details=details,
            recoverable=False,
            **kwargs,
        )


class ProviderError(ServiceError):
    """AI provider error."""

    def __init__(self, message: str, provider_name: str = None, **kwargs):
        details = {"provider": provider_name} if provider_name else {}
        super().__init__(
            message=message, category=ErrorCategory.PROVIDER, details=details, **kwargs
        )


class TimeoutError(ServiceError):
    """Operation timed out."""

    def __init__(
        self, message: str, operation: str = None, timeout_seconds: float = None, **kwargs
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.WARNING,
            details=details,
            **kwargs,
        )


# Error handling utilities


class ErrorHandler:
    """Centralized error handling utilities."""

    @staticmethod
    def wrap_error(error: Exception, context: str = None) -> ServiceError:
        """
        Wrap a generic exception in a ServiceError.

        Args:
            error: The exception to wrap
            context: Additional context about where the error occurred

        Returns:
            ServiceError instance
        """
        if isinstance(error, ServiceError):
            return error

        # Map common Python errors
        if isinstance(error, ValueError):
            return ValidationError(message=str(error), cause=error)
        elif isinstance(error, PermissionError):
            return PermissionError(message=str(error), cause=error)
        elif isinstance(error, FileNotFoundError):
            return ServiceError(
                message=str(error),
                category=ErrorCategory.NOT_FOUND,
                details={"resource": "file"},
                cause=error,
            )
        elif isinstance(error, TimeoutError):
            return TimeoutError(message=str(error), cause=error)
        else:
            return ServiceError(
                message=str(error),
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.ERROR,
                details={"context": context} if context else {},
                cause=error,
            )

    @staticmethod
    def format_error_chain(error: ServiceError) -> str:
        """
        Format an error with its cause chain.

        Args:
            error: The service error

        Returns:
            Formatted error string
        """
        messages = [f"{error.category.value}: {error.message}"]

        current = error.cause
        while current:
            messages.append(f"  Caused by: {str(current)}")
            if hasattr(current, "cause"):
                current = current.cause
            else:
                break

        return "\n".join(messages)

    @staticmethod
    def should_retry(error: ServiceError) -> bool:
        """
        Determine if an operation should be retried based on the error.

        Args:
            error: The service error

        Returns:
            True if the operation should be retried
        """
        # Don't retry non-recoverable errors
        if not error.recoverable:
            return False

        # Retry certain categories with appropriate backoff
        retryable_categories = {
            ErrorCategory.TIMEOUT,
            ErrorCategory.PROVIDER,
        }

        return error.category in retryable_categories


# Context managers for error handling


class ErrorContext:
    """
    Context manager for consistent error handling.

    Usage:
        with ErrorContext("tool_execution", tool_name="my_tool"):
            # code that might raise exceptions
    """

    def __init__(self, context: str, **details):
        self.context = context
        self.details = details

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            # Wrap the exception with context
            wrapped = ErrorHandler.wrap_error(exc_val, self.context)

            # Add any additional details
            if self.details:
                wrapped.details.update(self.details)

            # Re-raise the wrapped exception
            raise wrapped from exc_val

        return False
