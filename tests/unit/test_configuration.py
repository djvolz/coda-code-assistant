"""Unit tests for configuration enhancements."""

import os
from unittest.mock import patch

import pytest

from coda.configuration import CodaConfig, ConfigManager


class TestCodaConfigEnhancements:
    """Test the CodaConfig dataclass enhancements."""

    def test_observability_field_exists(self):
        """Test that observability field exists in CodaConfig."""
        config = CodaConfig()
        assert hasattr(config, "observability")
        assert config.observability == {}

    def test_merge_with_observability(self):
        """Test merging configurations with observability settings."""
        config1 = CodaConfig(observability={"enabled": True, "metrics": {"enabled": True}})
        config2 = CodaConfig(
            observability={"tracing": {"enabled": True}, "metrics": {"interval": 60}}
        )

        merged = config1.merge(config2)

        assert merged.observability["enabled"] is True
        assert merged.observability["metrics"]["enabled"] is True
        assert merged.observability["metrics"]["interval"] == 60
        assert merged.observability["tracing"]["enabled"] is True

    def test_merge_preserves_other_fields(self):
        """Test that merge preserves other configuration fields."""
        config1 = CodaConfig(default_persona="test_persona", observability={"enabled": True})
        config2 = CodaConfig(observability={"metrics": {"enabled": True}})

        merged = config1.merge(config2)

        assert merged.default_persona == "test_persona"
        assert merged.observability["enabled"] is True
        assert merged.observability["metrics"]["enabled"] is True


