#!/usr/bin/env python3
"""
Generate an HTML dashboard from collected CI/CD metrics.

This script creates a visual dashboard showing:
- Performance trends over time
- Success/failure rates
- Workflow comparisons
- Achievement of performance targets
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coda CI/CD Metrics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .metric-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-target {
            font-size: 0.9em;
            color: #999;
        }
        .metric-good { color: #22c55e; }
        .metric-warning { color: #f59e0b; }
        .metric-bad { color: #ef4444; }
        .chart-container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .chart-title {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 15px;
            color: #333;
        }
        .workflow-table {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #eee;
        }
        th {
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }
        .timestamp {
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-top: 40px;
        }
        .legend {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 10px;
            font-size: 0.9em;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .legend-color {
            width: 20px;
            height: 12px;
            border-radius: 2px;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>🚀 Coda CI/CD Metrics Dashboard</h1>
        
        <div class="metrics-grid">
            {metric_cards}
        </div>
        
        <div class="chart-container">
            <div class="chart-title">Success Rate Trend (7 Days)</div>
            <canvas id="successTrendChart" height="100"></canvas>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">Average Workflow Duration (minutes)</div>
            <canvas id="durationChart" height="100"></canvas>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">Daily Run Volume</div>
            <canvas id="volumeChart" height="100"></canvas>
        </div>
        
        <div class="workflow-table">
            <div class="chart-title">Workflow Performance</div>
            <table>
                <thead>
                    <tr>
                        <th>Workflow</th>
                        <th>Runs</th>
                        <th>Success Rate</th>
                        <th>Avg Duration</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {workflow_rows}
                </tbody>
            </table>
        </div>
        
        <div class="timestamp">
            Generated at: {timestamp}
        </div>
    </div>
    
    <script>
        // Chart configuration
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        };
        
        // Success rate trend chart
        const successCtx = document.getElementById('successTrendChart').getContext('2d');
        new Chart(successCtx, {
            type: 'line',
            data: {
                labels: {dates},
                datasets: [{
                    label: 'Success Rate %',
                    data: {success_rates},
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.3
                }]
            },
            options: {
                ...chartOptions,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
        
        // Duration chart
        const durationCtx = document.getElementById('durationChart').getContext('2d');
        new Chart(durationCtx, {
            type: 'bar',
            data: {
                labels: {workflow_names},
                datasets: [{
                    label: 'Average Duration (minutes)',
                    data: {workflow_durations},
                    backgroundColor: '#3b82f6'
                }]
            },
            options: chartOptions
        });
        
        // Volume chart
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        new Chart(volumeCtx, {
            type: 'bar',
            data: {
                labels: {dates},
                datasets: [{
                    label: 'Total Runs',
                    data: {daily_volumes},
                    backgroundColor: '#8b5cf6'
                }]
            },
            options: chartOptions
        });
    </script>
</body>
</html>
"""


def generate_metric_card(label: str, value: str, target: str = None, status: str = "good") -> str:
    """Generate HTML for a metric card."""
    status_class = f"metric-{status}"
    target_html = f'<div class="metric-target">Target: {target}</div>' if target else ''
    
    return f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value {status_class}">{value}</div>
            {target_html}
        </div>
    """


def determine_status(value: float, target: float, higher_is_better: bool = True) -> str:
    """Determine metric status based on value and target."""
    if higher_is_better:
        if value >= target:
            return "good"
        elif value >= target * 0.9:
            return "warning"
        else:
            return "bad"
    else:
        if value <= target:
            return "good"
        elif value <= target * 1.1:
            return "warning"
        else:
            return "bad"


def generate_workflow_row(name: str, metrics: Dict[str, Any]) -> str:
    """Generate table row for workflow metrics."""
    success_rate = metrics.get("success_rate", 0) * 100
    avg_duration = metrics.get("avg_duration", 0) / 60
    
    status_icon = "✅" if success_rate > 95 else "⚠️" if success_rate > 80 else "❌"
    
    return f"""
        <tr>
            <td>{name}</td>
            <td>{metrics.get("count", 0)}</td>
            <td>{success_rate:.1f}%</td>
            <td>{avg_duration:.1f}m</td>
            <td>{status_icon}</td>
        </tr>
    """


def generate_dashboard(metrics_data: Dict[str, Any], output_file: Path):
    """Generate HTML dashboard from metrics data."""
    summary = metrics_data.get("summary", {})
    
    # Generate metric cards
    metric_cards = []
    
    # Success rate
    success_rate = summary.get("success_rate", 0) * 100
    metric_cards.append(generate_metric_card(
        "Success Rate",
        f"{success_rate:.1f}%",
        ">95%",
        determine_status(success_rate, 95)
    ))
    
    # PR validation time
    pr_time = summary.get("avg_pr_validation_time", 0) / 60
    metric_cards.append(generate_metric_card(
        "Avg PR Validation",
        f"{pr_time:.1f}m",
        "<2m",
        determine_status(pr_time, 2, higher_is_better=False)
    ))
    
    # Test flakiness
    flakiness = summary.get("flakiness_rate", 0) * 100
    metric_cards.append(generate_metric_card(
        "Test Flakiness",
        f"{flakiness:.2f}%",
        "<1%",
        determine_status(flakiness, 1, higher_is_better=False)
    ))
    
    # Total runs
    total_runs = summary.get("total_runs", 0)
    metric_cards.append(generate_metric_card(
        "Total Runs (7d)",
        str(total_runs)
    ))
    
    # Prepare chart data
    by_day = summary.get("by_day", {})
    dates = sorted(by_day.keys())[-7:]  # Last 7 days
    success_rates = [by_day[date]["success_rate"] * 100 for date in dates]
    daily_volumes = [by_day[date]["total_runs"] for date in dates]
    
    # Workflow data
    by_workflow = summary.get("by_workflow", {})
    workflow_names = list(by_workflow.keys())
    workflow_durations = [by_workflow[w]["avg_duration"] / 60 for w in workflow_names]
    
    # Generate workflow rows
    workflow_rows = []
    for name, metrics in sorted(by_workflow.items(), key=lambda x: x[1]["count"], reverse=True):
        workflow_rows.append(generate_workflow_row(name, metrics))
    
    # Fill in template
    html = DASHBOARD_TEMPLATE.format(
        metric_cards="".join(metric_cards),
        workflow_rows="".join(workflow_rows),
        dates=json.dumps(dates),
        success_rates=json.dumps(success_rates),
        daily_volumes=json.dumps(daily_volumes),
        workflow_names=json.dumps(workflow_names),
        workflow_durations=json.dumps(workflow_durations),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    
    # Write dashboard
    output_file.write_text(html)
    print(f"Dashboard generated: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate HTML dashboard from CI metrics")
    parser.add_argument("metrics_file", help="Path to metrics JSON file")
    parser.add_argument("-o", "--output", default="metrics-dashboard.html", help="Output HTML file")
    
    args = parser.parse_args()
    
    # Load metrics
    metrics_file = Path(args.metrics_file)
    if not metrics_file.exists():
        print(f"Error: Metrics file not found: {metrics_file}")
        sys.exit(1)
    
    with open(metrics_file, "r") as f:
        metrics_data = json.load(f)
    
    # Generate dashboard
    output_file = Path(args.output)
    generate_dashboard(metrics_data, output_file)


if __name__ == "__main__":
    main()