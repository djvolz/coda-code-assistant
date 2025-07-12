"""Unit tests for periodic task scheduler."""

import threading
import time
from unittest.mock import Mock

import pytest

from coda.observability.scheduler import PeriodicTaskScheduler


class TestPeriodicTaskScheduler:
    """Test the PeriodicTaskScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance."""
        scheduler = PeriodicTaskScheduler(max_workers=2)
        yield scheduler
        scheduler.stop(wait=True)

    def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = PeriodicTaskScheduler(max_workers=4)

        assert scheduler.max_workers == 4
        assert not scheduler._running
        assert len(scheduler._tasks) == 0
        assert scheduler._executor is None

        scheduler.stop()

    def test_schedule_task(self, scheduler):
        """Test scheduling a task."""
        mock_task = Mock()

        scheduler.schedule("test_task", mock_task, interval=1.0)

        assert "test_task" in scheduler._tasks
        task_info = scheduler._tasks["test_task"]
        assert task_info["func"] == mock_task
        assert task_info["interval"] == 1.0
        assert task_info["last_run"] == 0

    def test_schedule_duplicate_task(self, scheduler):
        """Test scheduling a task with duplicate name."""
        mock_task1 = Mock()
        mock_task2 = Mock()

        scheduler.schedule("test_task", mock_task1, interval=1.0)
        scheduler.schedule("test_task", mock_task2, interval=2.0)

        # Second task should overwrite the first
        task_info = scheduler._tasks["test_task"]
        assert task_info["func"] == mock_task2
        assert task_info["interval"] == 2.0

    def test_start_stop(self, scheduler):
        """Test starting and stopping the scheduler."""
        assert not scheduler._running

        scheduler.start()
        assert scheduler._running
        assert scheduler._executor is not None
        assert scheduler._scheduler_thread is not None
        assert scheduler._scheduler_thread.is_alive()

        scheduler.stop(wait=True)
        assert not scheduler._running
        assert not scheduler._scheduler_thread.is_alive()

    def test_task_execution(self, scheduler):
        """Test that tasks are executed."""
        execution_count = 0
        execution_lock = threading.Lock()

        def test_task():
            nonlocal execution_count
            with execution_lock:
                execution_count += 1

        scheduler.schedule("test_task", test_task, interval=0.1)
        scheduler.start()

        # Wait for task to execute multiple times
        time.sleep(0.35)

        scheduler.stop(wait=True)

        with execution_lock:
            assert execution_count >= 3

    def test_multiple_tasks(self, scheduler):
        """Test multiple tasks running concurrently."""
        results = {"task1": 0, "task2": 0}
        lock = threading.Lock()

        def task1():
            with lock:
                results["task1"] += 1

        def task2():
            with lock:
                results["task2"] += 1

        scheduler.schedule("task1", task1, interval=0.1)
        scheduler.schedule("task2", task2, interval=0.15)
        scheduler.start()

        time.sleep(0.35)
        scheduler.stop(wait=True)

        with lock:
            assert results["task1"] >= 3
            assert results["task2"] >= 2

    def test_task_error_handling(self, scheduler):
        """Test that task errors don't crash the scheduler."""
        execution_count = 0
        error_count = 0

        def failing_task():
            nonlocal execution_count, error_count
            execution_count += 1
            if execution_count % 2 == 0:
                error_count += 1
                raise Exception("Task error")

        scheduler.schedule("failing_task", failing_task, interval=0.1)
        scheduler.start()

        time.sleep(0.35)
        scheduler.stop(wait=True)

        assert execution_count >= 3
        assert error_count >= 1

    def test_remove_task(self, scheduler):
        """Test removing a scheduled task."""
        mock_task = Mock()

        scheduler.schedule("test_task", mock_task, interval=1.0)
        assert "test_task" in scheduler._tasks

        scheduler.remove_task("test_task")
        assert "test_task" not in scheduler._tasks

    def test_remove_nonexistent_task(self, scheduler):
        """Test removing a task that doesn't exist."""
        # Should not raise an error
        scheduler.remove_task("nonexistent")

    def test_reschedule_task(self, scheduler):
        """Test rescheduling a task with different interval."""
        execution_times = []

        def test_task():
            execution_times.append(time.time())

        # Schedule with long interval
        scheduler.schedule("test_task", test_task, interval=10.0)
        scheduler.start()

        time.sleep(0.1)

        # Reschedule with short interval
        scheduler.schedule("test_task", test_task, interval=0.1)

        time.sleep(0.35)
        scheduler.stop(wait=True)

        # Should have multiple executions with short interval
        assert len(execution_times) >= 3

    def test_stop_with_wait_false(self, scheduler):
        """Test stopping without waiting for tasks."""
        slow_task_started = threading.Event()
        slow_task_completed = threading.Event()

        def slow_task():
            slow_task_started.set()
            time.sleep(0.5)
            slow_task_completed.set()

        scheduler.schedule("slow_task", slow_task, interval=0.1)
        scheduler.start()

        # Wait for task to start
        assert slow_task_started.wait(timeout=1.0)

        # Stop without waiting
        scheduler.stop(wait=False)

        # Scheduler should stop quickly
        assert not scheduler._running

        # Task might still be running
        # (We don't assert this as it's timing-dependent)

    def test_executor_shutdown(self, scheduler):
        """Test that executor is properly shutdown."""
        scheduler.start()
        executor = scheduler._executor

        scheduler.stop(wait=True)

        # Executor should be shutdown
        with pytest.raises(RuntimeError):
            executor.submit(lambda: None)

    def test_task_timing_accuracy(self, scheduler):
        """Test that tasks run at approximately correct intervals."""
        execution_times = []

        def test_task():
            execution_times.append(time.time())

        scheduler.schedule("test_task", test_task, interval=0.1)
        scheduler.start()

        time.sleep(0.55)
        scheduler.stop(wait=True)

        # Calculate intervals between executions
        intervals = []
        for i in range(1, len(execution_times)):
            intervals.append(execution_times[i] - execution_times[i - 1])

        # Average interval should be close to 0.1
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            assert 0.08 < avg_interval < 0.12

    def test_concurrent_task_execution(self, scheduler):
        """Test that tasks can run concurrently."""
        task1_running = threading.Event()
        task2_running = threading.Event()
        both_running = threading.Event()

        def task1():
            task1_running.set()
            if task2_running.is_set():
                both_running.set()
            time.sleep(0.2)

        def task2():
            task2_running.set()
            if task1_running.is_set():
                both_running.set()
            time.sleep(0.2)

        scheduler.schedule("task1", task1, interval=0.1)
        scheduler.schedule("task2", task2, interval=0.1)
        scheduler.start()

        # Wait for both tasks to run concurrently
        assert both_running.wait(timeout=1.0)

        scheduler.stop(wait=True)

    def test_max_workers_limit(self):
        """Test that max_workers limits concurrent executions."""
        scheduler = PeriodicTaskScheduler(max_workers=1)

        running_count = 0
        max_concurrent = 0
        lock = threading.Lock()

        def slow_task():
            nonlocal running_count, max_concurrent
            with lock:
                running_count += 1
                max_concurrent = max(max_concurrent, running_count)

            time.sleep(0.2)

            with lock:
                running_count -= 1

        # Schedule multiple tasks
        for i in range(3):
            scheduler.schedule(f"task{i}", slow_task, interval=0.05)

        scheduler.start()
        time.sleep(0.5)
        scheduler.stop(wait=True)

        # With max_workers=1, only 1 task should run at a time
        assert max_concurrent == 1

    def test_get_task_info(self, scheduler):
        """Test getting information about scheduled tasks."""

        def task1():
            pass

        def task2():
            pass

        scheduler.schedule("task1", task1, interval=1.0)
        scheduler.schedule("task2", task2, interval=2.0)

        # Get all tasks
        tasks = scheduler.get_tasks()
        assert len(tasks) == 2
        assert "task1" in tasks
        assert "task2" in tasks
        assert tasks["task1"]["interval"] == 1.0
        assert tasks["task2"]["interval"] == 2.0
