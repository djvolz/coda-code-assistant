"""Migration tool for converting old configuration to new format.

This script helps migrate from the old configuration.py/CodaConfig
to the new modular configuration system.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import old configuration
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from coda.base.config import Config
    from coda.configuration import get_config as get_old_config
except ImportError as e:
    print(f"Error importing configuration modules: {e}")
    sys.exit(1)


def migrate_configuration():
    """Migrate old configuration to new format."""
    print("Configuration Migration Tool")
    print("==========================")

    # Load old configuration
    print("\nLoading old configuration...")
    try:
        old_config = get_old_config()
        old_dict = old_config.to_dict()
        print(f"✓ Loaded configuration with {len(old_dict)} top-level keys")
    except Exception as e:
        print(f"✗ Failed to load old configuration: {e}")
        return False

    # Determine new config path
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        new_config_dir = Path(xdg_config_home) / "coda"
    else:
        new_config_dir = Path.home() / ".config" / "coda"

    new_config_path = new_config_dir / "config.toml"

    # Check if new config already exists
    if new_config_path.exists():
        print(f"\n⚠️  New configuration already exists at: {new_config_path}")
        response = input("Overwrite? (y/N): ").lower()
        if response != "y":
            print("Migration cancelled.")
            return False

    # Create new config directory
    new_config_dir.mkdir(parents=True, exist_ok=True)

    # Create new config instance
    print(f"\nCreating new configuration at: {new_config_path}")
    new_config = Config(config_path=new_config_path)

    # Migrate settings
    print("\nMigrating settings...")

    # Direct mappings
    direct_mappings = [
        "default_provider",
        "debug",
        "temperature",
        "max_tokens",
        "providers",
        "ui",
        "session",
        "observability",
        "web",
    ]

    for key in direct_mappings:
        if key in old_dict:
            new_config.set(key, old_dict[key])
            print(f"  ✓ Migrated {key}")

    # Save new configuration
    print("\nSaving new configuration...")
    try:
        new_config.save()
        print(f"✓ Configuration saved to: {new_config_path}")
    except Exception as e:
        print(f"✗ Failed to save configuration: {e}")
        return False

    # Show summary
    print("\n" + "=" * 50)
    print("Migration Summary")
    print("=" * 50)
    print("Old config format: CodaConfig dataclass")
    print(f"New config location: {new_config_path}")
    print(f"Settings migrated: {len([k for k in direct_mappings if k in old_dict])}")

    print("\nNext steps:")
    print("1. Review the migrated configuration")
    print("2. Update your code to use the new ConfigService:")
    print("   from coda.services.config import get_config_service")
    print("   config = get_config_service()")
    print("3. Remove old configuration.py imports")

    return True


if __name__ == "__main__":
    success = migrate_configuration()
    sys.exit(0 if success else 1)
