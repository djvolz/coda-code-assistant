"""Observability CLI commands for Coda.

This module provides CLI commands for viewing metrics, health status,
and other observability data.
"""

import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .manager import ObservabilityManager
from .security import PathValidator, SecurityError


class ObservabilityCommands:
    """CLI commands for observability features."""

    def __init__(self, observability_manager: ObservabilityManager, console: Console):
        """Initialize observability commands.

        Args:
            observability_manager: Observability manager instance
            console: Rich console for output
        """
        self.obs_manager = observability_manager
        self.console = console

    def show_status(self):
        """Show overall observability status."""
        if not self.obs_manager.enabled:
            self.console.print(
                Panel(
                    "[yellow]Observability is disabled[/yellow]\n\n"
                    "To enable observability, add to your config:\n"
                    "[dim]observability.enabled = true[/dim]",
                    title="Observability Status",
                    border_style="yellow",
                )
            )
            return

        status = self.obs_manager.get_health_status()

        # Create status panel
        status_text = Text()
        status_text.append("Status: ", style="bold")
        status_text.append("Enabled", style="green")
        status_text.append(f"\nExport Directory: {status['observability']['export_directory']}")

        # Add component status
        if "components" in status["observability"]:
            status_text.append("\n\nComponents:")
            for component, comp_status in status["observability"]["components"].items():
                status_text.append(f"\n  • {component}: ")
                if comp_status.get("running", False):
                    status_text.append("Running", style="green")
                else:
                    status_text.append("Stopped", style="red")

        self.console.print(Panel(status_text, title="Observability Status", border_style="green"))

    def show_metrics(self, detailed: bool = False):
        """Show metrics summary.

        Args:
            detailed: Whether to show detailed metrics
        """
        if not self.obs_manager.enabled or not self.obs_manager.metrics_collector:
            self.console.print("[yellow]Metrics collection is not enabled[/yellow]")
            return

        metrics = self.obs_manager.metrics_collector

        # Session summary
        session_summary = metrics.get_session_summary()
        session_table = Table(title="Session Metrics")
        session_table.add_column("Metric", style="cyan")
        session_table.add_column("Value", style="magenta")

        session_table.add_row("Total Sessions", str(session_summary["total_sessions"]))
        session_table.add_row("Total Messages", str(session_summary["total_messages"]))
        session_table.add_row("Total Tokens", str(session_summary["total_tokens"]))
        session_table.add_row("Total Errors", str(session_summary["total_errors"]))

        self.console.print(session_table)

        # Provider summary
        provider_summary = metrics.get_provider_summary()
        if provider_summary:
            provider_table = Table(title="Provider Metrics")
            provider_table.add_column("Provider", style="cyan")
            provider_table.add_column("Requests", style="magenta")
            provider_table.add_column("Errors", style="red")
            provider_table.add_column("Avg Response (ms)", style="green")
            provider_table.add_column("Error Rate (%)", style="yellow")

            for provider, data in provider_summary.items():
                provider_table.add_row(
                    provider,
                    str(data["total_requests"]),
                    str(data["total_errors"]),
                    f"{data['average_response_time']:.2f}",
                    f"{data['error_rate']:.1f}",
                )

            self.console.print(provider_table)

        if detailed:
            # Error summary from metrics
            error_summary = metrics.get_error_summary()
            if error_summary["total_errors"] > 0:
                error_table = Table(title="Error Summary (Basic)")
                error_table.add_column("Error Type", style="red")
                error_table.add_column("Count", style="magenta")

                for error_type, count in error_summary["error_types"].items():
                    error_table.add_row(error_type, str(count))

                self.console.print(error_table)

            # Detailed error tracking if available
            if self.obs_manager.error_tracker:
                detailed_errors = self.obs_manager.get_error_summary(days=7)
                if detailed_errors.get("total_errors", 0) > 0:
                    detailed_table = Table(title="Detailed Error Analysis (Last 7 Days)")
                    detailed_table.add_column("Category", style="cyan")
                    detailed_table.add_column("Severity", style="yellow")
                    detailed_table.add_column("Count", style="magenta")

                    for category, count in detailed_errors.get("categories", {}).items():
                        detailed_table.add_row(category, "", str(count))

                    for severity, count in detailed_errors.get("severities", {}).items():
                        color = {
                            "low": "green",
                            "medium": "yellow",
                            "high": "red",
                            "critical": "bright_red",
                        }.get(severity, "white")
                        detailed_table.add_row("", f"[{color}]{severity}[/{color}]", str(count))

                    self.console.print(detailed_table)

            # Daily stats
            daily_stats = metrics.get_daily_stats(7)  # Last 7 days
            if daily_stats:
                daily_table = Table(title="Daily Statistics (Last 7 Days)")
                daily_table.add_column("Date", style="cyan")
                daily_table.add_column("Sessions", style="magenta")
                daily_table.add_column("Messages", style="green")
                daily_table.add_column("Tokens", style="blue")
                daily_table.add_column("Errors", style="red")

                for date, stats in daily_stats.items():
                    daily_table.add_row(
                        date,
                        str(stats.get("sessions_created", 0)),
                        str(stats.get("messages_sent", 0)),
                        str(stats.get("total_tokens", 0)),
                        str(stats.get("errors", 0)),
                    )

                self.console.print(daily_table)

    def show_health(self, component: str | None = None):
        """Show health status.

        Args:
            component: Specific component to show (optional)
        """
        if not self.obs_manager.enabled or not self.obs_manager.health_monitor:
            self.console.print("[yellow]Health monitoring is not enabled[/yellow]")
            return

        health_monitor = self.obs_manager.health_monitor

        if component:
            # Show specific component health
            comp_health = health_monitor.get_component_health(component)
            if "error" in comp_health:
                self.console.print(f"[red]{comp_health['error']}[/red]")
                return

            # Create component panel
            status_color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(
                comp_health["status"], "white"
            )

            health_text = Text()
            health_text.append(f"Status: {comp_health['status']}", style=status_color)
            health_text.append(f"\nUptime: {comp_health['uptime_percentage']:.1f}%")
            health_text.append(f"\nLast Check: {comp_health['last_check']}")
            health_text.append(f"\nRecent Checks: {len(comp_health['checks'])}")

            self.console.print(
                Panel(health_text, title=f"Health Status: {component}", border_style=status_color)
            )
        else:
            # Show overall health
            overall_health = health_monitor.get_overall_health()
            status_color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(
                overall_health["status"], "white"
            )

            self.console.print(
                Panel(
                    f"[{status_color}]{overall_health['message']}[/{status_color}]\n\n"
                    f"Components: {overall_health.get('component_count', 0)}\n"
                    f"Healthy: {overall_health.get('healthy_count', 0)}\n"
                    f"Degraded: {overall_health.get('degraded_count', 0)}\n"
                    f"Unhealthy: {overall_health.get('unhealthy_count', 0)}",
                    title="Overall Health",
                    border_style=status_color,
                )
            )

            # Show component details
            component_health = health_monitor.get_component_health()
            if component_health:
                health_table = Table(title="Component Health Details")
                health_table.add_column("Component", style="cyan")
                health_table.add_column("Status", style="bold")
                health_table.add_column("Uptime %", style="green")
                health_table.add_column("Last Check", style="dim")

                for comp_name, comp_data in component_health.items():
                    status_style = {
                        "healthy": "green",
                        "degraded": "yellow",
                        "unhealthy": "red",
                    }.get(comp_data["status"], "white")

                    health_table.add_row(
                        comp_name,
                        f"[{status_style}]{comp_data['status']}[/{status_style}]",
                        f"{comp_data['uptime_percentage']:.1f}%",
                        comp_data["last_check"],
                    )

                self.console.print(health_table)

    def show_traces(self, limit: int = 10):
        """Show recent traces.

        Args:
            limit: Number of traces to show
        """
        if not self.obs_manager.enabled or not self.obs_manager.tracing_manager:
            self.console.print("[yellow]Tracing is not enabled[/yellow]")
            return

        tracing_manager = self.obs_manager.tracing_manager

        # Get trace summary
        trace_summary = tracing_manager.get_trace_summary()

        summary_table = Table(title="Trace Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")

        summary_table.add_row("Total Traces", str(trace_summary["total_traces"]))
        summary_table.add_row("Total Spans", str(trace_summary["total_spans"]))
        summary_table.add_row("Active Spans", str(trace_summary["active_spans"]))
        summary_table.add_row("Avg Duration (ms)", f"{trace_summary['average_duration_ms']:.2f}")

        self.console.print(summary_table)

        # Get recent traces
        recent_traces = tracing_manager.get_recent_traces(limit)
        if recent_traces:
            traces_table = Table(title=f"Recent Traces (Last {len(recent_traces)})")
            traces_table.add_column("Trace ID", style="cyan")
            traces_table.add_column("Spans", style="magenta")
            traces_table.add_column("Duration (ms)", style="green")
            traces_table.add_column("Operations", style="dim")

            for trace in recent_traces:
                operations = set()
                for span in trace["spans"]:
                    operations.add(span["operation_name"])

                traces_table.add_row(
                    trace["trace_id"][:16] + "...",  # Truncate trace ID
                    str(trace["span_count"]),
                    f"{trace.get('duration_ms', 0):.2f}",
                    ", ".join(list(operations)[:3]) + ("..." if len(operations) > 3 else ""),
                )

            self.console.print(traces_table)

    def export_data(self, format: str = "json", output_file: str | None = None):
        """Export observability data.

        Args:
            format: Export format (json, summary)
            output_file: Output file path (optional)
        """
        if not self.obs_manager.enabled:
            self.console.print("[yellow]Observability is not enabled[/yellow]")
            return

        # Validate output file path if provided
        if output_file:
            try:
                from pathlib import Path

                output_path = Path(output_file)

                # Validate filename
                PathValidator.validate_filename(
                    output_path.name, allowed_extensions=[".json", ".txt"]
                )

                # If path has parent directories, validate them
                if output_path.parent != Path("."):
                    # Use current directory as base for validation
                    PathValidator.validate_export_path(output_path, Path.cwd())
            except SecurityError as e:
                self.console.print(f"[red]Invalid output path: {e}[/red]")
                return

        data = {}

        # Collect data from all components
        if self.obs_manager.metrics_collector:
            data["metrics"] = {
                "sessions": self.obs_manager.metrics_collector.get_session_summary(),
                "providers": self.obs_manager.metrics_collector.get_provider_summary(),
                "errors": self.obs_manager.metrics_collector.get_error_summary(),
                "daily_stats": self.obs_manager.metrics_collector.get_daily_stats(30),
            }

        if self.obs_manager.tracing_manager:
            data["tracing"] = {
                "summary": self.obs_manager.tracing_manager.get_trace_summary(),
                "recent_traces": self.obs_manager.tracing_manager.get_recent_traces(20),
            }

        if self.obs_manager.health_monitor:
            data["health"] = {
                "overall": self.obs_manager.health_monitor.get_overall_health(),
                "components": self.obs_manager.health_monitor.get_component_health(),
            }

        data["status"] = self.obs_manager.get_health_status()

        if format == "json":
            if output_file:
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2, default=str)
                self.console.print(f"[green]Data exported to {output_file}[/green]")
            else:
                self.console.print(Syntax(json.dumps(data, indent=2, default=str), "json"))

        elif format == "summary":
            # Print a summary view
            tree = Tree("Observability Data Summary")

            if "metrics" in data:
                metrics_branch = tree.add("Metrics")
                sessions = data["metrics"]["sessions"]
                metrics_branch.add(f"Sessions: {sessions['total_sessions']}")
                metrics_branch.add(f"Messages: {sessions['total_messages']}")
                metrics_branch.add(f"Tokens: {sessions['total_tokens']}")
                metrics_branch.add(f"Errors: {sessions['total_errors']}")

            if "health" in data:
                health_branch = tree.add("Health")
                overall = data["health"]["overall"]
                health_branch.add(f"Status: {overall['status']}")
                health_branch.add(f"Components: {overall.get('component_count', 0)}")

            if "tracing" in data:
                tracing_branch = tree.add("Tracing")
                summary = data["tracing"]["summary"]
                tracing_branch.add(f"Traces: {summary['total_traces']}")
                tracing_branch.add(f"Spans: {summary['total_spans']}")
                tracing_branch.add(f"Avg Duration: {summary['average_duration_ms']:.2f}ms")

            self.console.print(tree)

        else:
            self.console.print(f"[red]Unknown format: {format}[/red]")
            self.console.print("Available formats: json, summary")

    def show_errors(self, limit: int = 20, days: int = 7):
        """Show recent errors and error analysis.

        Args:
            limit: Number of recent errors to show
            days: Number of days for error summary
        """
        if not self.obs_manager.enabled or not self.obs_manager.error_tracker:
            self.console.print("[yellow]Error tracking is not enabled[/yellow]")
            return

        # Get error summary
        error_summary = self.obs_manager.get_error_summary(days)

        if error_summary.get("total_errors", 0) == 0:
            self.console.print(f"[green]No errors recorded in the last {days} days[/green]")
            return

        # Summary table
        summary_table = Table(title=f"Error Summary (Last {days} Days)")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")

        summary_table.add_row("Total Errors", str(error_summary["total_errors"]))
        summary_table.add_row("Unique Error Types", str(len(error_summary["error_types"])))
        summary_table.add_row("Categories", str(len(error_summary["categories"])))

        self.console.print(summary_table)

        # Top errors
        if error_summary["top_errors"]:
            top_table = Table(title="Top Error Types")
            top_table.add_column("Error Type", style="red")
            top_table.add_column("Count", style="magenta")

            for error_type, count in error_summary["top_errors"][:10]:
                top_table.add_row(error_type, str(count))

            self.console.print(top_table)

        # Category breakdown
        if error_summary["categories"]:
            category_table = Table(title="Errors by Category")
            category_table.add_column("Category", style="cyan")
            category_table.add_column("Count", style="magenta")

            for category, count in error_summary["categories"].items():
                category_table.add_row(category, str(count))

            self.console.print(category_table)

        # Severity breakdown
        if error_summary["severities"]:
            severity_table = Table(title="Errors by Severity")
            severity_table.add_column("Severity", style="yellow")
            severity_table.add_column("Count", style="magenta")

            for severity, count in error_summary["severities"].items():
                color = {
                    "low": "green",
                    "medium": "yellow",
                    "high": "red",
                    "critical": "bright_red",
                }.get(severity, "white")
                severity_table.add_row(f"[{color}]{severity}[/{color}]", str(count))

            self.console.print(severity_table)

        # Recent errors
        recent_errors = self.obs_manager.get_recent_errors(limit)
        if recent_errors:
            recent_table = Table(title=f"Recent Errors (Last {len(recent_errors)})")
            recent_table.add_column("Time", style="dim")
            recent_table.add_column("Type", style="red")
            recent_table.add_column("Category", style="cyan")
            recent_table.add_column("Severity", style="yellow")
            recent_table.add_column("Message", style="white")

            for error in recent_errors[:limit]:
                # Parse timestamp
                try:
                    from datetime import datetime

                    timestamp = datetime.fromisoformat(error["timestamp"])
                    time_str = timestamp.strftime("%H:%M:%S")
                except Exception:
                    time_str = "Unknown"

                severity = error["severity"]
                severity_color = {
                    "low": "green",
                    "medium": "yellow",
                    "high": "red",
                    "critical": "bright_red",
                }.get(severity, "white")

                # Truncate long messages
                message = error["error_message"]
                if len(message) > 60:
                    message = message[:57] + "..."

                recent_table.add_row(
                    time_str,
                    error["error_type"],
                    error["category"],
                    f"[{severity_color}]{severity}[/{severity_color}]",
                    message,
                )

            self.console.print(recent_table)

    def show_performance(self, limit: int = 20):
        """Show performance profiling data.

        Args:
            limit: Number of functions to show
        """
        if not self.obs_manager.enabled or not self.obs_manager.profiler:
            self.console.print("[yellow]Performance profiling is not enabled[/yellow]")
            self.console.print("Enable with: [dim]observability.profiling.enabled = true[/dim]")
            return

        # Get performance summary
        perf_summary = self.obs_manager.get_performance_summary()

        if perf_summary.get("total_calls", 0) == 0:
            self.console.print("[green]No profiling data available[/green]")
            self.console.print("Profiling may be disabled or no functions have been profiled yet.")
            return

        # Summary table
        summary_table = Table(title="Performance Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")

        summary_table.add_row("Total Calls", str(perf_summary["total_calls"]))
        summary_table.add_row("Unique Functions", str(perf_summary["unique_functions"]))
        summary_table.add_row("Total Time (ms)", f"{perf_summary['total_time_ms']:.2f}")
        summary_table.add_row("Avg Call Time (ms)", f"{perf_summary['avg_call_time_ms']:.2f}")
        summary_table.add_row(
            "Min Duration Threshold (ms)", f"{perf_summary['min_duration_threshold_ms']:.1f}"
        )
        summary_table.add_row("Memory Tracking", "Yes" if perf_summary["memory_tracking"] else "No")

        self.console.print(summary_table)

        # Function statistics
        function_stats = self.obs_manager.get_function_stats(limit)
        if function_stats:
            func_table = Table(title=f"Top {len(function_stats)} Functions by Total Time")
            func_table.add_column("Function", style="cyan")
            func_table.add_column("Calls", style="magenta")
            func_table.add_column("Total (ms)", style="red")
            func_table.add_column("Avg (ms)", style="yellow")
            func_table.add_column("Min (ms)", style="green")
            func_table.add_column("Max (ms)", style="blue")

            for stats in function_stats:
                # Truncate long function names
                func_name = stats["function_name"]
                if len(func_name) > 40:
                    func_name = "..." + func_name[-37:]

                func_table.add_row(
                    func_name,
                    str(stats["call_count"]),
                    f"{stats['total_time_ms']:.2f}",
                    f"{stats['avg_time_ms']:.2f}",
                    f"{stats['min_time_ms']:.2f}",
                    f"{stats['max_time_ms']:.2f}",
                )

            self.console.print(func_table)

        # Performance hotspots (last 10 minutes)
        hotspots = self.obs_manager.get_performance_hotspots(10)
        if hotspots:
            hotspot_table = Table(title="Recent Performance Hotspots (Last 10 Minutes)")
            hotspot_table.add_column("Function", style="cyan")
            hotspot_table.add_column("Calls", style="magenta")
            hotspot_table.add_column("Total (ms)", style="red")
            hotspot_table.add_column("Avg (ms)", style="yellow")

            for hotspot in hotspots[:10]:  # Show top 10
                func_name = hotspot["function"]
                if len(func_name) > 40:
                    func_name = "..." + func_name[-37:]

                hotspot_table.add_row(
                    func_name,
                    str(hotspot["call_count"]),
                    f"{hotspot['total_time_ms']:.2f}",
                    f"{hotspot['avg_time_ms']:.2f}",
                )

            self.console.print(hotspot_table)
