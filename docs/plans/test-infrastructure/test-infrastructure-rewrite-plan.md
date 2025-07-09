# Test Infrastructure Rewrite Plan

## Executive Summary

This document outlines a comprehensive plan to rewrite and optimize our test infrastructure for the Coda Code Assistant project. The goal is to create a more maintainable, efficient, and targeted testing strategy that reduces CI compute costs while maintaining high code quality.

## Current State Analysis

### CI/CD Pipeline Overview

We currently have multiple CI workflows:

1. **ci-main.yml** - Main CI pipeline with staged execution
   - Stage 1: Quick checks (lint, imports)
   - Stage 2: Fast unit tests (no external deps)
   - Stage 3: Parallel specialized tests (agents, web UI)
   - Stage 4: Integration tests (conditional)
   - Stage 5: Docker build (main branch only)

2. **test.yml** - Legacy comprehensive test suite
   - Runs all tests sequentially
   - Includes lint, unit, integration, and web UI tests
   - Matrix testing for Python 3.11, 3.12, 3.13

3. **test-fast.yml** - Quick unit tests with mock providers

4. Specialized workflows:
   - test-agents.yml
   - test-observability.yml
   - test-oci-genai.yml
   - test-web-ui.yml
   - test-with-ollama.yml

### Test Directory Structure

```
tests/
├── agents/          # Agent and tool integration tests
├── cli/             # CLI interaction and command tests
├── embeddings/      # Embedding provider tests
├── functional/      # End-to-end workflow tests
├── integration/     # Cross-module integration tests
├── intelligence/    # Code intelligence and analysis tests
├── llm/             # LLM provider tests
├── providers/       # Provider-specific tests
├── session/         # Session management tests
├── tools/           # Tool execution tests
├── unit/            # Pure unit tests
├── vector_stores/   # Vector storage tests
└── web/             # Web UI tests
    ├── functional/
    ├── integration/
    ├── manual/
    └── unit/
```

### Identified Issues

1. **Test Duplication**: Multiple workflows test the same functionality
2. **Inefficient Execution**: All tests run regardless of changed code
3. **Slow Feedback**: Full test suite takes too long
4. **Resource Waste**: No fail-fast behavior in some workflows
5. **Poor Organization**: Tests not clearly mapped to modules
6. **Missing Coverage**: Some modules lack comprehensive tests

## Module-to-Test Mapping

### Phase 1: Initial Mapping

