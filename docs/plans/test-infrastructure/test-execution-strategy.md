# Test Execution Strategy

## Current Testing Pain Points

### 1. Performance Issues
- **Full test suite runtime**: ~15 minutes
- **No intelligent test selection**: All tests run on every change
- **Sequential execution**: Tests run one after another instead of parallel
- **Redundant test runs**: Same tests executed multiple times across workflows

### 2. Resource Waste
- **No fail-fast**: Tests continue running even after failures
- **Excessive matrix testing**: All Python versions tested for every change
- **Docker builds**: Built even when no Docker files changed
- **Integration tests**: Run even for documentation changes

### 3. Maintenance Burden
- **Duplicate workflows**: Multiple CI files with overlapping functionality
- **Unclear test ownership**: Tests not clearly mapped to modules
- **Flaky tests**: Intermittent failures in integration tests
- **Poor error reporting**: Hard to identify which module caused failure

### 4. Developer Experience
- **Slow feedback loop**: Wait 15+ minutes for PR validation
- **Unclear test categorization**: Don't know which tests to run locally
- **Missing test documentation**: No guide on writing new tests
- **Complex CI debugging**: Hard to reproduce CI failures locally

## Optimized CI/CD Strategy

### Test Selection Algorithm

```python
# scripts/select_tests.py
import json
import os
from pathlib import Path
from typing import Set, List

class TestSelector:
    def __init__(self):
        with open('docs/plans/module-test-mapping.json') as f:
            self.mapping = json.load(f)
    
    def get_tests_for_changes(self, changed_files: List[str]) -> Set[str]:
        """Select tests based on changed files."""
        tests = set()
        
        for file in changed_files:
            # Direct module mapping
            if file in self.mapping:
                module_info = self.mapping[file]
                tests.update(module_info['unit_tests'])
                tests.update(module_info['integration_tests'])
            
            # Check dependencies
            for module, info in self.mapping.items():
                for dep in info['dependencies']:
                    if file.startswith(dep):
                        tests.update(info['unit_tests'])
        
        return tests
    
    def get_markers_for_changes(self, changed_files: List[str]) -> Set[str]:
        """Get pytest markers for changed files."""
        markers = set()
        
        for file in changed_files:
            if file in self.mapping:
                markers.update(self.mapping[file]['markers'])
        
        return markers
```

### Fail-Fast Configuration

```yaml
# .github/workflows/ci-optimized.yml
name: Optimized CI Pipeline

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      tests: ${{ steps.select.outputs.tests }}
      markers: ${{ steps.select.outputs.markers }}
      skip-tests: ${{ steps.select.outputs.skip }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Get changed files
        id: changed-files
        uses: tj-actions/changed-files@v40
        
      - name: Select tests
        id: select
        run: |
          python scripts/select_tests.py \
            --changed-files "${{ steps.changed-files.outputs.all_changed_files }}" \
            --output-format github
  
  quick-lint:
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - name: Lint check
        run: |
          uv sync --no-extras
          uv run ruff check . --exit-non-zero-on-fix
          uv run ruff format --check .
  
  targeted-tests:
    needs: [detect-changes, quick-lint]
    if: needs.detect-changes.outputs.skip-tests != 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    strategy:
      fail-fast: true
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      - name: Run targeted tests
        run: |
          uv sync --all-extras
          uv run pytest ${{ needs.detect-changes.outputs.tests }} \
            --maxfail=1 \
            --tb=short \
            -v
```

### Test Categorization

```ini
# pyproject.toml
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

testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Fail fast
addopts = [
    "--strict-markers",
    "--maxfail=1",
    "--tb=short",
    "-ra",
]
```

### Parallel Test Execution

