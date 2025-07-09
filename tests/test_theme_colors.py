"""Unit tests for theme color application."""

from unittest.mock import Mock, patch

import pytest

from coda.themes import THEMES, ConsoleTheme, get_console_theme


@pytest.mark.unit
class TestThemeColors:
    """Test theme color definitions and application."""

    def test_all_themes_have_conversation_colors(self):
        """Verify all themes define user_message and assistant_message colors."""
        for theme_name, theme in THEMES.items():
            assert hasattr(theme.console, "user_message"), (
                f"{theme_name} missing user_message color"
            )
            assert hasattr(theme.console, "assistant_message"), (
                f"{theme_name} missing assistant_message color"
            )
            assert theme.console.user_message, f"{theme_name} has empty user_message color"
            assert theme.console.assistant_message, (
                f"{theme_name} has empty assistant_message color"
            )

    def test_all_themes_have_info_color(self):
        """Verify all themes define info color for status messages."""
        for theme_name, theme in THEMES.items():
            assert hasattr(theme.console, "info"), f"{theme_name} missing info color"
            assert theme.console.info, f"{theme_name} has empty info color"

    def test_light_themes_use_appropriate_colors(self):
        """Verify light themes use darker colors for readability."""
        light_themes = [name for name, theme in THEMES.items() if not theme.is_dark]

        for theme_name in light_themes:
            theme = THEMES[theme_name]
            # Light themes should not use 'bright_' colors for main text
            assert not theme.console.user_message.startswith("bright_"), (
                f"{theme_name} uses bright color for user messages on light background"
            )
            assert not theme.console.assistant_message.startswith("bright_"), (
                f"{theme_name} uses bright color for assistant messages on light background"
            )

    def test_high_contrast_themes_use_bold(self):
        """Verify high contrast themes use bold text where appropriate."""
        high_contrast_themes = [name for name, theme in THEMES.items() if theme.high_contrast]

        for theme_name in high_contrast_themes:
            theme = THEMES[theme_name]
            # High contrast themes should use bold for emphasis
            assert (
                "bold" in theme.console.user_message or "bold" in theme.console.assistant_message
            ), f"{theme_name} high contrast theme doesn't use bold for messages"

    def test_theme_color_inheritance(self):
        """Test that ConsoleTheme properly inherits default values."""
        # Create a minimal theme
        minimal_console = ConsoleTheme()

        # Check default values are set
        assert minimal_console.success == "green"
        assert minimal_console.error == "red"
        assert minimal_console.warning == "yellow"
        assert minimal_console.info == "cyan"
        assert minimal_console.user_message == "bright_blue"
        assert minimal_console.assistant_message == "bright_green"

    def test_theme_colors_are_valid(self):
        """Test that all theme colors are valid Rich color strings."""
        from coda.themes import is_valid_color

        for theme_name, theme in THEMES.items():
            # Check console theme colors
            for attr_name in [
                "success",
                "error",
                "warning",
                "info",
                "user_message",
                "assistant_message",
            ]:
                color = getattr(theme.console, attr_name)
                assert is_valid_color(color), (
                    f"{theme_name}.console.{attr_name} has invalid color: {color}"
                )

    def test_get_console_theme_returns_current_theme(self):
        """Test that get_console_theme returns the current theme's console."""
        with patch("coda.themes.get_theme_manager") as mock_get_manager:
            # Mock theme manager
            mock_manager = Mock()
            mock_theme = Mock()
            mock_theme.console = ConsoleTheme(
                user_message="test_blue", assistant_message="test_green"
            )
            mock_manager.get_console_theme.return_value = mock_theme.console
            mock_get_manager.return_value = mock_manager

            # Get console theme
            console_theme = get_console_theme()

            # Verify it returns the current theme's console
            assert console_theme.user_message == "test_blue"
            assert console_theme.assistant_message == "test_green"

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_theme_colors_different_from_default(self, theme_name):
        """Test that each theme has some unique colors (not all default)."""
        if theme_name == "default":
            return  # Skip default theme

        theme = THEMES[theme_name]
        default_theme = THEMES["default"]

        # At least one color should be different from default
        differences = 0
        for attr in ["info", "user_message", "assistant_message", "panel_border"]:
            if getattr(theme.console, attr) != getattr(default_theme.console, attr):
                differences += 1

        assert differences > 0, f"{theme_name} has no color differences from default theme"

    def test_theme_message_colors_contrast(self):
        """Test that user and assistant message colors are different within each theme."""
        for theme_name, theme in THEMES.items():
            # Skip minimal theme which intentionally uses monochrome
            if theme_name == "minimal":
                continue

            # Remove style modifiers for comparison
            user_base = theme.console.user_message.split()[0]
            assistant_base = theme.console.assistant_message.split()[0]

            assert user_base != assistant_base, (
                f"{theme_name} uses same base color for user and assistant messages"
            )