class TestConfigManagerEnhancements:
    """Test the ConfigManager enhancements."""

    @pytest.fixture
    def config_manager(self):
        """Create a ConfigManager instance with test configuration."""
        manager = ConfigManager()
        manager._config = {
            "observability": {
                "enabled": True,
                "metrics": {"enabled": True, "interval": 60, "max_events": 1000},
                "tracing": {"enabled": False, "sampling_rate": 0.1},
            },
            "other_setting": "value",
            "nested": {"deep": {"value": "test"}},
        }
        return manager

    def test_get_bool_basic(self, config_manager):
        """Test get_bool with basic values."""
        assert config_manager.get_bool("observability.enabled") is True
        assert config_manager.get_bool("observability.metrics.enabled") is True
        assert config_manager.get_bool("observability.tracing.enabled") is False

    def test_get_bool_with_default(self, config_manager):
        """Test get_bool with default values."""
        assert config_manager.get_bool("nonexistent.key", default=True) is True
        assert config_manager.get_bool("nonexistent.key", default=False) is False

    def test_get_bool_with_env_override(self, config_manager):
        """Test get_bool with environment variable override."""
        with patch.dict(os.environ, {"CODA_OBSERVABILITY_ENABLED": "false"}):
            assert config_manager.get_bool("observability.enabled") is False

        with patch.dict(os.environ, {"CODA_OBSERVABILITY_METRICS_ENABLED": "true"}):
            assert config_manager.get_bool("observability.metrics.enabled") is True

    def test_get_bool_type_conversion(self, config_manager):
        """Test get_bool type conversion."""
        config_manager._config["string_bool"] = "true"
        config_manager._config["int_bool"] = 1
        config_manager._config["zero_bool"] = 0

        assert config_manager.get_bool("string_bool") is True
        assert config_manager.get_bool("int_bool") is True
        assert config_manager.get_bool("zero_bool") is False

    def test_get_int_basic(self, config_manager):
        """Test get_int with basic values."""
        assert config_manager.get_int("observability.metrics.interval") == 60
        assert config_manager.get_int("observability.metrics.max_events") == 1000

    def test_get_int_with_default(self, config_manager):
        """Test get_int with default values."""
        assert config_manager.get_int("nonexistent.key", default=42) == 42

    def test_get_int_with_env_override(self, config_manager):
        """Test get_int with environment variable override."""
        with patch.dict(os.environ, {"CODA_OBSERVABILITY_METRICS_INTERVAL": "120"}):
            assert config_manager.get_int("observability.metrics.interval") == 120

    def test_get_int_type_conversion(self, config_manager):
        """Test get_int type conversion."""
        config_manager._config["string_int"] = "123"
        config_manager._config["float_int"] = 123.7

        assert config_manager.get_int("string_int") == 123
        assert config_manager.get_int("float_int") == 123

    def test_get_int_invalid_conversion(self, config_manager):
        """Test get_int with invalid conversion."""
        config_manager._config["invalid_int"] = "not_a_number"

        assert config_manager.get_int("invalid_int", default=0) == 0

    def test_get_float_basic(self, config_manager):
        """Test get_float with basic values."""
        assert config_manager.get_float("observability.tracing.sampling_rate") == 0.1

    def test_get_float_with_default(self, config_manager):
        """Test get_float with default values."""
        assert config_manager.get_float("nonexistent.key", default=3.14) == 3.14

    def test_get_float_with_env_override(self, config_manager):
        """Test get_float with environment variable override."""
        with patch.dict(os.environ, {"CODA_OBSERVABILITY_TRACING_SAMPLING_RATE": "0.5"}):
            assert config_manager.get_float("observability.tracing.sampling_rate") == 0.5

    def test_get_float_type_conversion(self, config_manager):
        """Test get_float type conversion."""
        config_manager._config["string_float"] = "3.14"
        config_manager._config["int_float"] = 42

        assert config_manager.get_float("string_float") == 3.14
        assert config_manager.get_float("int_float") == 42.0

    def test_get_string_basic(self, config_manager):
        """Test get_string with basic values."""
        assert config_manager.get_string("other_setting") == "value"
        assert config_manager.get_string("nested.deep.value") == "test"

    def test_get_string_with_default(self, config_manager):
        """Test get_string with default values."""
        assert config_manager.get_string("nonexistent.key", default="default") == "default"

    def test_get_string_with_env_override(self, config_manager):
        """Test get_string with environment variable override."""
        with patch.dict(os.environ, {"CODA_OTHER_SETTING": "env_value"}):
            assert config_manager.get_string("other_setting") == "env_value"

    def test_get_string_type_conversion(self, config_manager):
        """Test get_string type conversion."""
        config_manager._config["bool_string"] = True
        config_manager._config["int_string"] = 123

        assert config_manager.get_string("bool_string") == "True"
        assert config_manager.get_string("int_string") == "123"

    def test_get_config(self, config_manager):
        """Test get_config returns full configuration."""
        config = config_manager.get_config()

        assert isinstance(config, dict)
        assert "observability" in config
        assert config["observability"]["enabled"] is True

    def test_get_nested_value_basic(self, config_manager):
        """Test _get_nested_value with basic paths."""
        assert config_manager._get_nested_value("observability.enabled") is True
        assert config_manager._get_nested_value("observability.metrics.interval") == 60
        assert config_manager._get_nested_value("nested.deep.value") == "test"

    def test_get_nested_value_missing(self, config_manager):
        """Test _get_nested_value with missing paths."""
        assert config_manager._get_nested_value("nonexistent") is None
        assert config_manager._get_nested_value("observability.nonexistent") is None
        assert config_manager._get_nested_value("nested.deep.nonexistent") is None

    def test_get_nested_value_none_config(self):
        """Test _get_nested_value with None config."""
        manager = ConfigManager()
        manager._config = None

        assert manager._get_nested_value("any.key") is None

    def test_env_var_name_generation(self, config_manager):
        """Test environment variable name generation."""
        test_cases = [
            ("observability.enabled", "CODA_OBSERVABILITY_ENABLED"),
            ("observability.metrics.enabled", "CODA_OBSERVABILITY_METRICS_ENABLED"),
            ("some.nested.key.path", "CODA_SOME_NESTED_KEY_PATH"),
        ]

        for key, expected_env_var in test_cases:
            # Test by setting env var and checking it's used
            with patch.dict(os.environ, {expected_env_var: "test_value"}):
                result = config_manager.get_string(key)
                assert result == "test_value"

    def test_type_safety(self, config_manager):
        """Test type safety of configuration methods."""
        # Set various types
        config_manager._config["test"] = {
            "bool": True,
            "int": 42,
            "float": 3.14,
            "string": "hello",
            "none": None,
        }

        # get_bool should handle all types
        assert config_manager.get_bool("test.bool") is True
        assert config_manager.get_bool("test.int") is True
        assert config_manager.get_bool("test.float") is True
        assert config_manager.get_bool("test.string", default=False) is False
        assert config_manager.get_bool("test.none", default=False) is False

        # get_int should handle numeric types
        assert config_manager.get_int("test.int") == 42
        assert config_manager.get_int("test.float") == 3
        assert config_manager.get_int("test.string", default=0) == 0
        assert config_manager.get_int("test.none", default=0) == 0

        # get_float should handle numeric types
        assert config_manager.get_float("test.int") == 42.0
        assert config_manager.get_float("test.float") == 3.14
        assert config_manager.get_float("test.string", default=0.0) == 0.0
        assert config_manager.get_float("test.none", default=0.0) == 0.0

        # get_string should handle all types
        assert config_manager.get_string("test.bool") == "True"
        assert config_manager.get_string("test.int") == "42"
        assert config_manager.get_string("test.float") == "3.14"
        assert config_manager.get_string("test.string") == "hello"
        assert config_manager.get_string("test.none", default="") == ""

    def test_empty_key(self, config_manager):
        """Test handling of empty keys."""
        assert config_manager.get_bool("", default=False) is False
        assert config_manager.get_int("", default=0) == 0
        assert config_manager.get_float("", default=0.0) == 0.0
        assert config_manager.get_string("", default="") == ""

    def test_complex_nested_structure(self, config_manager):
        """Test with complex nested configuration."""
        config_manager._config = {
            "level1": {"level2": {"level3": {"level4": {"value": "deep_value", "number": 42}}}}
        }

        assert config_manager.get_string("level1.level2.level3.level4.value") == "deep_value"
        assert config_manager.get_int("level1.level2.level3.level4.number") == 42
