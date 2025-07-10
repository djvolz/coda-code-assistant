#!/usr/bin/env python3
"""
Collect test execution metrics during pytest runs.

This script is designed to be used as a pytest plugin or wrapper to collect:
- Individual test execution times
- Test success/failure counts
- Slow test identification
- Test coverage metrics
"""

import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import pytest
except ImportError:
    print("Error: pytest not installed")
    sys.exit(1)


class TestMetricsCollector:
    """Pytest plugin to collect test metrics."""

    def __init__(self):
        self.test_results = []
        self.session_start_time = None
        self.session_end_time = None
        self.coverage_data = {}

    def pytest_sessionstart(self, session):
        """Called when test session starts."""
        self.session_start_time = time.time()

    def pytest_sessionfinish(self, session, exitstatus):
        """Called when test session finishes."""
        self.session_end_time = time.time()
        self._save_metrics(session)

    def pytest_runtest_protocol(self, item, nextitem):
        """Called for each test item."""
        start_time = time.time()

        # Run the test
        reports = pytest.main.runtestprotocol(item, log=False, nextitem=nextitem)

        end_time = time.time()
        duration = end_time - start_time

        # Extract test result
        call_report = None
        for report in reports:
            if report.when == "call":
                call_report = report
                break

        if call_report:
            self.test_results.append(
                {
                    "test_id": item.nodeid,
                    "test_name": item.name,
                    "module": str(item.fspath),
                    "duration": duration,
                    "outcome": call_report.outcome,
                    "markers": [marker.name for marker in item.iter_markers()],
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return True

    def _save_metrics(self, session):
        """Save collected metrics to file."""
        metrics_dir = Path.home() / ".coda" / "test_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["outcome"] == "passed")
        failed = sum(1 for r in self.test_results if r["outcome"] == "failed")
        skipped = sum(1 for r in self.test_results if r["outcome"] == "skipped")

        # Identify slow tests (>1 second)
        slow_tests = sorted(
            [r for r in self.test_results if r["duration"] > 1.0],
            key=lambda x: x["duration"],
            reverse=True,
        )[:10]

        # Group by module
        by_module = defaultdict(list)
        for result in self.test_results:
            by_module[result["module"]].append(result)

        # Create metrics summary
        metrics = {
            "session": {
                "start_time": self.session_start_time,
                "end_time": self.session_end_time,
                "duration": self.session_end_time - self.session_start_time,
                "timestamp": datetime.now().isoformat(),
            },
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": passed / total_tests if total_tests > 0 else 0,
            },
            "slow_tests": slow_tests,
            "by_module": {
                module: {
                    "total": len(results),
                    "passed": sum(1 for r in results if r["outcome"] == "passed"),
                    "failed": sum(1 for r in results if r["outcome"] == "failed"),
                    "avg_duration": sum(r["duration"] for r in results) / len(results),
                }
                for module, results in by_module.items()
            },
            "test_results": self.test_results,
        }

        # Save to timestamped file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metrics_file = metrics_dir / f"test_metrics_{timestamp}.json"

        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)

        # Also save as latest
        latest_file = metrics_dir / "test_metrics_latest.json"
        with open(latest_file, "w") as f:
            json.dump(metrics, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("TEST METRICS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed} ({passed / total_tests * 100:.1f}%)")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Duration: {self.session_end_time - self.session_start_time:.2f}s")

        if slow_tests:
            print("\nSlowest Tests (>1s):")
            for test in slow_tests[:5]:
                print(f"  {test['duration']:.2f}s - {test['test_name']}")

        print(f"\nMetrics saved to: {metrics_file}")


def analyze_test_trends():
    """Analyze test metrics over time."""
    metrics_dir = Path.home() / ".coda" / "test_metrics"
    if not metrics_dir.exists():
        print("No test metrics found. Run tests with metrics collection enabled.")
        return

    # Load all metrics files
    metrics_files = sorted(metrics_dir.glob("test_metrics_*.json"))
    if not metrics_files:
        print("No metrics files found.")
        return

    # Analyze trends
    all_metrics = []
    for file in metrics_files[-30:]:  # Last 30 runs
        with open(file) as f:
            all_metrics.append(json.load(f))

    # Calculate trends
    print("\nTEST EXECUTION TRENDS")
    print("=" * 60)

    # Success rate trend
    success_rates = [m["summary"]["success_rate"] * 100 for m in all_metrics]
    avg_success = sum(success_rates) / len(success_rates)
    print(f"Average Success Rate: {avg_success:.1f}%")

    # Duration trend
    durations = [m["session"]["duration"] for m in all_metrics]
    avg_duration = sum(durations) / len(durations)
    print(f"Average Test Duration: {avg_duration:.1f}s")

    # Test count trend
    test_counts = [m["summary"]["total_tests"] for m in all_metrics]
    print(f"Average Test Count: {sum(test_counts) / len(test_counts):.0f}")

    # Identify consistently slow tests
    slow_test_counts = defaultdict(list)
    for metrics in all_metrics:
        for test in metrics.get("slow_tests", []):
            slow_test_counts[test["test_name"]].append(test["duration"])

    print("\nConsistently Slow Tests:")
    for test_name, durations in sorted(
        slow_test_counts.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True
    )[:5]:
        avg_duration = sum(durations) / len(durations)
        print(f"  {avg_duration:.2f}s avg - {test_name} (appeared {len(durations)} times)")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test metrics collection and analysis")
    parser.add_argument("--analyze", action="store_true", help="Analyze test trends")
    parser.add_argument("--export", help="Export metrics summary to file")

    args = parser.parse_args()

    if args.analyze:
        analyze_test_trends()
    else:
        print("Use pytest with this plugin to collect metrics:")
        print("  pytest --metrics")
        print("\nOr analyze existing metrics:")
        print("  python test_metrics_collector.py --analyze")


# Register as pytest plugin
def pytest_configure(config):
    """Register the metrics collector plugin."""
    config.pluginmanager.register(TestMetricsCollector(), "metrics_collector")


if __name__ == "__main__":
    main()