```yaml
# Run tests in parallel groups
parallel-tests:
  strategy:
    fail-fast: true
    matrix:
      group:
        - name: "core"
          pattern: "tests/unit/test_*.py tests/test_*.py"
          markers: "unit and not slow"
        - name: "cli"  
          pattern: "tests/cli/"
          markers: "cli and not integration"
        - name: "providers"
          pattern: "tests/providers/ tests/unit/test_oci*.py"
          markers: "providers"
        - name: "web"
          pattern: "tests/web/unit/"
          markers: "web and unit"
  
  steps:
    - name: Run ${{ matrix.group.name }} tests
      run: |
        uv run pytest ${{ matrix.group.pattern }} \
          -m "${{ matrix.group.markers }}" \
          --maxfail=1 \
          -n auto
```

## Test Execution Tiers

### Tier 1: PR Validation (Target: <2 minutes)
- Lint checks
- Import validation
- Smoke tests
- Unit tests for changed modules only

### Tier 2: Pre-merge (Target: <5 minutes)
- All unit tests
- Integration tests for changed modules
- Critical path tests

### Tier 3: Post-merge (Target: <10 minutes)
- Full test suite
- All integration tests
- Browser tests
- Performance benchmarks

### Tier 4: Nightly (Target: <30 minutes)
- Extended integration tests
- Load tests
- Security scans
- Compatibility matrix (all Python versions)

## Local Development Workflow

### Quick Test Commands

```bash
# Run tests for current changes
make test-changes

# Run fast unit tests
pytest -m "unit and fast" --maxfail=1

# Run tests for specific module
pytest tests/cli/ -m "not slow"

# Run smoke tests before commit
pytest -m smoke --tb=short
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: quick-tests
        name: Quick Tests
        entry: pytest -m "smoke" --maxfail=1 --quiet
        language: system
        pass_filenames: false
        always_run: true
```

## Monitoring and Metrics

### Key Performance Indicators

1. **Average PR validation time**: Target <2 minutes
2. **Test flakiness rate**: Target <1%
3. **CI compute minutes**: Target 60% reduction
4. **Developer wait time**: Target 80% reduction

### Test Performance Tracking

```python
# scripts/track_test_performance.py
import time
import json
from pathlib import Path

class TestPerformanceTracker:
    def __init__(self):
        self.results_file = Path(".test-performance.json")
        self.load_history()
    
    def track_test_run(self, test_name: str, duration: float):
        """Track individual test performance."""
        if test_name not in self.history:
            self.history[test_name] = []
        
        self.history[test_name].append({
            'duration': duration,
            'timestamp': time.time()
        })
        
        # Flag slow tests
        if duration > 10:
            print(f"⚠️ Slow test detected: {test_name} ({duration:.2f}s)")
    
    def get_slow_tests(self, threshold: float = 10.0) -> List[str]:
        """Identify consistently slow tests."""
        slow_tests = []
        
        for test, runs in self.history.items():
            avg_duration = sum(r['duration'] for r in runs) / len(runs)
            if avg_duration > threshold:
                slow_tests.append((test, avg_duration))
        
        return sorted(slow_tests, key=lambda x: x[1], reverse=True)
```

## Implementation Checklist

### Week 1: Foundation
- [ ] Create test selection script
- [ ] Set up module-test mapping
- [ ] Configure pytest markers
- [ ] Update CI workflows with fail-fast

### Week 2: Optimization  
- [ ] Implement parallel test execution
- [ ] Create tiered test strategy
- [ ] Set up change detection
- [ ] Add performance tracking

### Week 3: Integration
- [ ] Migrate existing workflows
- [ ] Update developer documentation
- [ ] Create local test commands
- [ ] Set up monitoring dashboard

### Week 4: Refinement
- [ ] Identify and fix flaky tests
- [ ] Optimize slow tests
- [ ] Create test writing guide
- [ ] Measure performance improvements

## Success Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| PR Validation Time | 15 min | 2 min | 87% |
| Full Test Suite | 15 min | 8 min | 47% |
| CI Compute Minutes | 1000/day | 400/day | 60% |
| Failed PR Rate | 30% | 10% | 67% |
| Developer Satisfaction | 3/10 | 8/10 | 167% |