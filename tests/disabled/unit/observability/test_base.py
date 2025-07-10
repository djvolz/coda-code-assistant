"""Unit tests for observability base component."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from coda.configuration import ConfigManager
from coda.observability.base import ObservabilityComponent
from coda.observability.storage import FileStorageBackend


class TestObservabilityComponent:
    """Test the base ObservabilityComponent class."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager."""
        config_manager = Mock(spec=ConfigManager)
        config_manager.get_config.return_value = {}
        return config_manager

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_component_initialization(self, temp_dir, config_manager):
        """Test component initialization with file storage."""

        class TestComponent(ObservabilityComponent):
            def get_component_name(self) -> str:
                return "TestComponent"

            def get_flush_interval(self) -> int:
                return 60

            def _flush_data(self) -> None:
                pass

        component = TestComponent(temp_dir, config_manager)

        assert component.export_directory == temp_dir
        assert component.config_manager == config_manager
        assert isinstance(component.storage, FileStorageBackend)
        assert not component._running

    def test_component_with_custom_storage(self, temp_dir, config_manager):
        """Test component initialization with custom storage backend."""
        from coda.observability.storage import MemoryStorageBackend

        class TestComponent(ObservabilityComponent):
            def get_component_name(self) -> str:
                return "TestComponent"

            def get_flush_interval(self) -> int:
                return 60

            def _flush_data(self) -> None:
                pass

        custom_storage = MemoryStorageBackend()
        component = TestComponent(temp_dir, config_manager, storage_backend=custom_storage)

        assert component.storage == custom_storage
        assert isinstance(component.storage, MemoryStorageBackend)

    def test_flush_data_called(self, temp_dir, config_manager):
        """Test that flush_data is called when component stops."""
        flush_called = False

        class TestComponent(ObservabilityComponent):
            def get_component_name(self) -> str:
                return "TestComponent"

            def get_flush_interval(self) -> int:
                return 60

            def _flush_data(self) -> None:
                nonlocal flush_called
                flush_called = True

        component = TestComponent(temp_dir, config_manager)
        component.start()
        component.stop()  # Stop should trigger a flush

        assert flush_called

    def test_stop_method(self, temp_dir, config_manager):
        """Test component stop method."""

        class TestComponent(ObservabilityComponent):
            def get_component_name(self) -> str:
                return "TestComponent"

            def get_flush_interval(self) -> int:
                return 60

            def _flush_data(self) -> None:
                pass

        component = TestComponent(temp_dir, config_manager)
        assert not component._running

        component.stop()
        assert not component._running  # After stop, should not be running

    def test_abstract_methods_must_be_implemented(self, temp_dir, config_manager):
        """Test that abstract methods must be implemented."""
        with pytest.raises(TypeError):
            # This should fail because abstract methods are not implemented
            ObservabilityComponent(temp_dir, config_manager)

    @pytest.mark.parametrize(
        "flush_interval,expected",
        [
            (30, 30),
            (60, 60),
            (300, 300),
        ],
    )
    def test_different_flush_intervals(self, temp_dir, config_manager, flush_interval, expected):
        """Test components with different flush intervals."""

        class TestComponent(ObservabilityComponent):
            def get_component_name(self) -> str:
                return "TestComponent"

            def get_flush_interval(self) -> int:
                return flush_interval

            def _flush_data(self) -> None:
                pass

        component = TestComponent(temp_dir, config_manager)
        assert component.get_flush_interval() == expected
