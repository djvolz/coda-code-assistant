# Test Infrastructure Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing the new test infrastructure strategy for the Coda Code Assistant project.

## Quick Start

### For Developers

```bash
# Run tests for your changes
python scripts/select_tests.py --changed-files "$(git diff --name-only HEAD)" --output-format command | bash

# Run fast unit tests
pytest -m "unit and fast" --maxfail=1

# Run tests for specific module
pytest tests/cli/ -m "not slow"

# Run smoke tests before commit
pytest -m smoke --tb=short
```

### For CI/CD

The new CI pipeline automatically:
1. Detects changed files
2. Selects relevant tests
3. Runs tests with fail-fast behavior
4. Provides feedback in <2 minutes for most PRs

## Implementation Phases

### Phase 1: Foundation Setup (Week 1)

#### 1.1 Deploy Test Selection Infrastructure

```bash
# Copy the test selection script
cp docs/plans/scripts/select_tests.py scripts/

# Make it executable
chmod +x scripts/select_tests.py

# Test the script
./scripts/select_tests.py --changed-files "coda/cli/cli.py" --output-format command
```

#### 1.2 Update pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (may require external services)",
    "slow: Tests that take >10s",
    "fast: Tests that take <1s",
    "smoke: Critical path tests that must always pass",
    "cli: CLI interaction tests",
    "web: Web UI tests",
    "providers: Provider-specific tests",
    "agent: Agent functionality tests",
    "session: Session management tests",
    "observability: Observability and monitoring tests",
]

addopts = [
    "--strict-markers",
    "--tb=short",
    "-ra",
]
```

#### 1.3 Add Smoke Tests

Create `tests/test_smoke.py` with critical path tests:

```python
import pytest

@pytest.mark.smoke
@pytest.mark.fast
def test_core_imports():
    """Verify core modules can be imported."""
    import coda
    import coda.cli
    import coda.providers
    import coda.agents
    
@pytest.mark.smoke
@pytest.mark.fast
def test_cli_help():
    """Verify CLI can show help."""
    from coda.cli.main import app
    # Test implementation

@pytest.mark.smoke
def test_mock_provider():
    """Verify mock provider works."""
    from coda.providers import MockProvider
    provider = MockProvider()
    response = provider.chat([{"role": "user", "content": "test"}], "mock-echo")
    assert response.content == "test"
```

### Phase 2: CI Pipeline Migration (Week 2)

#### 2.1 Create New Optimized Workflow

1. Copy `docs/plans/ci-optimized-example.yml` to `.github/workflows/ci-optimized.yml`
2. Test in a feature branch first
3. Monitor execution times and adjust timeouts

#### 2.2 Update Branch Protection Rules

```yaml
# Required status checks:
- ci-optimized / quick-checks
- ci-optimized / unit-tests
- ci-optimized / ci-status
```

#### 2.3 Deprecate Old Workflows

1. Add deprecation notice to old workflows
2. Gradually reduce their triggers
3. Remove after 2 weeks of stable operation

### Phase 3: Performance Optimization (Week 3)

#### 3.1 Enable Parallel Test Execution

```bash
# Install pytest-xdist
uv pip install pytest-xdist

# Update test commands
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 workers
```

#### 3.2 Implement Test Result Caching

```yaml
# In CI workflow
- name: Cache test results
  uses: actions/cache@v3
  with:
    path: .pytest_cache
    key: pytest-${{ runner.os }}-${{ hashFiles('tests/**/*.py') }}
```

#### 3.3 Profile and Optimize Slow Tests

```bash
# Find slow tests
pytest --durations=20

# Add slow marker to tests >10s
@pytest.mark.slow
def test_expensive_operation():
    ...
```

### Phase 4: Monitoring and Refinement (Week 4)

#### 4.1 Set Up Metrics Collection

Create `scripts/collect_ci_metrics.py`:

```python
import json
from datetime import datetime
from pathlib import Path

def collect_workflow_metrics(workflow_run):
    """Extract metrics from GitHub workflow run."""
    return {
        "date": datetime.now().isoformat(),
        "workflow": workflow_run["name"],
        "duration": workflow_run["duration_seconds"],
        "status": workflow_run["conclusion"],
        "tests_run": workflow_run["tests_run"],
        "tests_failed": workflow_run["tests_failed"],
    }
```

#### 4.2 Create Dashboard

Use GitHub Actions metrics or create simple dashboard:

```markdown
## CI Performance Dashboard

| Date | PR Validation | Full Suite | Tests Run | Success Rate |
|------|--------------|------------|-----------|--------------|
| Today | 1m 45s | 7m 30s | 245 | 98% |
| Yesterday | 2m 10s | 8m 15s | 243 | 97% |
| Last Week | 2m 30s | 9m 00s | 240 | 95% |
```

## Best Practices

### Writing Tests

1. **Use appropriate markers**
   ```python
   @pytest.mark.unit
   @pytest.mark.fast
   def test_quick_function():
       pass
   
   @pytest.mark.integration
   @pytest.mark.slow
   def test_external_service():
       pass
   ```

2. **Keep tests focused**
   - One test per behavior
   - Clear test names
   - Minimal setup/teardown

3. **Use MockProvider for AI tests**
   ```python
   from coda.providers import MockProvider
   
   def test_ai_behavior():
       provider = MockProvider()
       # Test without external dependencies
   ```

### CI/CD Guidelines

1. **Always fail fast**
   - Use `--maxfail=1` for quick feedback
   - Set reasonable timeouts
   - Cancel outdated runs

2. **Run relevant tests only**
   - Trust the test selector
   - Add smoke tests for critical paths
   - Use markers effectively

3. **Monitor and iterate**
   - Track test execution times
   - Identify flaky tests
   - Continuously optimize

## Troubleshooting

### Common Issues

**Issue**: Test selector not finding tests
```bash
# Debug with verbose output
python scripts/select_tests.py --changed-files "file.py" --output-format json

# Check mapping file exists
ls docs/plans/module-test-mapping.json
```

**Issue**: Tests timing out in CI
```yaml
# Increase timeout for specific jobs
timeout-minutes: 15  # Instead of default 10
```

**Issue**: Flaky tests failing randomly
```python
# Mark flaky tests for investigation
@pytest.mark.flaky(reruns=3)
def test_unreliable():
    pass
```

## Migration Checklist

- [ ] Test selection script deployed
- [ ] pytest configuration updated
- [ ] Smoke tests created
- [ ] Module-test mapping verified
- [ ] New CI workflow tested
- [ ] Branch protection updated
- [ ] Old workflows deprecated
- [ ] Team trained on new process
- [ ] Metrics collection enabled
- [ ] Documentation updated

## Success Metrics

Track these metrics weekly:

1. **Average PR validation time**: Target <2 minutes
2. **CI compute minutes**: Target 60% reduction
3. **Test flakiness**: Target <1%
4. **Developer satisfaction**: Survey monthly

## Next Steps

1. Start with Phase 1 immediately
2. Run new and old CI in parallel for 1 week
3. Gather feedback from team
4. Iterate based on metrics
5. Complete all phases within 4 weeks

## Support

- Questions: Create issue with `test-infrastructure` label
- Problems: Check troubleshooting guide first
- Improvements: Submit PR with proposed changes