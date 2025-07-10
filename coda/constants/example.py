#!/usr/bin/env python3
"""Standalone example showing the constants module works without other Coda modules.

This example demonstrates that the constants module:
1. Has zero external dependencies
2. Can be used in any project
3. Provides organized, type-safe constants

Run with: python -m coda.constants.example
Or if copy-pasted: python example.py
"""

# If this module is copy-pasted to another project, change this import to:
# from constants import UI, API, DEFAULTS, PROVIDERS, THEMES, MODES
try:
    from coda.constants import (
        API,
        APP,
        DEFAULTS,
        ENV,
        ERRORS,
        EXPORT,
        FILES,
        MODES,
        PROVIDERS,
        THEMES,
        UI,
    )
    from coda.constants.models import (
        DeveloperMode,
        ProviderType,
        ThemeType,
    )
except ImportError:
    # If running as standalone after copy-paste
    from definitions import (
        API,
        APP,
        DEFAULTS,
        ENV,
        ERRORS,
        EXPORT,
        FILES,
        MODES,
        PROVIDERS,
        THEMES,
        UI,
    )
    from models import (
        DeveloperMode,
        ProviderType,
        ThemeType,
    )


def main():
    """Demonstrate usage of the constants module."""
    print("=== Coda Constants Module Demo ===\n")

    # Application metadata
    print(f"Application: {APP.DISPLAY_NAME} (internal name: {APP.NAME})")
    print()

    # UI constants
    print("UI Configuration:")
    print(f"  Max line length: {UI.MAX_LINE_LENGTH}")
    print(f"  Console width: {UI.CONSOLE_WIDTH_DEFAULT}")
    print(f"  Max models to display: {UI.MAX_MODELS_DISPLAY}")
    print()

    # API constants
    print("API Configuration:")
    print(f"  Cache duration: {API.MODEL_CACHE_DURATION // 3600} hours")
    print("  Context ratios:")
    print(f"    Aggressive: {API.CONTEXT_AGGRESSIVE_RATIO}")
    print(f"    Balanced: {API.CONTEXT_BALANCED_RATIO}")
    print(f"    Conservative: {API.CONTEXT_CONSERVATIVE_RATIO}")
    print()

    # Default values
    print("Default Settings:")
    print(f"  Provider: {DEFAULTS.PROVIDER}")
    print(f"  Mode: {DEFAULTS.MODE}")
    print(f"  Temperature: {DEFAULTS.TEMPERATURE}")
    print(f"  Theme: {DEFAULTS.THEME}")
    print()

    # Available options
    print(f"Available Providers: {', '.join(PROVIDERS.ALL)}")
    print(f"Available Themes: {', '.join(THEMES.ALL[:5])}...")
    print(f"Available Modes: {', '.join(MODES.ALL)}")
    print(f"Export Formats: {', '.join(EXPORT.ALL)}")
    print()

    # Using enums
    print("Using Enums:")
    print(f"  Provider enum: {ProviderType.OCI_GENAI.value}")
    print(f"  Theme enum: {ThemeType.DARK.value}")
    print(f"  Mode enum: {DeveloperMode.CODE.value}")
    print()

    # File system constants
    print("File System:")
    print(f"  Config file: {FILES.CONFIG_FILE}")
    print(f"  Config dir: {FILES.CONFIG_DIR}")
    print(f"  Project config: {FILES.PROJECT_CONFIG_DIR}")
    print()

    # Environment variables
    print("Environment Variables:")
    print(f"  Debug: {ENV.DEBUG}")
    print(f"  Default provider: {ENV.DEFAULT_PROVIDER}")
    print(f"  All vars use prefix: {ENV.PREFIX}")
    print()

    # Error messages
    print("Error Templates:")
    print(f"  Provider not found: {ERRORS.PROVIDER_NOT_FOUND.format(provider='test')}")
    print(f"  Model not found: {ERRORS.MODEL_NOT_FOUND.format(model='gpt-test')}")
    print()

    # Demonstrating immutability
    print("Constants are immutable:")
    try:
        UI.MAX_LINE_LENGTH = 100
    except AttributeError as e:
        print(f"  ✓ {e}")

    print("\n✓ Constants module works standalone!")
    print("✓ Zero external dependencies")
    print("✓ Can be copy-pasted to any project")


if __name__ == "__main__":
    main()
