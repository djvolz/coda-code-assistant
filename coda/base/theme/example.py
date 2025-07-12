#!/usr/bin/env python3
"""Standalone example showing the theme module works without other Coda modules.

This example demonstrates that the theme module:
1. Has zero external dependencies
2. Can be used in any project
3. Provides comprehensive theming support

When using this module standalone:
- Copy the entire theme directory to your project
- Import directly: from theme import ThemeManager
- Or run this example: python example.py
"""

import json

# Standalone imports - use these when copying this module to another project
try:
    # When running as standalone module
    from manager import ThemeManager
    from themes import get_dark_themes, get_light_themes
except ImportError:
    # When running from coda package
    from coda.base.theme import ThemeManager
    from coda.base.theme.themes import get_dark_themes, get_light_themes


def print_colored(text: str, color: str = "") -> None:
    """Print text with optional ANSI color codes."""
    if not color:
        print(text)
        return

    # Simple ANSI color mapping
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "cyan": "\033[36m",
        "bright_green": "\033[92m",
        "bright_blue": "\033[94m",
        "bold": "\033[1m",
    }

    reset = "\033[0m"
    color_code = colors.get(color, "")
    print(f"{color_code}{text}{reset}")


def demo_theme(theme_mgr: ThemeManager, theme_name: str) -> None:
    """Demonstrate a specific theme."""
    theme_mgr.set_theme(theme_name)
    theme = theme_mgr.current_theme
    console_theme = theme_mgr.get_console_theme()

    print(f"\n--- {theme.name.upper()} THEME ---")
    print(f"Description: {theme.description}")
    print(f"Dark theme: {theme.is_dark}, High contrast: {theme.high_contrast}")
    print()

    # Demo console colors
    print_colored("✓ Success message", console_theme.success)
    print_colored("✗ Error message", console_theme.error)
    print_colored("⚠ Warning message", console_theme.warning)
    print_colored("ℹ Info message", console_theme.info)
    print_colored("User: Hello!", console_theme.user_message)
    print_colored("Assistant: Hi there!", console_theme.assistant_message)
    print()


def main():
    """Demonstrate usage of the theme module."""
    print("=== Coda Theme Module Demo ===\n")

    # 1. Basic usage
    print("1. Basic Theme Management:")
    theme_mgr = ThemeManager()
    print(f"  Default theme: {theme_mgr.current_theme_name}")
    print(f"  Available themes: {', '.join(theme_mgr.list_theme_names())}")
    print()

    # 2. Theme categories
    print("2. Theme Categories:")
    print(f"  Dark themes: {', '.join(get_dark_themes())}")
    print(f"  Light themes: {', '.join(get_light_themes())}")
    print()

    # 3. Demo a few themes
    print("3. Theme Demonstrations:")
    for theme_name in ["default", "dark", "minimal", "vibrant"]:
        demo_theme(theme_mgr, theme_name)

    # 4. Create custom theme
    print("4. Custom Theme Creation:")
    custom = ThemeManager.create_custom_theme(
        "mycompany",
        "Company brand colors",
        base_theme="dark",
        success="#00aa00",
        error="#ff0000",
        info="#0066cc",
        user_message="#0066cc",
        assistant_message="#00aa00",
    )

    theme_mgr.register_custom_theme(custom)
    demo_theme(theme_mgr, "mycompany")

    # 5. Export/Import theme
    print("5. Theme Export/Import:")
    exported = theme_mgr.export_theme("mycompany")
    print(f"  Exported theme data: {json.dumps(exported, indent=2)[:200]}...")

    # Import with modifications
    exported["name"] = "mycompany_v2"
    exported["description"] = "Updated company theme"
    exported["console"]["warning"] = "#ff9900"

    imported = theme_mgr.import_theme(exported)
    theme_mgr.register_custom_theme(imported)
    print(f"  Imported theme: {imported.name}")
    print()

    # 6. Theme validation
    print("6. Theme Validation:")
    try:
        # Try to create invalid theme
        ThemeManager.create_custom_theme(
            "invalid",
            "Theme with invalid colors",
            success="not_a_color",
            error="#gggggg",  # Invalid hex
        )
    except ValueError as e:
        print(f"  ✓ Validation caught invalid colors: {str(e)[:60]}...")
    print()

    # 7. Access theme data programmatically
    print("7. Programmatic Theme Access:")
    theme_mgr.set_theme("dracula_dark")
    console = theme_mgr.get_console_theme()
    prompt = theme_mgr.get_prompt_theme()

    print(f"  Console success color: {console.success}")
    print(f"  Console error color: {console.error}")
    print(f"  Prompt input field style: {prompt.input_field}")
    print(f"  Prompt completion style: {prompt.completion}")
    print()

    print("✓ Theme module works standalone!")
    print("✓ Zero external dependencies")
    print("✓ Can be copy-pasted to any project")
    print("✓ Provides complete theming solution")


if __name__ == "__main__":
    main()
