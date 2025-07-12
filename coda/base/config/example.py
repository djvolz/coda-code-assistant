#!/usr/bin/env python3
"""Standalone example showing the config module works without other Coda modules.

This example demonstrates that the config module:
1. Has zero external dependencies
2. Can be used in any project
3. Provides flexible configuration management

When using this module standalone:
- Copy the entire config directory to your project
- Import directly: from config import Config, ConfigManager
- Or run this example: python example.py
"""

import json
import os
import tempfile
from pathlib import Path

# Standalone imports - use these when copying this module to another project
try:
    # When running as standalone module
    from manager import Config, ConfigManager
    from models import ConfigFormat, ConfigPath
except ImportError:
    # When running from coda package
    from coda.base.config import Config, ConfigManager
    from coda.base.config.models import ConfigFormat, ConfigPath


def main():
    """Demonstrate usage of the config module."""
    print("=== Coda Config Module Demo ===\n")

    # Create a temporary directory for our demo
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)

        # 1. Basic usage with defaults
        print("1. Basic Configuration with Defaults:")
        config = Config(
            app_name="demo",
            defaults={
                "debug": False,
                "server": {"host": "localhost", "port": 8080},
                "database": {"name": "mydb", "pool_size": 10},
            },
        )

        print(f"  Debug mode: {config.get_bool('debug')}")
        print(f"  Server host: {config.get_string('server.host')}")
        print(f"  Server port: {config.get_int('server.port')}")
        print(f"  DB pool size: {config.get_int('database.pool_size')}")
        print()

        # 2. Create and load a config file
        print("2. Loading from Config File:")
        config_file = config_dir / "config.json"
        config_data = {
            "debug": True,
            "server": {"host": "0.0.0.0", "port": 9000, "workers": 4},
            "features": {"auth": True, "api": True, "ui": False},
        }
        config_file.write_text(json.dumps(config_data, indent=2))

        config = Config(app_name="demo", config_file=str(config_file))
        print(f"  Debug mode: {config.get_bool('debug')}")
        print(f"  Server: {config.get_string('server.host')}:{config.get_int('server.port')}")
        print(f"  Workers: {config.get_int('server.workers')}")
        print(f"  Features: {config.get_dict('features')}")
        print()

        # 3. Environment variable override
        print("3. Environment Variable Override:")
        os.environ["DEMO_SERVER_PORT"] = "3000"
        os.environ["DEMO_DEBUG"] = "false"
        os.environ["DEMO_FEATURES_UI"] = "true"

        config = Config(app_name="demo", config_file=str(config_file), env_prefix="DEMO_")
        print(f"  Debug mode: {config.get_bool('debug')} (overridden by env)")
        print(f"  Server port: {config.get_int('server.port')} (overridden by env)")
        print(f"  UI enabled: {config.get_bool('features.ui')} (overridden by env)")
        print()

        # 4. Runtime configuration changes
        print("4. Runtime Configuration:")
        config.set("server.timeout", 30)
        config.set("features.experimental", True)
        print(f"  Server timeout: {config.get_int('server.timeout')} (set at runtime)")
        print(f"  Experimental: {config.get_bool('features.experimental')} (set at runtime)")
        print()

        # 5. Working with lists and complex types
        print("5. Complex Configuration Types:")
        config.set("allowed_hosts", ["localhost", "127.0.0.1", "example.com"])
        config.set("cors.origins", "http://localhost:3000,https://example.com")
        config.set("database.options", {"ssl": True, "timeout": 5000})

        print(f"  Allowed hosts: {config.get_list('allowed_hosts')}")
        print(f"  CORS origins: {config.get_list('cors.origins')}")
        print(f"  DB options: {config.get_dict('database.options')}")
        print()

        # 6. Saving configuration
        print("6. Saving Configuration:")
        save_path = config_dir / "saved_config.json"
        config.save(save_path, ConfigFormat.JSON)
        print(f"  Saved to: {save_path}")
        print(f"  File exists: {save_path.exists()}")
        print()

        # 7. Advanced: Multiple config sources
        print("7. Multiple Configuration Sources:")
        # Create system config
        system_config = config_dir / "system.toml"
        system_config.write_text(
            """
debug = false
[server]
host = "0.0.0.0"
port = 80
"""
        )

        # Create user config
        user_config = config_dir / "user.json"
        user_config.write_text('{"debug": true, "server": {"port": 8080}}')

        # Load with multiple sources
        config_manager = ConfigManager(
            app_name="demo",
            config_paths=[
                ConfigPath(system_config, ConfigFormat.TOML),
                ConfigPath(user_config, ConfigFormat.JSON),
            ],
            env_prefix="DEMO_",
        )

        print("  Config layer priority (lowest to highest):")
        print("    - system.toml: port=80, debug=false")
        print("    - user.json: port=8080, debug=true")
        print(
            f"    - Result: port={config_manager.get_int('server.port')}, debug={config_manager.get_bool('debug')}"
        )
        print()

        # 8. Type safety and defaults
        print("8. Type Safety and Defaults:")
        print(f"  Missing key with default: {config.get_string('missing.key', 'default value')}")
        print(f"  Wrong type with conversion: {config.get_int('debug', 999)}")  # bool -> int
        print(f"  Safe dict access: {config.get_dict('nonexistent.section')}")  # Returns {}
        print()

    # Clean up environment
    for key in list(os.environ.keys()):
        if key.startswith("DEMO_"):
            del os.environ[key]

    print("✓ Config module works standalone!")
    print("✓ Zero external dependencies")
    print("✓ Can be copy-pasted to any project")
    print("✓ Supports files, environment, and runtime config")


if __name__ == "__main__":
    main()
