#!/usr/bin/env python3
"""
Collect CI/CD metrics from GitHub Actions for monitoring test infrastructure performance.

This script collects metrics including:
- Workflow execution times
- Test success/failure rates
- Number of tests run
- Trend analysis over time
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import requests
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    print("Error: Required packages not installed. Please run:")
    print("  pip install requests rich")
    sys.exit(1)

console = Console()

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = os.getenv("GITHUB_REPOSITORY_OWNER", "anthropics")
REPO_NAME = os.getenv("GITHUB_REPOSITORY_NAME", "coda-code-assistant")

# Metrics storage
METRICS_DIR = Path.home() / ".coda" / "metrics"
METRICS_FILE = METRICS_DIR / "ci_metrics.json"

# Performance targets (from plan)
TARGETS = {
    "avg_pr_validation_time": 120,  # 2 minutes in seconds
    "test_flakiness_rate": 0.01,  # 1%
    "ci_compute_reduction": 0.60,  # 60% reduction
    "developer_wait_reduction": 0.80,  # 80% reduction
    "full_suite_time": 600,  # 10 minutes in seconds
}


class GitHubMetricsCollector:
    """Collect metrics from GitHub Actions API."""

    def __init__(self, token: str | None = None):
        self.token = token or GITHUB_TOKEN
        self.headers = {}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
        self.headers["Accept"] = "application/vnd.github.v3+json"

    def get_workflow_runs(
        self, workflow_name: str | None = None, branch: str | None = None, days_back: int = 7
    ) -> list[dict[str, Any]]:
        """Get workflow runs from the past N days."""
        runs = []
        since = datetime.now(UTC) - timedelta(days=days_back)

        params = {
            "created": f">{since.isoformat()}",
            "per_page": 100,
        }

        if branch:
            params["branch"] = branch

        url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching workflow runs...", total=None)

            while url:
                response = requests.get(url, headers=self.headers, params=params)
                response.raise_for_status()

                data = response.json()
                workflow_runs = data.get("workflow_runs", [])

                for run in workflow_runs:
                    if workflow_name and workflow_name not in run["name"]:
                        continue
                    runs.append(run)

                # Check for pagination
                url = None
                if "Link" in response.headers:
                    links = response.headers["Link"].split(",")
                    for link in links:
                        if 'rel="next"' in link:
                            url = link.split(";")[0].strip("<>")
                            params = {}  # Clear params for next page
                            break

                progress.update(task, description=f"Fetched {len(runs)} runs...")

        return runs

    def get_workflow_jobs(self, run_id: int) -> list[dict[str, Any]]:
        """Get jobs for a specific workflow run."""
        url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/jobs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("jobs", [])

    def get_workflow_logs_analysis(self, run_id: int) -> dict[str, Any]:
        """Analyze workflow logs to extract test metrics."""
        # Note: Logs API requires authentication and returns a redirect to download
        # For now, we'll return mock data structure
        return {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "coverage_percent": 0.0,
        }


class MetricsAnalyzer:
    """Analyze collected metrics and generate insights."""

    def __init__(self):
        self.metrics_data = self._load_metrics()

    def _load_metrics(self) -> dict[str, Any]:
        """Load existing metrics from file."""
        if METRICS_FILE.exists():
            with open(METRICS_FILE) as f:
                return json.load(f)
        return {"runs": [], "summary": {}}

    def _save_metrics(self):
        """Save metrics to file."""
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "w") as f:
            json.dump(self.metrics_data, f, indent=2)

    def add_workflow_runs(self, runs: list[dict[str, Any]]):
        """Add new workflow runs to metrics."""
        existing_ids = {run["id"] for run in self.metrics_data["runs"]}

        for run in runs:
            if run["id"] not in existing_ids:
                metrics = {
                    "id": run["id"],
                    "name": run["name"],
                    "branch": run["head_branch"],
                    "status": run["status"],
                    "conclusion": run["conclusion"],
                    "created_at": run["created_at"],
                    "updated_at": run["updated_at"],
                    "run_started_at": run["run_started_at"],
                    "duration_seconds": self._calculate_duration(run),
                    "event": run["event"],
                    "commit_sha": run["head_sha"][:8],
                }
                self.metrics_data["runs"].append(metrics)

        # Keep only recent runs (last 30 days)
        cutoff = datetime.now(UTC) - timedelta(days=30)
        self.metrics_data["runs"] = [
            run
            for run in self.metrics_data["runs"]
            if datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) > cutoff
        ]

        # Sort by creation date
        self.metrics_data["runs"].sort(key=lambda x: x["created_at"], reverse=True)

        self._save_metrics()

    def _calculate_duration(self, run: dict[str, Any]) -> float | None:
        """Calculate workflow duration in seconds."""
        if run["status"] != "completed":
            return None

        start = datetime.fromisoformat(run["run_started_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
        return (end - start).total_seconds()

    def generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        runs = self.metrics_data["runs"]
        if not runs:
            return {}

        # Filter completed runs
        completed_runs = [r for r in runs if r["status"] == "completed"]
        pr_runs = [r for r in completed_runs if r["event"] == "pull_request"]

        # Calculate metrics
        summary = {
            "total_runs": len(runs),
            "total_completed": len(completed_runs),
            "success_rate": self._calculate_success_rate(completed_runs),
            "avg_duration": self._calculate_avg_duration(completed_runs),
            "avg_pr_validation_time": self._calculate_avg_duration(pr_runs),
            "by_workflow": self._group_by_workflow(completed_runs),
            "by_day": self._group_by_day(runs),
            "flakiness_rate": self._calculate_flakiness_rate(completed_runs),
        }

        self.metrics_data["summary"] = summary
        self._save_metrics()

        return summary

    def _calculate_success_rate(self, runs: list[dict[str, Any]]) -> float:
        """Calculate success rate of completed runs."""
        if not runs:
            return 0.0
        successful = sum(1 for r in runs if r["conclusion"] == "success")
        return successful / len(runs)

    def _calculate_avg_duration(self, runs: list[dict[str, Any]]) -> float:
        """Calculate average duration of completed runs."""
        durations = [r["duration_seconds"] for r in runs if r["duration_seconds"]]
        return sum(durations) / len(durations) if durations else 0.0

    def _group_by_workflow(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Group metrics by workflow name."""
        workflows = defaultdict(list)
        for run in runs:
            workflows[run["name"]].append(run)

        result = {}
        for name, workflow_runs in workflows.items():
            result[name] = {
                "count": len(workflow_runs),
                "success_rate": self._calculate_success_rate(workflow_runs),
                "avg_duration": self._calculate_avg_duration(workflow_runs),
            }

        return result

    def _group_by_day(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Group metrics by day."""
        days = defaultdict(list)
        for run in runs:
            date = run["created_at"].split("T")[0]
            days[date].append(run)

        result = {}
        for date, day_runs in sorted(days.items()):
            completed = [r for r in day_runs if r["status"] == "completed"]
            result[date] = {
                "total_runs": len(day_runs),
                "success_rate": self._calculate_success_rate(completed),
                "avg_duration": self._calculate_avg_duration(completed),
            }

        return result

    def _calculate_flakiness_rate(self, runs: list[dict[str, Any]]) -> float:
        """Estimate test flakiness rate based on failures."""
        # Simple heuristic: Look for runs that failed but succeeded on retry
        # Group by commit SHA
        by_commit = defaultdict(list)
        for run in runs:
            by_commit[run["commit_sha"]].append(run)

        flaky_commits = 0
        total_commits = 0

        for _commit, commit_runs in by_commit.items():
            if len(commit_runs) > 1:
                total_commits += 1
                conclusions = [r["conclusion"] for r in commit_runs]
                if "failure" in conclusions and "success" in conclusions:
                    flaky_commits += 1

        return flaky_commits / total_commits if total_commits > 0 else 0.0


def display_dashboard(summary: dict[str, Any]):
    """Display metrics dashboard in the terminal."""
    console.print(Panel.fit("🎯 CI/CD Metrics Dashboard", style="bold blue"))

    # Overall metrics
    overall_table = Table(title="Overall Metrics", show_header=True)
    overall_table.add_column("Metric", style="cyan")
    overall_table.add_column("Value", style="yellow")
    overall_table.add_column("Target", style="green")
    overall_table.add_column("Status", style="white")

    # Success rate
    success_rate = summary.get("success_rate", 0) * 100
    overall_table.add_row(
        "Success Rate", f"{success_rate:.1f}%", ">95%", "✅" if success_rate > 95 else "⚠️"
    )

    # Average PR validation time
    avg_pr_time = summary.get("avg_pr_validation_time", 0)
    overall_table.add_row(
        "Avg PR Validation Time",
        f"{avg_pr_time/60:.1f}m",
        f"{TARGETS['avg_pr_validation_time']/60}m",
        "✅" if avg_pr_time < TARGETS["avg_pr_validation_time"] else "❌",
    )

    # Test flakiness
    flakiness = summary.get("flakiness_rate", 0) * 100
    overall_table.add_row(
        "Test Flakiness Rate",
        f"{flakiness:.2f}%",
        f"{TARGETS['test_flakiness_rate']*100}%",
        "✅" if flakiness < TARGETS["test_flakiness_rate"] * 100 else "❌",
    )

    console.print(overall_table)
    console.print()

    # Workflow breakdown
    if "by_workflow" in summary:
        workflow_table = Table(title="Metrics by Workflow", show_header=True)
        workflow_table.add_column("Workflow", style="cyan")
        workflow_table.add_column("Runs", style="yellow")
        workflow_table.add_column("Success Rate", style="green")
        workflow_table.add_column("Avg Duration", style="magenta")

        for name, metrics in summary["by_workflow"].items():
            workflow_table.add_row(
                name,
                str(metrics["count"]),
                f"{metrics['success_rate']*100:.1f}%",
                f"{metrics['avg_duration']/60:.1f}m",
            )

        console.print(workflow_table)
        console.print()

    # Recent trends
    if "by_day" in summary:
        trend_table = Table(title="7-Day Trend", show_header=True)
        trend_table.add_column("Date", style="cyan")
        trend_table.add_column("Runs", style="yellow")
        trend_table.add_column("Success Rate", style="green")
        trend_table.add_column("Avg Duration", style="magenta")

        # Show last 7 days
        days = sorted(summary["by_day"].items(), reverse=True)[:7]
        for date, metrics in reversed(days):
            trend_table.add_row(
                date,
                str(metrics["total_runs"]),
                f"{metrics['success_rate']*100:.1f}%",
                f"{metrics['avg_duration']/60:.1f}m" if metrics["avg_duration"] > 0 else "N/A",
            )

        console.print(trend_table)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Collect and analyze CI/CD metrics")
    parser.add_argument(
        "--days", type=int, default=7, help="Number of days to collect (default: 7)"
    )
    parser.add_argument("--workflow", help="Filter by workflow name")
    parser.add_argument("--branch", help="Filter by branch name")
    parser.add_argument("--no-fetch", action="store_true", help="Skip fetching new data")
    parser.add_argument("--export", help="Export metrics to JSON file")

    args = parser.parse_args()

    # Check for GitHub token
    if not GITHUB_TOKEN and not args.no_fetch:
        console.print("[yellow]Warning: GITHUB_TOKEN not set. API rate limits will apply.[/yellow]")
        console.print("Set GITHUB_TOKEN environment variable for better access.")
        console.print()

    analyzer = MetricsAnalyzer()

    # Fetch new data
    if not args.no_fetch:
        try:
            collector = GitHubMetricsCollector()
            runs = collector.get_workflow_runs(
                workflow_name=args.workflow, branch=args.branch, days_back=args.days
            )

            console.print(f"[green]Collected {len(runs)} workflow runs[/green]")
            analyzer.add_workflow_runs(runs)

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching data from GitHub: {e}[/red]")
            if not analyzer.metrics_data["runs"]:
                sys.exit(1)
            console.print("[yellow]Using cached data...[/yellow]")

    # Generate summary
    summary = analyzer.generate_summary()

    if not summary:
        console.print(
            "[yellow]No metrics data available. Run without --no-fetch to collect data.[/yellow]"
        )
        sys.exit(1)

    # Display dashboard
    display_dashboard(summary)

    # Export if requested
    if args.export:
        export_path = Path(args.export)
        with open(export_path, "w") as f:
            json.dump(
                {
                    "summary": summary,
                    "generated_at": datetime.now().isoformat(),
                    "parameters": {
                        "days": args.days,
                        "workflow": args.workflow,
                        "branch": args.branch,
                    },
                },
                f,
                indent=2,
            )
        console.print(f"\n[green]Metrics exported to: {export_path}[/green]")


if __name__ == "__main__":
    main()
