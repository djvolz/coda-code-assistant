"""
Tool permission management system.

This module provides a comprehensive permission system for controlling
access to tools based on user roles, tool categories, and security policies.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import ToolSchema


class PermissionLevel(str, Enum):
    """Permission levels for tool access."""

    DENIED = "denied"  # Explicitly denied access
    READ_ONLY = "read_only"  # Can view but not execute
    LIMITED = "limited"  # Can execute with restrictions
    STANDARD = "standard"  # Normal execution permissions
    ELEVATED = "elevated"  # Can execute dangerous operations
    ADMIN = "admin"  # Full access to all tools


class ToolCategory(str, Enum):
    """Tool categories for permission management."""

    FILESYSTEM = "filesystem"
    SYSTEM = "system"
    WEB = "web"
    GIT = "git"
    CUSTOM = "custom"
    ALL = "all"


class PermissionRule(BaseModel):
    """A permission rule that can be applied to tools."""

    rule_id: str = Field(..., description="Unique identifier for this rule")
    name: str = Field(..., description="Human-readable name for the rule")
    description: str = Field(..., description="Description of what this rule does")

    # What this rule applies to
    tool_names: list[str] | None = Field(None, description="Specific tools this rule applies to")
    tool_categories: list[ToolCategory] | None = Field(
        None, description="Tool categories this rule applies to"
    )
    tool_patterns: list[str] | None = Field(None, description="Tool name patterns (regex)")

    # Permission level granted/denied
    permission_level: PermissionLevel = Field(..., description="Permission level to grant/deny")

    # Conditions
    require_approval: bool = Field(False, description="Whether this rule requires user approval")
    max_daily_usage: int | None = Field(None, description="Maximum uses per day")
    allowed_hours: list[int] | None = Field(None, description="Hours when tool can be used (0-23)")
    allowed_days: list[int] | None = Field(
        None, description="Days when tool can be used (0-6, Mon-Sun)"
    )

    # Parameter restrictions
    parameter_restrictions: dict[str, Any] = Field(
        default_factory=dict, description="Restrictions on tool parameters"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(None, description="When this rule expires")
    priority: int = Field(50, description="Rule priority (higher number = higher priority)")

    def is_expired(self) -> bool:
        """Check if this rule has expired."""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at

    def applies_to_tool(self, tool_name: str, tool_category: str) -> bool:
        """Check if this rule applies to a specific tool."""
        if self.is_expired():
            return False

        # Check specific tool names
        if self.tool_names and tool_name in self.tool_names:
            return True

        # Check categories
        if self.tool_categories:
            if ToolCategory.ALL in self.tool_categories:
                return True
            if tool_category in [cat.value for cat in self.tool_categories]:
                return True

        # Check patterns (basic wildcard support)
        if self.tool_patterns:
            import fnmatch

            for pattern in self.tool_patterns:
                if fnmatch.fnmatch(tool_name, pattern):
                    return True

        return False

    def is_usage_allowed_now(self) -> bool:
        """Check if usage is allowed at the current time."""
        now = datetime.utcnow()

        # Check allowed hours
        if self.allowed_hours is not None:
            if now.hour not in self.allowed_hours:
                return False

        # Check allowed days
        if self.allowed_days is not None:
            if now.weekday() not in self.allowed_days:
                return False

        return True


class UserPermissions(BaseModel):
    """Permission configuration for a specific user or session."""

    user_id: str = Field(..., description="User or session identifier")

    # Base permission level
    base_permission: PermissionLevel = Field(
        PermissionLevel.STANDARD, description="Base permission level"
    )

    # Applied rules
    rules: list[PermissionRule] = Field(
        default_factory=list, description="Permission rules for this user"
    )

    # Usage tracking
    daily_usage: dict[str, int] = Field(
        default_factory=dict, description="Tool usage count per day"
    )
    last_usage_date: str | None = Field(
        None, description="Last date usage was tracked (YYYY-MM-DD)"
    )

    # Approval tracking
    pending_approvals: list[str] = Field(
        default_factory=list, description="Tool invocations awaiting approval"
    )
    approved_operations: set[str] = Field(
        default_factory=set, description="Recently approved dangerous operations"
    )

    def get_effective_permission(self, tool_name: str, tool_schema: ToolSchema) -> PermissionLevel:
        """Get the effective permission level for a tool."""
        # Start with base permission
        effective_permission = self.base_permission

        # Apply rules in priority order (highest first)
        applicable_rules = [
            rule
            for rule in sorted(self.rules, key=lambda r: r.priority, reverse=True)
            if rule.applies_to_tool(tool_name, tool_schema.category)
        ]

        for rule in applicable_rules:
            if rule.permission_level == PermissionLevel.DENIED:
                return PermissionLevel.DENIED
            elif rule.permission_level.value > effective_permission.value:
                effective_permission = rule.permission_level

        return effective_permission

    def can_execute_tool(
        self, tool_name: str, tool_schema: ToolSchema, arguments: dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if a tool can be executed with given arguments."""
        # Check base permission
        permission = self.get_effective_permission(tool_name, tool_schema)

        if permission == PermissionLevel.DENIED:
            return False, "Tool access denied by permission rules"

        if permission == PermissionLevel.READ_ONLY:
            return False, "Tool is read-only for this user"

        # Check if tool is dangerous and requires elevated permission
        if tool_schema.dangerous and permission < PermissionLevel.ELEVATED:
            return False, "Dangerous tool requires elevated permissions"

        # Check applicable rules for additional restrictions
        for rule in self.rules:
            if not rule.applies_to_tool(tool_name, tool_schema.category):
                continue

            # Check time restrictions
            if not rule.is_usage_allowed_now():
                return False, f"Tool usage not allowed at this time (rule: {rule.name})"

            # Check daily usage limits
            if rule.max_daily_usage is not None:
                today = datetime.utcnow().strftime("%Y-%m-%d")
                if self.last_usage_date != today:
                    self.daily_usage.clear()
                    self.last_usage_date = today

                current_usage = self.daily_usage.get(tool_name, 0)
                if current_usage >= rule.max_daily_usage:
                    return False, f"Daily usage limit exceeded for {tool_name} (rule: {rule.name})"

            # Check parameter restrictions
            if rule.parameter_restrictions:
                for param_name, restriction in rule.parameter_restrictions.items():
                    if param_name in arguments:
                        value = arguments[param_name]
                        if not self._check_parameter_restriction(param_name, value, restriction):
                            return (
                                False,
                                f"Parameter {param_name} violates restriction (rule: {rule.name})",
                            )

        return True, "Permission granted"

    def _check_parameter_restriction(self, param_name: str, value: Any, restriction: Any) -> bool:
        """Check if a parameter value meets the restriction."""
        if isinstance(restriction, dict):
            # Complex restriction
            if "allowed_values" in restriction:
                return value in restriction["allowed_values"]
            if "max_value" in restriction:
                return value <= restriction["max_value"]
            if "min_value" in restriction:
                return value >= restriction["min_value"]
            if "max_length" in restriction and isinstance(value, str):
                return len(value) <= restriction["max_length"]
            if "pattern" in restriction and isinstance(value, str):
                import re

                return bool(re.match(restriction["pattern"], value))
        else:
            # Simple restriction - exact match
            return value == restriction

        return True

    def record_tool_usage(self, tool_name: str) -> None:
        """Record usage of a tool for rate limiting."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.last_usage_date != today:
            self.daily_usage.clear()
            self.last_usage_date = today

        self.daily_usage[tool_name] = self.daily_usage.get(tool_name, 0) + 1

    def requires_approval(self, tool_name: str, tool_schema: ToolSchema) -> bool:
        """Check if tool execution requires user approval."""
        # Check if any applicable rule requires approval
        for rule in self.rules:
            if rule.applies_to_tool(tool_name, tool_schema.category) and rule.require_approval:
                return True

        # Dangerous tools always require approval unless pre-approved
        if tool_schema.dangerous:
            operation_key = self._get_operation_key(tool_name, {})
            return operation_key not in self.approved_operations

        return False

    def approve_operation(
        self, tool_name: str, arguments: dict[str, Any], expires_in_minutes: int = 60
    ) -> str:
        """Approve a dangerous operation for limited time."""
        operation_key = self._get_operation_key(tool_name, arguments)
        self.approved_operations.add(operation_key)

        # Clean up expired approvals
        # Note: In a real implementation, this would use timestamps
        return operation_key

    def _get_operation_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Generate a key for tracking approved operations."""
        # Create a hash of tool name and arguments for tracking
        content = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class PermissionManager:
    """Manages tool permissions across users and sessions."""

    def __init__(self):
        self.users: dict[str, UserPermissions] = {}
        self.global_rules: list[PermissionRule] = []
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default permission rules."""
        # Default rules for safe operation
        safe_rule = PermissionRule(
            rule_id="default_safe",
            name="Default Safe Tools",
            description="Allow standard access to safe tools",
            tool_categories=[ToolCategory.FILESYSTEM, ToolCategory.GIT, ToolCategory.WEB],
            permission_level=PermissionLevel.STANDARD,
            priority=10,
        )

        # Restrict dangerous system tools
        system_rule = PermissionRule(
            rule_id="system_restricted",
            name="System Tools Restricted",
            description="Require elevated permissions for system tools",
            tool_categories=[ToolCategory.SYSTEM],
            permission_level=PermissionLevel.ELEVATED,
            require_approval=True,
            priority=20,
        )

        # Rate limit shell commands
        shell_limit_rule = PermissionRule(
            rule_id="shell_rate_limit",
            name="Shell Command Rate Limit",
            description="Limit shell command executions per day",
            tool_names=["shell_execute"],
            permission_level=PermissionLevel.ELEVATED,
            max_daily_usage=50,
            require_approval=True,
            priority=30,
        )

        self.global_rules = [safe_rule, system_rule, shell_limit_rule]

    def get_user_permissions(self, user_id: str) -> UserPermissions:
        """Get permissions for a user, creating default if not exists."""
        if user_id not in self.users:
            self.users[user_id] = UserPermissions(user_id=user_id, rules=self.global_rules.copy())
        return self.users[user_id]

    def check_tool_permission(
        self, user_id: str, tool_name: str, tool_schema: ToolSchema, arguments: dict[str, Any]
    ) -> tuple[bool, str, bool]:
        """
        Check if a user can execute a tool.

        Returns:
            (can_execute, reason, requires_approval)
        """
        user_perms = self.get_user_permissions(user_id)

        can_execute, reason = user_perms.can_execute_tool(tool_name, tool_schema, arguments)
        requires_approval = (
            user_perms.requires_approval(tool_name, tool_schema) if can_execute else False
        )

        return can_execute, reason, requires_approval

    def record_tool_execution(self, user_id: str, tool_name: str) -> None:
        """Record that a user executed a tool."""
        user_perms = self.get_user_permissions(user_id)
        user_perms.record_tool_usage(tool_name)

    def approve_dangerous_operation(
        self, user_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Approve a dangerous operation for a user."""
        user_perms = self.get_user_permissions(user_id)
        return user_perms.approve_operation(tool_name, arguments)

    def add_user_rule(self, user_id: str, rule: PermissionRule) -> None:
        """Add a permission rule for a specific user."""
        user_perms = self.get_user_permissions(user_id)
        user_perms.rules.append(rule)

    def add_global_rule(self, rule: PermissionRule) -> None:
        """Add a global permission rule."""
        self.global_rules.append(rule)
        # Apply to existing users
        for user_perms in self.users.values():
            user_perms.rules.append(rule)

    def set_user_base_permission(self, user_id: str, level: PermissionLevel) -> None:
        """Set the base permission level for a user."""
        user_perms = self.get_user_permissions(user_id)
        user_perms.base_permission = level

    def get_user_tool_summary(self, user_id: str) -> dict[str, Any]:
        """Get a summary of user's tool permissions and usage."""
        user_perms = self.get_user_permissions(user_id)

        return {
            "user_id": user_id,
            "base_permission": user_perms.base_permission.value,
            "active_rules": len([r for r in user_perms.rules if not r.is_expired()]),
            "daily_usage": user_perms.daily_usage,
            "pending_approvals": len(user_perms.pending_approvals),
            "approved_operations": len(user_perms.approved_operations),
        }


# Global permission manager instance
permission_manager = PermissionManager()


# Convenience functions for tool integration
def check_tool_permission(
    user_id: str, tool_name: str, tool_schema: ToolSchema, arguments: dict[str, Any]
) -> tuple[bool, str, bool]:
    """Check tool permission for a user."""
    return permission_manager.check_tool_permission(user_id, tool_name, tool_schema, arguments)


def record_tool_execution(user_id: str, tool_name: str) -> None:
    """Record tool execution for a user."""
    permission_manager.record_tool_execution(user_id, tool_name)


def approve_dangerous_operation(user_id: str, tool_name: str, arguments: dict[str, Any]) -> str:
    """Approve a dangerous operation."""
    return permission_manager.approve_dangerous_operation(user_id, tool_name, arguments)
