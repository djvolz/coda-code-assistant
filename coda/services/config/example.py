"""Example usage of the configuration service."""

from pathlib import Path

from coda.services.config import ConfigService, get_config_service


def basic_usage():
    """Show basic configuration service usage."""
    print("Basic Configuration Service Usage")
    print("=" * 40)

    # Get the global instance
    config = get_config_service()

    # Access configuration values
    print(f"Default provider: {config.default_provider}")
    print(f"Debug mode: {config.debug}")
    print(f"Temperature: {config.temperature}")
    print(f"Max tokens: {config.max_tokens}")

    # Get provider-specific config
    oci_config = config.get_provider_config("oci_genai")
    print(f"OCI config: {oci_config}")

    # Access directories
    print(f"\nData directory: {config.get_data_dir()}")
    print(f"Cache directory: {config.get_cache_dir()}")
    print(f"Session DB: {config.get_session_db_path()}")
    print(f"History file: {config.get_history_file_path()}")

    # Access theme
    print(f"\nCurrent theme: {config.theme_manager.current_theme_name}")
    print(f"Available themes: {', '.join(config.theme_manager.list_themes())}")


def custom_config_path():
    """Show usage with custom config path."""
    print("\n\nCustom Configuration Path")
    print("=" * 40)

    # Create service with custom config path
    custom_path = Path("/tmp/coda-config.toml")
    config = ConfigService(config_path=custom_path)

    # Set some values
    config.set("myapp.setting1", "value1")
    config.set("myapp.setting2", 42)
    config.set("myapp.enabled", True)

    # Save
    config.save()
    print(f"Saved configuration to: {custom_path}")

    # Read back
    print(f"myapp.setting1: {config.get_string('myapp.setting1')}")
    print(f"myapp.setting2: {config.get_int('myapp.setting2')}")
    print(f"myapp.enabled: {config.get_bool('myapp.enabled')}")


def environment_overrides():
    """Show environment variable overrides."""
    print("\n\nEnvironment Variable Overrides")
    print("=" * 40)

    # Set some environment variables
    import os

    os.environ["CODA_DEFAULT_PROVIDER"] = "ollama"
    os.environ["CODA_DEBUG"] = "true"

    # Get config - environment variables take precedence
    config = ConfigService()

    print(f"Default provider: {config.default_provider}")  # Will be "ollama"
    print(f"Debug mode: {config.debug}")  # Will be True

    # Clean up
    del os.environ["CODA_DEFAULT_PROVIDER"]
    del os.environ["CODA_DEBUG"]


def theme_integration():
    """Show theme integration."""
    print("\n\nTheme Integration")
    print("=" * 40)

    config = get_config_service()

    # Current theme
    print(f"Current theme: {config.theme_manager.current_theme_name}")

    # Change theme
    config.theme_manager.set_theme("dark")
    print(f"Changed to: {config.theme_manager.current_theme_name}")

    # Save theme preference
    config.set("ui.theme", "dark")
    config.save()
    print("Theme preference saved to config")

    # Get console with theme applied
    console = config.theme_manager.get_console()
    console.print("[success]Success message with theme[/success]")


if __name__ == "__main__":
    basic_usage()
    custom_config_path()
    environment_overrides()
    theme_integration()
