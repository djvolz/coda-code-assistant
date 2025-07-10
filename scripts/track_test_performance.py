#!/usr/bin/env python3
"""Track and analyze test performance metrics.

This script helps identify slow tests and track performance improvements
over time. It can be used locally or in CI to monitor test suite health.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class TestPerformanceTracker:
    """Track and analyze test performance metrics."""

    def __init__(self, history_file: str = ".test-performance-history.json"):
        self.history_file = Path(history_file)
        self.history = self.load_history()

    def load_history(self) -> dict:
        """Load performance history from file."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return {"runs": []}

    def save_history(self):
        """Save performance history to file."""
        with open(self.history_file, "w") as f:
            json.dump(self.history, f, indent=2)

    def run_tests_with_profiling(self, pytest_args: list[str]) -> dict:
        """Run pytest with duration profiling."""
        cmd = [
            "uv",
            "run",
            "pytest",
            "--durations=50",
            "--durations-min=0.1",
            "--json-report",
            "--json-report-file=.test-report.json",
            "-v",
        ] + pytest_args

        print(f"Running: {' '.join(cmd)}")
        start_time = datetime.now()

        result = subprocess.run(cmd, capture_output=True, text=True)
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()

        # Parse JSON report
        report_data = {}
        if Path(".test-report.json").exists():
            with open(".test-report.json") as f:
                report_data = json.load(f)

        return {
            "timestamp": start_time.isoformat(),
            "duration": duration,
            "exit_code": result.returncode,
            "pytest_output": result.stdout,
            "report": report_data,
        }

    def analyze_test_durations(self, run_data: dict) -> list[tuple[str, float]]:
        """Extract and analyze test durations from run data."""
        slow_tests = []

        if "report" in run_data and "tests" in run_data["report"]:
            for test in run_data["report"]["tests"]:
                if test.get("call", {}).get("duration", 0) > 0.5:
                    slow_tests.append((test["nodeid"], test["call"]["duration"]))

        return sorted(slow_tests, key=lambda x: x[1], reverse=True)

    def generate_report(self, run_data: dict, slow_tests: list[tuple[str, float]]):
        """Generate performance report."""
        print("\n" + "=" * 60)
        print("TEST PERFORMANCE REPORT")
        print("=" * 60)

        print(f"\nTotal Duration: {run_data['duration']:.2f}s")
        print(f"Exit Code: {run_data['exit_code']}")

        if slow_tests:
            print("\nTop 10 Slowest Tests (>0.5s):")
            print("-" * 50)
            for test_name, duration in slow_tests[:10]:
                print(f"{duration:6.2f}s - {test_name}")

        # Compare with previous runs
        if len(self.history["runs"]) > 0:
            prev_run = self.history["runs"][-1]
            prev_duration = prev_run.get("duration", 0)
            diff = run_data["duration"] - prev_duration
            pct_change = (diff / prev_duration * 100) if prev_duration > 0 else 0

            print("\nComparison with Previous Run:")
            print(f"Previous: {prev_duration:.2f}s")
            print(f"Current:  {run_data['duration']:.2f}s")
            print(f"Change:   {diff:+.2f}s ({pct_change:+.1f}%)")

    def suggest_improvements(self, slow_tests: list[tuple[str, float]]):
        """Suggest improvements based on slow tests."""
        print("\n" + "=" * 60)
        print("IMPROVEMENT SUGGESTIONS")
        print("=" * 60)

        suggestions = []

        for test_name, duration in slow_tests:
            if "test_cli_" in test_name and duration > 1.0:
                suggestions.append(f"- {test_name}: Consider mocking subprocess calls")
            elif "test_web_" in test_name:
                suggestions.append(f"- {test_name}: Consider using lighter fixtures")
            elif duration > 2.0:
                suggestions.append(f"- {test_name}: Mark as @pytest.mark.slow")

        if suggestions:
            print("\nSpecific Test Improvements:")
            for suggestion in suggestions[:5]:
                print(suggestion)

        print("\nGeneral Recommendations:")
        print("- Run slow tests separately: pytest -m 'not slow'")
        print("- Use parallel execution: pytest -n auto")
        print("- Enable test caching: --cache-clear for fresh runs")
        print("- Profile fixtures: pytest --setup-show")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Track and analyze test performance")
    parser.add_argument("pytest_args", nargs="*", help="Arguments to pass to pytest")
    parser.add_argument(
        "--history-file",
        default=".test-performance-history.json",
        help="Path to performance history file",
    )
    parser.add_argument("--save-history", action="store_true", help="Save this run to history")
    parser.add_argument(
        "--compare-only", action="store_true", help="Only show comparison with previous runs"
    )

    args = parser.parse_args()

    tracker = TestPerformanceTracker(args.history_file)

    if args.compare_only:
        if len(tracker.history["runs"]) < 2:
            print("Not enough history for comparison")
            sys.exit(1)

        current = tracker.history["runs"][-1]
        previous = tracker.history["runs"][-2]
        print(f"Previous: {previous['duration']:.2f}s")
        print(f"Current:  {current['duration']:.2f}s")
        print(f"Change:   {current['duration'] - previous['duration']:+.2f}s")
        sys.exit(0)

    # Run tests with profiling
    run_data = tracker.run_tests_with_profiling(args.pytest_args)

    # Analyze results
    slow_tests = tracker.analyze_test_durations(run_data)

    # Generate report
    tracker.generate_report(run_data, slow_tests)
    tracker.suggest_improvements(slow_tests)

    # Save to history if requested
    if args.save_history:
        tracker.history["runs"].append(
            {
                "timestamp": run_data["timestamp"],
                "duration": run_data["duration"],
                "exit_code": run_data["exit_code"],
                "slow_tests": slow_tests[:10],
            }
        )
        tracker.save_history()
        print(f"\nPerformance data saved to {tracker.history_file}")

    sys.exit(run_data["exit_code"])


if __name__ == "__main__":
    main()
