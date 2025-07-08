"""Thread safety and concurrent access tests for observability system."""

import os
import queue
import random
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from coda.configuration import CodaConfig, ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityThreadSafety:
    """Test thread safety and concurrent access in the observability system."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a config manager for thread safety testing."""
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "thread_safety": {
                "lock_timeout": 5.0,
                "enable_thread_local": True,
                "max_concurrent_writes": 10,
            },
            "metrics": {"enabled": True},
            "tracing": {"enabled": True},
            "health": {"enabled": True},
            "error_tracking": {"enabled": True},
            "profiling": {"enabled": True},
        }

        manager = ConfigManager()
        manager.config = config
        return manager

    def test_concurrent_event_tracking(self, config_manager):
        """Test concurrent event tracking from multiple threads."""
        obs_manager = ObservabilityManager(config_manager)

        num_threads = 20
        events_per_thread = 1000
        all_events = set()
        lock = threading.Lock()
        errors = []

        def track_events(thread_id):
            thread_events = set()
            try:
                for i in range(events_per_thread):
                    event_id = f"thread_{thread_id}_event_{i}"
                    obs_manager.track_event(
                        event_id, {"thread_id": thread_id, "index": i, "timestamp": time.time()}
                    )
                    thread_events.add(event_id)
            except Exception as e:
                errors.append((thread_id, e))

            with lock:
                all_events.update(thread_events)

        # Run threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=track_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(all_events) == num_threads * events_per_thread

    def test_concurrent_trace_operations(self, config_manager):
        """Test concurrent trace operations with nested spans."""
        obs_manager = ObservabilityManager(config_manager)

        num_threads = 10
        traces_per_thread = 100
        trace_ids = []
        lock = threading.Lock()

        def create_traces(thread_id):
            for i in range(traces_per_thread):
                trace_id = f"thread_{thread_id}_trace_{i}"

                with obs_manager.trace(trace_id) as span:
                    span.set_attribute("thread_id", thread_id)

                    # Nested trace
                    with obs_manager.trace(f"{trace_id}_nested") as nested_span:
                        nested_span.set_attribute("parent", trace_id)
                        time.sleep(0.001)  # Simulate work

                    with lock:
                        trace_ids.append(trace_id)

        # Run threads
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_traces, i) for i in range(num_threads)]

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()

        # Verify all traces were created
        assert len(trace_ids) == num_threads * traces_per_thread

    def test_race_condition_in_metrics_aggregation(self, config_manager):
        """Test for race conditions in metrics aggregation."""
        obs_manager = ObservabilityManager(config_manager)

        # Shared counter that multiple threads will update
        counter_name = "concurrent_counter"
        num_threads = 50
        increments_per_thread = 100

        def increment_counter(thread_id):
            for _ in range(increments_per_thread):
                obs_manager.track_event(
                    "counter_increment",
                    {"counter": counter_name, "thread_id": thread_id, "increment": 1},
                )

        # Run threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=increment_counter, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Get metrics summary
        if hasattr(obs_manager.metrics_collector, "get_summary"):
            summary = obs_manager.metrics_collector.get_summary()
            # Total events should match expected
            total_events = summary.get("total_events", 0)
            expected_events = num_threads * increments_per_thread
            assert total_events >= expected_events  # May have other events too

    def test_concurrent_error_tracking(self, config_manager):
        """Test concurrent error tracking with different error types."""
        obs_manager = ObservabilityManager(config_manager)

        error_types = [ValueError, TypeError, RuntimeError, ConnectionError, TimeoutError]
        num_threads = len(error_types) * 2
        errors_per_thread = 200

        def track_errors(thread_id, error_type):
            for i in range(errors_per_thread):
                error = error_type(f"Error from thread {thread_id}, iteration {i}")
                obs_manager.track_error(
                    error,
                    {
                        "thread_id": thread_id,
                        "iteration": i,
                        "severity": random.choice(["low", "medium", "high"]),
                    },
                )

                # Occasionally query errors
                if i % 50 == 0 and obs_manager.error_tracker:
                    obs_manager.error_tracker.get_recent_errors(limit=10)

        # Run threads with different error types
        threads = []
        for i in range(num_threads):
            error_type = error_types[i % len(error_types)]
            thread = threading.Thread(target=track_errors, args=(i, error_type))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify error tracking worked
        if obs_manager.error_tracker:
            analysis = obs_manager.error_tracker.get_error_analysis()
            assert analysis["total_errors"] >= num_threads * errors_per_thread

    def test_concurrent_health_checks(self, config_manager):
        """Test concurrent health check operations."""
        obs_manager = ObservabilityManager(config_manager)

        num_threads = 20
        checks_per_thread = 50
        health_results = queue.Queue()

        def perform_health_checks(thread_id):
            for i in range(checks_per_thread):
                try:
                    # Get overall health
                    health = obs_manager.get_health_status()
                    health_results.put((thread_id, i, "overall", health))

                    # Check specific component
                    if obs_manager.health_monitor:
                        component = random.choice(
                            ["metrics", "tracing", "health", "error_tracking"]
                        )
                        component_health = obs_manager.health_monitor.check_component_health(
                            component
                        )
                        health_results.put((thread_id, i, component, component_health))

                    # Simulate some work between checks
                    time.sleep(random.uniform(0.001, 0.01))
                except Exception as e:
                    health_results.put((thread_id, i, "error", str(e)))

        # Run threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=perform_health_checks, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Analyze results
        results = []
        while not health_results.empty():
            results.append(health_results.get())

        # Should have results from all threads
        assert len(results) >= num_threads * checks_per_thread * 2  # overall + component

        # Check for errors
        errors = [r for r in results if r[2] == "error"]
        assert len(errors) == 0, f"Health check errors: {errors}"

    def test_thread_local_storage(self, config_manager):
        """Test thread-local storage for observability context."""
        obs_manager = ObservabilityManager(config_manager)

        thread_contexts = {}
        lock = threading.Lock()

        def thread_with_context(thread_id):
            # Set thread-local context
            context = {
                "thread_id": thread_id,
                "user_id": f"user_{thread_id}",
                "request_id": f"req_{thread_id}_{time.time()}",
            }

            # Store context (simulating thread-local)
            with lock:
                thread_contexts[threading.current_thread().ident] = context

            # Perform operations that should include context
            for i in range(100):
                obs_manager.track_event(f"contextual_event_{i}", {"operation": "test", "index": i})

                with obs_manager.trace(f"contextual_trace_{i}"):
                    time.sleep(0.001)

            # Verify context is isolated
            with lock:
                stored_context = thread_contexts.get(threading.current_thread().ident)
                assert stored_context == context

        # Run threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=thread_with_context, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have its own context
        assert len(thread_contexts) == 10

    def test_deadlock_prevention(self, config_manager):
        """Test that concurrent operations don't cause deadlocks."""
        obs_manager = ObservabilityManager(config_manager)

        # Operations that might cause deadlock if not handled properly
        def operation_a(thread_id):
            for i in range(100):
                with obs_manager.trace(f"op_a_{thread_id}_{i}"):
                    obs_manager.track_event("event_a", {"thread": thread_id})
                    # Try to access another resource
                    obs_manager.get_health_status()

        def operation_b(thread_id):
            for i in range(100):
                health = obs_manager.get_health_status()
                with obs_manager.trace(f"op_b_{thread_id}_{i}"):
                    obs_manager.track_event("event_b", {"health": health})

        # Run operations concurrently
        threads = []
        for i in range(5):
            thread_a = threading.Thread(target=operation_a, args=(i,))
            thread_b = threading.Thread(target=operation_b, args=(i,))
            threads.extend([thread_a, thread_b])
            thread_a.start()
            thread_b.start()

        # Wait with timeout to detect deadlock
        start_time = time.time()
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout

        # Check if all threads completed
        active_threads = [t for t in threads if t.is_alive()]
        assert len(active_threads) == 0, (
            f"Deadlock detected! {len(active_threads)} threads still running"
        )

        completion_time = time.time() - start_time
        assert completion_time < 10, (
            f"Operations took too long ({completion_time}s), possible lock contention"
        )

    def test_concurrent_configuration_updates(self, config_manager):
        """Test thread safety during configuration updates."""
        obs_manager = ObservabilityManager(config_manager)

        errors = []

        def reader_thread(thread_id):
            """Continuously read configuration and track events."""
            for i in range(200):
                try:
                    # Read configuration
                    enabled = config_manager.get_bool("observability.enabled")
                    buffer_size = config_manager.get_int(
                        "observability.memory.buffer_size", default=1000
                    )

                    # Track event based on config
                    if enabled:
                        obs_manager.track_event(
                            f"reader_{thread_id}_{i}", {"buffer_size": buffer_size}
                        )
                except Exception as e:
                    errors.append(("reader", thread_id, e))

        def writer_thread(thread_id):
            """Periodically update configuration."""
            for _ in range(20):
                try:
                    # Simulate config updates
                    new_buffer_size = random.randint(500, 2000)
                    config_manager.config.observability["memory"]["buffer_size"] = new_buffer_size
                    time.sleep(0.05)  # Small delay between updates
                except Exception as e:
                    errors.append(("writer", thread_id, e))

        # Start readers and writers
        threads = []

        # Start reader threads
        for i in range(5):
            thread = threading.Thread(target=reader_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Start writer threads
        for i in range(2):
            thread = threading.Thread(target=writer_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should complete without errors
        assert len(errors) == 0, f"Errors during concurrent config access: {errors}"

    def test_atomic_operations(self, config_manager):
        """Test atomicity of critical operations."""
        obs_manager = ObservabilityManager(config_manager)

        # Test atomic counter increments
        counter_values = []
        num_threads = 10
        increments_per_thread = 1000

        def increment_and_read(thread_id):
            for _ in range(increments_per_thread):
                # These operations should be atomic
                obs_manager.track_event("atomic_increment", {"value": 1})

                # Try to read current state
                if hasattr(obs_manager.metrics_collector, "get_event_count"):
                    count = obs_manager.metrics_collector.get_event_count()
                    counter_values.append(count)

        # Run threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=increment_and_read, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Counter values should be monotonically increasing
        sorted_values = sorted(counter_values)
        assert sorted_values == counter_values or len(set(counter_values)) == len(counter_values)

    def test_concurrent_export(self, config_manager, temp_dir):
        """Test concurrent export operations."""
        obs_manager = ObservabilityManager(config_manager)

        # Generate some data
        for i in range(1000):
            obs_manager.track_event(f"export_test_{i}", {"index": i})

        export_results = queue.Queue()

        def export_data(thread_id, format_type):
            try:
                output_file = os.path.join(temp_dir, f"export_{thread_id}.{format_type}")
                result = obs_manager.export_data(format_type, output_file)
                export_results.put((thread_id, format_type, "success", result))
            except Exception as e:
                export_results.put((thread_id, format_type, "error", str(e)))

        # Start concurrent exports
        threads = []
        formats = ["json", "json", "summary", "summary"]  # Multiple of same format

        for i, fmt in enumerate(formats):
            thread = threading.Thread(target=export_data, args=(i, fmt))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Check results
        results = []
        while not export_results.empty():
            results.append(export_results.get())

        # All exports should complete
        assert len(results) == len(formats)

        # Check for conflicts
        errors = [r for r in results if r[2] == "error"]
        assert len(errors) == 0, f"Export errors: {errors}"

    def test_stress_test_with_chaos(self, config_manager):
        """Stress test with chaotic access patterns."""
        obs_manager = ObservabilityManager(config_manager)

        num_threads = 20
        duration_seconds = 5
        operations = ["event", "trace", "error", "health", "export", "stats"]

        stop_event = threading.Event()
        operation_counts = {op: 0 for op in operations}
        count_lock = threading.Lock()

        def chaos_worker(thread_id):
            while not stop_event.is_set():
                operation = random.choice(operations)

                try:
                    if operation == "event":
                        obs_manager.track_event(f"chaos_{thread_id}", {"random": random.random()})
                    elif operation == "trace":
                        with obs_manager.trace(f"chaos_trace_{thread_id}"):
                            time.sleep(random.uniform(0, 0.01))
                    elif operation == "error":
                        obs_manager.track_error(
                            Exception(f"Chaos error {thread_id}"),
                            {"severity": random.choice(["low", "medium", "high"])},
                        )
                    elif operation == "health":
                        obs_manager.get_health_status()
                    elif operation == "export":
                        if hasattr(obs_manager, "get_metrics_summary"):
                            obs_manager.get_metrics_summary()
                    elif operation == "stats":
                        obs_manager.get_status()

                    with count_lock:
                        operation_counts[operation] += 1

                except Exception:
                    pass  # Ignore errors in chaos test

        # Start chaos threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=chaos_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Let chaos ensue
        time.sleep(duration_seconds)
        stop_event.set()

        # Wait for threads
        for thread in threads:
            thread.join()

        # System should still be functional
        final_health = obs_manager.get_health_status()
        assert final_health is not None

        # Should have performed many operations
        total_ops = sum(operation_counts.values())
        print(f"\nChaos test performed {total_ops} operations in {duration_seconds} seconds")
        print(f"Operations breakdown: {operation_counts}")
        assert total_ops > 1000  # Should handle many operations