| Module | Test Coverage | Test Files |
|--------|--------------|------------|
| **coda/__version__.py** | ✅ Full | tests/test_version.py |
| **coda/agents/** | ✅ Good | tests/agents/*, tests/test_agent.py |
| **coda/chunking.py** | ✅ Full | tests/test_chunking.py |
| **coda/cli/** | ✅ Good | tests/cli/* |
| **coda/configuration.py** | ✅ Full | tests/unit/test_configuration.py |
| **coda/embeddings/** | ✅ Good | tests/embeddings/* |
| **coda/intelligence/** | ✅ Good | tests/intelligence/* |
| **coda/observability/** | ✅ Good | tests/unit/observability/*, tests/integration/observability/* |
| **coda/providers/** | ✅ Good | tests/providers/*, tests/unit/test_providers.py |
| **coda/semantic_search.py** | ✅ Full | tests/test_semantic_search.py |
| **coda/session/** | ✅ Good | tests/session/*, tests/unit/test_session_*.py |
| **coda/themes.py** | ✅ Full | tests/test_theme_colors.py |
| **coda/tools/** | ✅ Good | tests/tools/*, tests/test_tools.py |
| **coda/vector_stores/** | ✅ Full | tests/vector_stores/* |
| **coda/web/** | ✅ Good | tests/web/* |

### Test Categories by Execution Time

1. **Fast Tests** (<1s per test)
   - Unit tests with mocked dependencies
   - Configuration tests
   - Theme tests
   - Version tests

2. **Medium Tests** (1-10s per test)
   - CLI interaction tests
   - Mock provider tests
   - Session tests with in-memory DB

3. **Slow Tests** (>10s per test)
   - Integration tests with real providers
   - Web UI browser tests
   - Observability full-stack tests

## Phased Implementation Plan

### Phase 1: Test Organization and Mapping (Week 1)

**Objective**: Create clear module-to-test mapping and reorganize test structure

**Tasks**:
1. Create detailed mapping document
2. Identify and remove duplicate tests
3. Establish clear test naming conventions
4. Add test markers for categorization

**Deliverables**:
- `docs/plans/module-test-mapping.json`
- Updated pytest markers
- Test reorganization PR

### Phase 2: CI Pipeline Optimization (Week 2)

**Objective**: Implement smart test selection based on changed files

**Tasks**:
1. Create change detection script
2. Implement test selector logic
3. Update CI workflows to use selective testing
4. Add fail-fast behavior to all workflows

**Deliverables**:
- `scripts/detect-changes.py`
- `scripts/select-tests.py`
- Updated CI workflows

### Phase 3: Test Performance Optimization (Week 3)

**Objective**: Reduce test execution time

**Tasks**:
1. Profile slow tests
2. Parallelize test execution
3. Optimize fixture usage
4. Implement test result caching

**Deliverables**:
- Performance report
- Optimized test fixtures
- Parallel test execution config

### Phase 4: Coverage Gap Analysis (Week 4)

**Objective**: Identify and fill testing gaps

**Tasks**:
1. Generate coverage reports per module
2. Identify untested code paths
3. Write missing tests
4. Establish coverage thresholds

**Deliverables**:
- Coverage gap report
- New tests for uncovered code
- Coverage configuration

## CI/CD Strategy

### Fail-Fast Implementation

```yaml
# All test jobs should include:
strategy:
  fail-fast: true
  matrix:
    python-version: ["3.11", "3.12", "3.13"]

# Add early exit on first failure:
pytest --maxfail=1
```

### Selective Test Execution

```python
# scripts/select-tests.py
def get_affected_tests(changed_files):
    """Map changed files to relevant test files."""
    test_map = load_module_test_mapping()
    affected_tests = set()
    
    for file in changed_files:
        module = extract_module_path(file)
        if module in test_map:
            affected_tests.update(test_map[module])
    
    return affected_tests
```

### Workflow Structure

```yaml
# Optimized workflow structure
jobs:
  detect-changes:
    outputs:
      affected-modules: ${{ steps.detect.outputs.modules }}
      test-selector: ${{ steps.detect.outputs.tests }}
  
  quick-checks:
    needs: detect-changes
    # Always run lint and basic checks
  
  targeted-tests:
    needs: [detect-changes, quick-checks]
    # Run only tests for affected modules
    run: |
      pytest ${{ needs.detect-changes.outputs.test-selector }}
```

## Test Categorization Strategy

### Pytest Markers

```python
# pytest.ini
[pytest]
markers =
    unit: Pure unit tests (no external dependencies)
    integration: Tests requiring external services
    slow: Tests taking >10s
    fast: Tests taking <1s
    web: Web UI specific tests
    cli: CLI interaction tests
    provider: Provider-specific tests
    smoke: Critical path tests
```

### Test Selection Examples

```bash
# Run only fast unit tests
pytest -m "unit and fast"

# Run tests for specific module
pytest tests/agents/ -m "not slow"

# Run smoke tests
pytest -m smoke
```

## Performance Metrics

### Current Baseline

- Full test suite: ~15 minutes
- Unit tests only: ~3 minutes
- Integration tests: ~10 minutes
- Web UI tests: ~5 minutes

### Target Metrics

- PR validation (changed code only): <2 minutes
- Full unit test suite: <1 minute
- Critical path tests: <30 seconds
- Full test suite: <10 minutes

## Implementation Timeline

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Test Organization | Module mapping, test cleanup |
| 2 | CI Optimization | Selective testing, fail-fast |
| 3 | Performance | Parallel execution, caching |
| 4 | Coverage | Gap analysis, new tests |
| 5 | Documentation | Updated test guide |
| 6 | Monitoring | Test metrics dashboard |

## Success Criteria

1. **Efficiency**: 50% reduction in average CI runtime
2. **Reliability**: Zero flaky tests
3. **Coverage**: >90% code coverage maintained
4. **Speed**: <2 minute feedback for PRs
5. **Cost**: 60% reduction in CI compute costs

## Next Steps

1. Review and approve this plan
2. Create detailed module-test mapping JSON
3. Begin Phase 1 implementation
4. Set up monitoring for baseline metrics

## Appendix: Module Test Mapping Template

```json
{
  "coda/agents/agent.py": {
    "unit_tests": ["tests/unit/test_agent.py"],
    "integration_tests": ["tests/integration/test_agent_models_integration.py"],
    "markers": ["agent", "core"],
    "dependencies": ["coda/providers/", "coda/tools/"]
  }
}
```