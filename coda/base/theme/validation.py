"""Theme validation utilities.

This module provides color validation for themes.
Zero dependencies - uses only Python standard library.
"""

try:
    from .models import Theme
except ImportError:
    # If running as standalone after copy-paste
    from models import Theme


def is_valid_color(color: str) -> bool:
    """Validate if a color string is valid for terminal output.

    Args:
        color: Color string to validate

    Returns:
        bool: True if valid color

    Examples:
        >>> is_valid_color("red")
        True
        >>> is_valid_color("#ff0000")
        True
        >>> is_valid_color("bright_blue")
        True
        >>> is_valid_color("not_a_color")
        False
    """
    if not color:
        return True  # Empty string is valid (no styling)

    # Basic color names that most terminals support
    valid_colors = {
        "black",
        "red",
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "white",
        "bright_black",
        "bright_red",
        "bright_green",
        "bright_yellow",
        "bright_blue",
        "bright_magenta",
        "bright_cyan",
        "bright_white",
        "dim",
        "bold",
        "italic",
        "underline",
        "reverse",
        "strike",
        "blink",
    }

    # Check for hex colors
    if color.startswith("#") and len(color) in (4, 7):
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False

    # Check for basic colors (possibly with styles)
    parts = color.lower().split()
    return all(part in valid_colors for part in parts)


def is_valid_prompt_style(style: str) -> bool:
    """Validate if a style string is valid for prompt toolkit.

    Args:
        style: Style string to validate

    Returns:
        bool: True if valid style

    Examples:
        >>> is_valid_prompt_style("bg:#ffffff #000000")
        True
        >>> is_valid_prompt_style("bold reverse")
        True
    """
    if not style:
        return True

    # Basic validation - prompt toolkit has complex syntax
    # We just check for obvious issues
    if style.count("#") > 2:
        return False  # Too many color codes

    # Check if it contains valid keywords
    # valid_keywords = {"bg:", "fg:", "bold", "italic", "underline", "reverse", "blink"}

    # For now, accept anything that doesn't look obviously wrong
    # Prompt toolkit will validate more thoroughly
    return True


def validate_theme_colors(theme: Theme) -> list[str]:
    """Validate all colors in a theme.

    Args:
        theme: Theme to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate console theme colors
    console_attrs = [
        "success",
        "error",
        "warning",
        "info",
        "dim",
        "bold",
        "panel_border",
        "panel_title",
        "user_message",
        "assistant_message",
        "system_message",
        "table_header",
        "table_row_odd",
        "table_row_even",
        "command",
        "command_description",
    ]

    for attr in console_attrs:
        color = getattr(theme.console, attr, "")
        if not is_valid_color(color):
            errors.append(f"Invalid console color for {attr}: {color}")

    # Validate prompt theme styles (basic validation only)
    prompt_attrs = [
        "input_field",
        "cursor",
        "selection",
        "completion",
        "completion_selected",
        "completion_meta",
        "search",
        "search_match",
        "toolbar",
        "status",
        "prompt",
        "continuation",
        "model_selected",
        "model_search",
        "model_title",
        "model_provider",
        "model_info",
    ]

    for attr in prompt_attrs:
        style = getattr(theme.prompt, attr, "")
        if not is_valid_prompt_style(style):
            errors.append(f"Invalid prompt style for {attr}: {style}")

    return errors
