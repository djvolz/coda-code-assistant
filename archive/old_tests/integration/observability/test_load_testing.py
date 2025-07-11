"""Load testing for observability system with high-volume metrics."""

import multiprocessing
import os
import random
import statistics
import tempfile
import threading
import time
from datetime import datetime

import psutil
import pytest

from coda.configuration import CodaConfig, ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityLoadTesting:
    """Load test the observability system with high-volume metrics."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_for_load_testing(self, temp_dir):
        """Create config optimized for load testing."""
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "performance": {
                "batch_size": 1000,
                "write_buffer_size": 10000,
                "compression": True,
                "async_writes": True,
            },
            "memory": {"max_memory_mb": 200, "buffer_size": 10000},
            "metrics": {"enabled": True},
            "tracing": {"enabled": True},
            "health": {"enabled": True},
            "error_tracking": {"enabled": True},
            "profiling": {"enabled": True},
        }

        manager = ConfigManager()
        manager.config = config
        return manager

    def measure_throughput(self, func, duration_seconds=10):
        """Measure throughput of a function over a duration."""
        start_time = time.time()
        count = 0

        while time.time() - start_time < duration_seconds:
            func()
            count += 1

        elapsed = time.time() - start_time
        return count / elapsed  # Operations per second

    @pytest.mark.slow
    def test_event_tracking_throughput(self, config_for_load_testing):
        """Test maximum event tracking throughput."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        event_count = 0

        def track_event():
            nonlocal event_count
            obs_manager.track_event(
                f"throughput_test_{event_count}",
                {"timestamp": datetime.now().isoformat(), "index": event_count, "data": "x" * 100},
            )
            event_count += 1

        # Measure throughput
        throughput = self.measure_throughput(track_event, duration_seconds=5)

        print(f"\nEvent tracking throughput: {throughput:.2f} events/second")

        # Should handle at least 1000 events per second
        assert throughput > 1000

    @pytest.mark.slow
    def test_concurrent_load(self, config_for_load_testing):
        """Test system under concurrent load from multiple threads."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        events_per_thread = 10000
        num_threads = 10
        errors = []
        latencies = []

        def worker(thread_id):
            thread_latencies = []
            try:
                for i in range(events_per_thread):
                    start = time.time()

                    # Mix of different operations
                    if i % 4 == 0:
                        obs_manager.track_event(
                            f"thread_{thread_id}_event_{i}",
                            {"thread": thread_id, "operation": "event"},
                        )
                    elif i % 4 == 1:
                        with obs_manager.trace(f"thread_{thread_id}_trace_{i}"):
                            time.sleep(0.0001)  # Simulate work
                    elif i % 4 == 2:
                        obs_manager.track_provider_request(
                            "test_provider",
                            random.uniform(0.01, 0.1),
                            random.choice([True, False]),
                            {"thread": thread_id},
                        )
                    else:
                        if random.random() < 0.1:  # 10% error rate
                            obs_manager.track_error(
                                Exception(f"Test error from thread {thread_id}"),
                                {"thread": thread_id, "index": i},
                            )

                    latency = time.time() - start
                    thread_latencies.append(latency)
            except Exception as e:
                errors.append(e)

            latencies.extend(thread_latencies)

        # Start threads
        threads = []
        start_time = time.time()

        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        duration = time.time() - start_time

        # Calculate statistics
        total_operations = events_per_thread * num_threads
        throughput = total_operations / duration
        avg_latency = statistics.mean(latencies) * 1000  # Convert to ms
        p95_latency = statistics.quantiles(latencies, n=20)[18] * 1000  # 95th percentile
        p99_latency = statistics.quantiles(latencies, n=100)[98] * 1000  # 99th percentile

        print("\nConcurrent Load Test Results:")
        print(f"  Total operations: {total_operations}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Throughput: {throughput:.2f} ops/second")
        print(f"  Average latency: {avg_latency:.2f} ms")
        print(f"  P95 latency: {p95_latency:.2f} ms")
        print(f"  P99 latency: {p99_latency:.2f} ms")
        print(f"  Errors: {len(errors)}")

        # Assertions
        assert len(errors) == 0
        assert throughput > 5000  # Should handle at least 5000 ops/sec
        assert avg_latency < 10  # Average latency under 10ms
        assert p99_latency < 50  # P99 latency under 50ms

    @pytest.mark.slow
    def test_sustained_load(self, config_for_load_testing):
        """Test system stability under sustained load."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        duration_minutes = 2
        events_per_second = 1000

        start_time = time.time()
        event_count = 0
        errors = []
        memory_samples = []

        # Get process for memory monitoring
        process = psutil.Process()

        while time.time() - start_time < duration_minutes * 60:
            batch_start = time.time()

            # Track batch of events
            for _ in range(events_per_second):
                try:
                    obs_manager.track_event(
                        f"sustained_load_{event_count}",
                        {
                            "timestamp": datetime.now().isoformat(),
                            "batch": event_count // events_per_second,
                        },
                    )
                    event_count += 1
                except Exception as e:
                    errors.append(e)

            # Sample memory usage
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_samples.append(memory_mb)

            # Sleep to maintain rate
            batch_duration = time.time() - batch_start
            if batch_duration < 1.0:
                time.sleep(1.0 - batch_duration)

        # Analyze results
        total_duration = time.time() - start_time
        actual_rate = event_count / total_duration
        memory_growth = memory_samples[-1] - memory_samples[0]
        avg_memory = statistics.mean(memory_samples)

        print("\nSustained Load Test Results:")
        print(f"  Duration: {total_duration / 60:.2f} minutes")
        print(f"  Total events: {event_count}")
        print(f"  Target rate: {events_per_second} events/sec")
        print(f"  Actual rate: {actual_rate:.2f} events/sec")
        print(f"  Memory growth: {memory_growth:.2f} MB")
        print(f"  Average memory: {avg_memory:.2f} MB")
        print(f"  Errors: {len(errors)}")

        # Assertions
        assert len(errors) == 0
        assert actual_rate > events_per_second * 0.9  # Within 10% of target
        assert memory_growth < 100  # Less than 100MB growth

    @pytest.mark.slow
    def test_burst_load(self, config_for_load_testing):
        """Test system response to burst loads."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        # Test pattern: normal -> burst -> normal
        phases = [
            ("normal", 100, 5),  # 100 events/sec for 5 seconds
            ("burst", 10000, 2),  # 10000 events/sec for 2 seconds
            ("normal", 100, 5),  # Back to 100 events/sec
        ]

        results = []

        for phase_name, rate, duration in phases:
            phase_start = time.time()
            events_sent = 0
            errors = []

            while time.time() - phase_start < duration:
                batch_start = time.time()

                for _ in range(rate):
                    try:
                        obs_manager.track_event(
                            f"{phase_name}_burst_{events_sent}", {"phase": phase_name, "rate": rate}
                        )
                        events_sent += 1
                    except Exception as e:
                        errors.append(e)

                # Maintain rate
                batch_duration = time.time() - batch_start
                if batch_duration < 1.0:
                    time.sleep(1.0 - batch_duration)

            phase_duration = time.time() - phase_start
            actual_rate = events_sent / phase_duration

            results.append(
                {
                    "phase": phase_name,
                    "target_rate": rate,
                    "actual_rate": actual_rate,
                    "events": events_sent,
                    "errors": len(errors),
                }
            )

        print("\nBurst Load Test Results:")
        for result in results:
            print(
                f"  {result['phase']}: {result['actual_rate']:.2f} events/sec "
                f"(target: {result['target_rate']}), errors: {result['errors']}"
            )

        # System should handle burst without errors
        for result in results:
            assert result["errors"] == 0
            assert result["actual_rate"] > result["target_rate"] * 0.8

    @pytest.mark.slow
    def test_mixed_workload(self, config_for_load_testing):
        """Test with realistic mixed workload."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        duration_seconds = 30
        operations = {
            "events": 0,
            "traces": 0,
            "errors": 0,
            "provider_requests": 0,
            "health_checks": 0,
        }

        start_time = time.time()

        while time.time() - start_time < duration_seconds:
            # Simulate realistic workload distribution
            operation = random.choices(
                ["event", "trace", "error", "provider", "health"],
                weights=[70, 20, 5, 4, 1],  # 70% events, 20% traces, etc.
                k=1,
            )[0]

            try:
                if operation == "event":
                    obs_manager.track_event(
                        "mixed_workload_event",
                        {
                            "type": random.choice(["user_action", "system_event", "api_call"]),
                            "user_id": random.randint(1, 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                    operations["events"] += 1

                elif operation == "trace":
                    with obs_manager.trace(f"operation_{random.choice(['api', 'db', 'cache'])}"):
                        time.sleep(random.uniform(0.001, 0.01))  # Simulate operation
                    operations["traces"] += 1

                elif operation == "error":
                    error_types = [ValueError, ConnectionError, TimeoutError, RuntimeError]
                    obs_manager.track_error(
                        random.choice(error_types)("Simulated error"),
                        {"severity": random.choice(["low", "medium", "high"])},
                    )
                    operations["errors"] += 1

                elif operation == "provider":
                    obs_manager.track_provider_request(
                        random.choice(["openai", "anthropic", "ollama"]),
                        random.uniform(0.1, 2.0),
                        random.random() > 0.05,  # 95% success rate
                        {"model": random.choice(["gpt-4", "claude-2", "llama2"])},
                    )
                    operations["provider_requests"] += 1

                elif operation == "health":
                    obs_manager.get_health_status()
                    operations["health_checks"] += 1

            except Exception:
                pass  # Count errors separately

        total_operations = sum(operations.values())
        duration = time.time() - start_time

        print("\nMixed Workload Test Results:")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Total operations: {total_operations}")
        print(f"  Throughput: {total_operations / duration:.2f} ops/sec")
        print("\n  Operation breakdown:")
        for op_type, count in operations.items():
            percentage = (count / total_operations * 100) if total_operations > 0 else 0
            print(f"    {op_type}: {count} ({percentage:.1f}%)")

        # Should maintain good throughput with mixed workload
        assert total_operations / duration > 1000

    @pytest.mark.slow
    def test_resource_utilization(self, config_for_load_testing):
        """Test resource utilization under load."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        # Get process and initial stats
        process = psutil.Process()
        initial_cpu_percent = process.cpu_percent(interval=1)
        initial_memory = process.memory_info().rss / 1024 / 1024
        initial_threads = process.num_threads()

        # Generate load
        start_time = time.time()
        event_count = 0

        while time.time() - start_time < 10:  # 10 second test
            obs_manager.track_event(
                f"resource_test_{event_count}", {"data": "x" * 1000, "index": event_count}
            )
            event_count += 1

            if event_count % 1000 == 0:
                # Occasional complex operation
                with obs_manager.trace("complex_operation"):
                    for _ in range(10):
                        obs_manager.track_event("nested_event", {"nested": True})

        # Get final stats
        final_cpu_percent = process.cpu_percent(interval=1)
        final_memory = process.memory_info().rss / 1024 / 1024
        final_threads = process.num_threads()

        print("\nResource Utilization Test Results:")
        print(f"  Events processed: {event_count}")
        print(f"  CPU usage: {initial_cpu_percent:.1f}% -> {final_cpu_percent:.1f}%")
        print(f"  Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB")
        print(f"  Thread count: {initial_threads} -> {final_threads}")
        print(f"  Memory growth: {final_memory - initial_memory:.1f}MB")

        # Resource usage should be reasonable
        assert final_cpu_percent < 80  # Less than 80% CPU
        assert final_memory - initial_memory < 200  # Less than 200MB growth
        assert final_threads - initial_threads < 20  # Reasonable thread growth

    @pytest.mark.slow
    def test_degradation_under_extreme_load(self, config_for_load_testing):
        """Test graceful degradation under extreme load."""
        obs_manager = ObservabilityManager(config_for_load_testing)

        # Try to overwhelm the system
        extreme_rate = 100000  # 100k events per second attempt
        duration = 5

        successful_events = 0
        dropped_events = 0
        start_time = time.time()

        while time.time() - start_time < duration:
            batch_start = time.time()
            batch_success = 0
            batch_dropped = 0

            for _ in range(extreme_rate):
                try:
                    obs_manager.track_event(
                        f"extreme_load_{successful_events}", {"timestamp": time.time()}
                    )
                    batch_success += 1
                except Exception:
                    batch_dropped += 1

                # Break if taking too long
                if time.time() - batch_start > 1.0:
                    batch_dropped += extreme_rate - batch_success - batch_dropped
                    break

            successful_events += batch_success
            dropped_events += batch_dropped

        total_attempted = successful_events + dropped_events
        success_rate = successful_events / total_attempted if total_attempted > 0 else 0

        print("\nExtreme Load Test Results:")
        print(f"  Attempted events: {total_attempted}")
        print(f"  Successful events: {successful_events}")
        print(f"  Dropped events: {dropped_events}")
        print(f"  Success rate: {success_rate:.2%}")

        # System should degrade gracefully, not crash
        assert success_rate > 0.1  # At least 10% should succeed
        # System should still be responsive after extreme load
        health = obs_manager.get_health_status()
        assert health is not None

    @pytest.mark.slow
    def test_multiprocess_load(self, config_for_load_testing):
        """Test load from multiple processes."""
        num_processes = 4
        events_per_process = 10000

        def worker_process(process_id, config_dict, result_queue):
            """Worker process function."""
            # Recreate config in subprocess
            config = CodaConfig()
            config.observability = config_dict
            manager = ConfigManager()
            manager.config = config

            obs_manager = ObservabilityManager(manager)

            start_time = time.time()
            errors = 0

            for i in range(events_per_process):
                try:
                    obs_manager.track_event(
                        f"process_{process_id}_event_{i}", {"process": process_id, "index": i}
                    )
                except Exception:
                    errors += 1

            duration = time.time() - start_time
            result_queue.put(
                {
                    "process_id": process_id,
                    "duration": duration,
                    "errors": errors,
                    "rate": events_per_process / duration,
                }
            )

        # Start processes
        result_queue = multiprocessing.Queue()
        processes = []

        for i in range(num_processes):
            p = multiprocessing.Process(
                target=worker_process,
                args=(i, config_for_load_testing.config.observability, result_queue),
            )
            processes.append(p)
            p.start()

        # Wait for completion
        for p in processes:
            p.join()

        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        total_events = num_processes * events_per_process
        total_duration = max(r["duration"] for r in results)
        aggregate_rate = sum(r["rate"] for r in results)
        total_errors = sum(r["errors"] for r in results)

        print("\nMultiprocess Load Test Results:")
        print(f"  Processes: {num_processes}")
        print(f"  Total events: {total_events}")
        print(f"  Total duration: {total_duration:.2f} seconds")
        print(f"  Aggregate rate: {aggregate_rate:.2f} events/sec")
        print(f"  Total errors: {total_errors}")

        # All processes should complete successfully
        assert len(results) == num_processes
        assert total_errors == 0
        assert aggregate_rate > 10000  # Should handle >10k events/sec across processes
