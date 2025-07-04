"""Unit tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from coda.configuration import CodaConfig, ConfigManager, get_config, get_provider_config


@pytest.mark.unit
class TestCodaConfig:
    """Test CodaConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CodaConfig()

        assert config.default_provider == "oci_genai"
        assert config.providers == {}
        assert config.debug is False
        assert config.session["autosave"] is True
        assert config.ui["theme"] == "default"

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "default_provider": "litellm",
            "providers": {"litellm": {"api_key": "test-key"}},
            "debug": True,
        }

        config = CodaConfig.from_dict(data)

        assert config.default_provider == "litellm"
        assert config.providers["litellm"]["api_key"] == "test-key"
        assert config.debug is True

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = CodaConfig(
            default_provider="ollama",
            debug=True,
        )

        data = config.to_dict()

        assert data["default_provider"] == "ollama"
        assert data["debug"] is True
        assert "providers" in data
        assert "session" in data
        assert "ui" in data

    def test_merge(self):
        """Test merging configurations."""
        config = CodaConfig()

        # Merge new values
        config.merge(
            {
                "default_provider": "litellm",
                "providers": {
                    "litellm": {"api_key": "key1"},
                    "ollama": {"host": "localhost"},
                },
                "debug": True,
            }
        )

        assert config.default_provider == "litellm"
        assert config.providers["litellm"]["api_key"] == "key1"
        assert config.providers["ollama"]["host"] == "localhost"
        assert config.debug is True

        # Merge should update existing values
        config.merge(
            {
                "providers": {
                    "litellm": {"api_key": "key2", "model": "gpt-4"},
                }
            }
        )

        assert config.providers["litellm"]["api_key"] == "key2"
        assert config.providers["litellm"]["model"] == "gpt-4"
        assert config.providers["ollama"]["host"] == "localhost"  # Unchanged


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager class."""

    def test_env_var_override(self, monkeypatch):
        """Test environment variable overrides."""
        # Set environment variables
        monkeypatch.setenv("CODA_DEFAULT_PROVIDER", "ollama")
        monkeypatch.setenv("CODA_DEBUG", "true")
        monkeypatch.setenv("OCI_COMPARTMENT_ID", "test-compartment")

        # Create new config manager
        manager = ConfigManager()
        config = manager.config

        assert config.default_provider == "ollama"
        assert config.debug is True
        assert config.providers["oci_genai"]["compartment_id"] == "test-compartment"

    def test_get_provider_config(self):
        """Test getting provider-specific config."""
        manager = ConfigManager()
        manager.config.providers = {
            "litellm": {"api_key": "test-key"},
            "ollama": {"host": "localhost"},
        }

        assert manager.get_provider_config("litellm") == {"api_key": "test-key"}
        assert manager.get_provider_config("ollama") == {"host": "localhost"}
        assert manager.get_provider_config("nonexistent") == {}

    @pytest.mark.skipif(
        not hasattr(tempfile, "TemporaryDirectory"), reason="Requires TemporaryDirectory"
    )
    def test_load_config_file(self, monkeypatch):
        """Test loading configuration from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_dir = Path(tmpdir) / ".config" / "coda"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.toml"

            # Write test config
            config_file.write_text(
                """
default_provider = "litellm"
debug = true

[providers.litellm]
api_key = "test-key-from-file"

[ui]
theme = "dark"
"""
            )

            # Mock home directory
            monkeypatch.setenv("XDG_CONFIG_HOME", str(Path(tmpdir) / ".config"))

            # Create config manager
            manager = ConfigManager()
            config = manager.config

            assert config.default_provider == "litellm"
            assert config.debug is True
            assert config.providers["litellm"]["api_key"] == "test-key-from-file"
            assert config.ui["theme"] == "dark"


@pytest.mark.unit
class TestGlobalConfig:
    """Test global config functions."""

    def test_get_config(self):
        """Test getting global config."""
        config1 = get_config()
        config2 = get_config()

        # Should return same instance
        assert config1 is config2
        assert isinstance(config1, CodaConfig)

    def test_get_provider_config(self):
        """Test getting provider config from global."""
        # Set up some test config
        config = get_config()
        config.providers["test_provider"] = {"key": "value"}

        # Get provider config
        provider_config = get_provider_config("test_provider")
        assert provider_config == {"key": "value"}

        # Non-existent provider
        assert get_provider_config("nonexistent") == {}
