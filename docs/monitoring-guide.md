# CI/CD Monitoring Guide

This guide explains how to use the monitoring tools implemented in Phase 6 of the test infrastructure project to track and improve CI/CD performance.

## Overview

The monitoring system provides comprehensive insights into:
- Workflow execution times and success rates
- Test performance and flakiness
- Trends over time
- Achievement of performance targets

## Components

### 1. CI Metrics Collector (`scripts/collect_ci_metrics.py`)

Collects metrics from GitHub Actions API including:
- Workflow run durations
- Success/failure rates
- Test execution statistics
- Performance trends

#### Usage

```bash
# Collect metrics for the last 7 days
python scripts/collect_ci_metrics.py

# Collect metrics for specific workflow
python scripts/collect_ci_metrics.py --workflow "CI" --days 14

# Export metrics to JSON
python scripts/collect_ci_metrics.py --export metrics-report.json

# Use cached data without fetching
python scripts/collect_ci_metrics.py --no-fetch
```

#### Requirements

- `GITHUB_TOKEN` environment variable (optional but recommended)
- Python packages: `requests`, `rich`

### 2. Dashboard Generator (`scripts/generate_metrics_dashboard.py`)

Creates an interactive HTML dashboard from collected metrics.

#### Usage

```bash
# Generate dashboard from metrics
python scripts/generate_metrics_dashboard.py metrics-report.json

# Specify output file
python scripts/generate_metrics_dashboard.py metrics-report.json -o dashboard.html
```

The dashboard includes:
- Key performance indicators (KPIs)
- Success rate trends
- Workflow duration comparisons
- Daily run volume charts
- Performance against targets

### 3. Test Metrics Collector (`scripts/test_metrics_collector.py`)

Pytest plugin that collects detailed test execution metrics.

#### Usage

```bash
# Run tests with metrics collection
pytest --metrics

# Analyze test trends
python scripts/test_metrics_collector.py --analyze
```

Collects:
- Individual test execution times
- Pass/fail statistics by module
- Identification of slow tests
- Historical trends

### 4. Automated Collection Workflow

GitHub Actions workflow that runs daily to collect metrics automatically.

#### Manual Trigger

```bash
# Trigger via GitHub CLI
gh workflow run collect-metrics.yml -f days=30

# Or via GitHub UI
# Actions → Collect CI Metrics → Run workflow
```

## Performance Targets

The monitoring system tracks progress against these targets:

| Metric | Target | Description |
|--------|--------|-------------|
| Average PR Validation Time | < 2 minutes | Time from PR push to initial feedback |
| Test Flakiness Rate | < 1% | Percentage of tests that fail intermittently |
| CI Compute Minutes | 60% reduction | Reduction in GitHub Actions minutes used |
| Developer Wait Time | 80% reduction | Time developers wait for CI feedback |
| Full Test Suite | < 10 minutes | Complete test suite execution time |

## Metrics Storage

Metrics are stored in:
- **Local**: `~/.coda/metrics/ci_metrics.json`
- **GitHub Artifacts**: Available for 90 days after each workflow run
- **Test Metrics**: `~/.coda/test_metrics/`

## Dashboard Features

### Key Metrics Cards
- Success Rate with target comparison
- Average PR validation time
- Test flakiness rate
- Total run volume

### Trend Charts
- 7-day success rate trend
- Workflow duration comparison
- Daily run volume

### Workflow Performance Table
- Individual workflow statistics
- Success rates by workflow
- Average durations
- Visual status indicators

## Best Practices

### 1. Regular Monitoring
- Review dashboard weekly
- Set up alerts for degraded performance
- Track trends after major changes

### 2. Performance Optimization
- Focus on workflows with lowest success rates
- Identify and optimize slow tests
- Reduce flaky test occurrences

### 3. Data Collection
- Ensure `GITHUB_TOKEN` is set for complete data
- Run collection script regularly (automated via workflow)
- Keep historical data for trend analysis

## Troubleshooting

### No Data Available
- Check `GITHUB_TOKEN` is set correctly
- Verify repository permissions
- Ensure workflows have been running

### Incomplete Metrics
- API rate limits may apply without token
- Some metrics require multiple runs for trends
- Flakiness detection needs repeated runs

### Dashboard Issues
- Ensure all JavaScript libraries load
- Check browser console for errors
- Verify JSON data format

## Example Workflow

1. **Daily Automated Collection**
   ```yaml
   # Runs at midnight UTC
   - cron: '0 0 * * *'
   ```

2. **Weekly Review Process**
   ```bash
   # Collect latest metrics
   python scripts/collect_ci_metrics.py --days 7
   
   # Generate dashboard
   python scripts/generate_metrics_dashboard.py metrics-report.json
   
   # Open in browser
   open metrics-dashboard.html
   ```

3. **Performance Investigation**
   ```bash
   # Analyze specific workflow
   python scripts/collect_ci_metrics.py --workflow "CI" --days 30
   
   # Check test performance
   python scripts/test_metrics_collector.py --analyze
   ```

## Integration with CI/CD

The metrics system integrates with the optimized CI workflow to provide:
- Real-time performance tracking
- Historical comparison
- Identification of regression
- Data-driven optimization

## Future Enhancements

Potential improvements:
- Real-time dashboard updates
- Slack/email notifications for target breaches
- Predictive analytics for performance trends
- Integration with other monitoring tools
- Custom metric definitions

## Support

For issues or questions:
- Check existing metrics in `~/.coda/metrics/`
- Review GitHub Actions logs
- Ensure all dependencies are installed
- Verify API access permissions