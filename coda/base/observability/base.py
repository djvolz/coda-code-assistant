"""Base class for observability components."""

import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path

from coda.base.config.manager import Config as ConfigManager

from .scheduler import PeriodicTaskScheduler
from .storage import FileStorageBackend, StorageBackend

logger = logging.getLogger(__name__)


class ObservabilityComponent(ABC):
    """Base class for all observability components."""

    def __init__(
        self,
        export_directory: Path,
        config_manager: ConfigManager,
        storage_backend: StorageBackend | None = None,
        scheduler: PeriodicTaskScheduler | None = None,
    ):
        """Initialize the base observability component.

        Args:
            export_directory: Directory for exporting data
            config_manager: Configuration manager instance
            storage_backend: Optional storage backend (defaults to FileStorageBackend)
            scheduler: Optional shared scheduler (creates own timer if not provided)
        """
        self.export_directory = export_directory
        self.config_manager = config_manager
        self._lock = threading.RLock()
        self._running = False
        self._flush_timer: threading.Timer | None = None
        self._scheduler = scheduler
        self._use_shared_scheduler = scheduler is not None

        # Ensure export directory exists
        self.export_directory.mkdir(parents=True, exist_ok=True)

        # Initialize storage backend
        self.storage = storage_backend or FileStorageBackend(self.export_directory)

    @abstractmethod
    def _flush_data(self) -> None:
        """Flush component data to storage. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_component_name(self) -> str:
        """Return the component name for logging. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def get_flush_interval(self) -> int:
        """Return the flush interval in seconds. Must be implemented by subclasses."""
        pass

    def start(self) -> None:
        """Start the component with common initialization."""
        with self._lock:
            if self._running:
                logger.debug(f"{self.get_component_name()} already running")
                return

            self._running = True
            self._schedule_flush()
            logger.info(f"{self.get_component_name()} started")

    def stop(self) -> None:
        """Stop the component with common cleanup."""
        with self._lock:
            if not self._running:
                logger.debug(f"{self.get_component_name()} already stopped")
                return

            self._running = False

            # Cancel any pending flush
            if self._use_shared_scheduler and self._scheduler:
                task_name = f"{self.get_component_name()}_flush"
                self._scheduler.unschedule(task_name)
            elif self._flush_timer:
                self._flush_timer.cancel()
                self._flush_timer = None

            # Perform final flush
            try:
                self._flush_data()
            except Exception as e:
                logger.error(f"Error during final flush for {self.get_component_name()}: {e}")

            logger.info(f"{self.get_component_name()} stopped")

    def _schedule_flush(self) -> None:
        """Schedule the next periodic flush."""
        if not self._running:
            return

        interval = self.get_flush_interval()

        if self._use_shared_scheduler and self._scheduler:
            # Use shared scheduler
            task_name = f"{self.get_component_name()}_flush"
            self._scheduler.schedule(task_name, self._flush_with_error_handling, interval)
        else:
            # Use own timer
            def flush_and_reschedule():
                with self._lock:
                    if not self._running:
                        return

                    try:
                        self._flush_data()
                    except Exception as e:
                        logger.error(f"Error flushing {self.get_component_name()}: {e}")

                    # Reschedule next flush
                    self._schedule_flush()

            self._flush_timer = threading.Timer(interval, flush_and_reschedule)
            self._flush_timer.daemon = True
            self._flush_timer.start()

    def _flush_with_error_handling(self) -> None:
        """Flush data with error handling for scheduler use."""
        try:
            self._flush_data()
        except Exception as e:
            logger.error(f"Error flushing {self.get_component_name()}: {e}")

    def is_running(self) -> bool:
        """Check if the component is running."""
        with self._lock:
            return self._running

    def force_flush(self) -> None:
        """Force an immediate data flush."""
        with self._lock:
            if self._running:
                try:
                    self._flush_data()
                    logger.debug(f"Force flushed {self.get_component_name()}")
                except Exception as e:
                    logger.error(f"Error during force flush for {self.get_component_name()}: {e}")
