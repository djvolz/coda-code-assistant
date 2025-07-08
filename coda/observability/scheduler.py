"""Centralized scheduler for periodic observability tasks.

This module provides a unified scheduling mechanism to reduce thread
proliferation and improve resource management.
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """Represents a scheduled periodic task."""

    name: str
    func: Callable[[], None]
    interval: float
    last_run: datetime | None = None
    next_run: datetime | None = None
    running: bool = False
    enabled: bool = True
    error_count: int = 0

    def should_run(self, current_time: datetime) -> bool:
        """Check if the task should run based on current time."""
        if not self.enabled or self.running:
            return False

        if self.next_run is None:
            return True

        return current_time >= self.next_run

    def update_next_run(self, current_time: datetime) -> None:
        """Update the next run time based on interval."""
        from datetime import timedelta

        self.last_run = current_time
        self.next_run = current_time + timedelta(seconds=self.interval)


class PeriodicTaskScheduler:
    """Centralized scheduler for periodic tasks."""

    def __init__(self, max_workers: int = 2, tick_interval: float = 1.0):
        """Initialize the scheduler.

        Args:
            max_workers: Maximum number of concurrent task workers
            tick_interval: How often to check for tasks to run (seconds)
        """
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="observability-scheduler-"
        )
        self.tick_interval = tick_interval
        self.tasks: dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._running = False
        self._scheduler_thread: threading.Thread | None = None

    def schedule(self, name: str, func: Callable[[], None], interval: float) -> None:
        """Schedule a periodic task.

        Args:
            name: Unique name for the task
            func: Function to execute periodically
            interval: Interval between executions in seconds
        """
        with self._lock:
            if name in self.tasks:
                # Update existing task
                task = self.tasks[name]
                task.func = func
                task.interval = interval
                task.enabled = True
                logger.debug(f"Updated scheduled task: {name}")
            else:
                # Create new task
                self.tasks[name] = ScheduledTask(name=name, func=func, interval=interval)
                logger.debug(f"Scheduled new task: {name} (interval: {interval}s)")

    def unschedule(self, name: str) -> None:
        """Remove a scheduled task.

        Args:
            name: Name of the task to remove
        """
        with self._lock:
            if name in self.tasks:
                del self.tasks[name]
                logger.debug(f"Unscheduled task: {name}")

    def enable_task(self, name: str) -> None:
        """Enable a scheduled task."""
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = True

    def disable_task(self, name: str) -> None:
        """Disable a scheduled task without removing it."""
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = False

    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return

            self._running = True
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop, name="observability-scheduler-main", daemon=True
            )
            self._scheduler_thread.start()
            logger.info("Periodic task scheduler started")

    def stop(self, wait: bool = True, timeout: float = 10.0) -> None:
        """Stop the scheduler.

        Args:
            wait: Whether to wait for running tasks to complete
            timeout: Maximum time to wait for shutdown
        """
        with self._lock:
            if not self._running:
                return

            self._running = False

        # Wait for scheduler thread to finish
        if self._scheduler_thread and wait:
            self._scheduler_thread.join(timeout=timeout)

        # Shutdown executor
        # Note: timeout parameter is only available in Python 3.9+
        try:
            self.executor.shutdown(wait=wait, timeout=timeout)
        except TypeError:
            # Fallback for older Python versions
            self.executor.shutdown(wait=wait)
        logger.info("Periodic task scheduler stopped")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks and runs tasks."""
        logger.debug("Scheduler loop started")

        while self._running:
            try:
                current_time = datetime.now()
                tasks_to_run = []

                # Check which tasks need to run
                with self._lock:
                    for task in self.tasks.values():
                        if task.should_run(current_time):
                            task.running = True
                            task.update_next_run(current_time)
                            tasks_to_run.append(task)

                # Submit tasks to executor
                for task in tasks_to_run:
                    self.executor.submit(self._run_task, task)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

            # Sleep until next tick
            time.sleep(self.tick_interval)

        logger.debug("Scheduler loop stopped")

    def _run_task(self, task: ScheduledTask) -> None:
        """Run a single task with error handling."""
        try:
            logger.debug(f"Running task: {task.name}")
            start_time = time.time()

            task.func()

            duration = time.time() - start_time
            logger.debug(f"Task {task.name} completed in {duration:.2f}s")

            # Reset error count on success
            with self._lock:
                task.error_count = 0

        except Exception as e:
            logger.error(f"Error running task {task.name}: {e}")

            with self._lock:
                task.error_count += 1

                # Disable task after too many errors
                if task.error_count >= 5:
                    task.enabled = False
                    logger.error(f"Task {task.name} disabled after {task.error_count} errors")

        finally:
            with self._lock:
                task.running = False

    def get_status(self) -> dict[str, Any]:
        """Get current scheduler status."""
        with self._lock:
            task_statuses = {}

            for name, task in self.tasks.items():
                task_statuses[name] = {
                    "enabled": task.enabled,
                    "running": task.running,
                    "interval": task.interval,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "error_count": task.error_count,
                }

            return {
                "running": self._running,
                "tick_interval": self.tick_interval,
                "task_count": len(self.tasks),
                "tasks": task_statuses,
            }

    def force_run(self, name: str) -> bool:
        """Force immediate execution of a task.

        Args:
            name: Name of the task to run

        Returns:
            True if task was submitted, False if not found or already running
        """
        with self._lock:
            if name not in self.tasks:
                logger.warning(f"Task not found: {name}")
                return False

            task = self.tasks[name]
            if task.running:
                logger.warning(f"Task already running: {name}")
                return False

            task.running = True

        # Submit task to executor
        self.executor.submit(self._run_task, task)
        return True
