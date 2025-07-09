# Test Coverage Requirements

## Overview

This document outlines the test coverage requirements and goals for the Coda Code Assistant project. Coverage metrics help ensure code quality and identify areas needing additional testing.

## Coverage Goals

### Overall Project Coverage
- **Current**: 25.82% (as of Phase 4 analysis)
- **Target**: 70% overall coverage
- **Critical Path**: 90%+ for smoke-tested features

### Module-Specific Thresholds

Based on importance and user impact:

#### Critical Modules (80% target)
- `coda/cli/` - User-facing CLI interface
- `coda/providers/` - Core provider functionality
- `coda/agents/` - Agent system core
- `coda/session/` - Session management

#### Important Modules (70% target)
- `coda/tools/` - Tool execution
- `coda/embeddings/` - Embedding functionality
- `coda/configuration/` - Config management

#### Medium Priority (60% target)
- `coda/observability/` - Monitoring features
- `coda/intelligence/` - Code analysis
- `coda/semantic_search/` - Search functionality

#### Lower Priority (50% target)
- `coda/web/` - Web UI (separate E2E testing)
- `coda/vector_stores/` - Vector storage

## Coverage Analysis Tools

### 1. Coverage Generation
```bash
# Run tests with coverage
make test-cov

# Generate detailed reports
pytest --cov=coda --cov-report=html --cov-report=json
```

### 2. Coverage Analysis Script
```bash
# Analyze coverage gaps
uv run python scripts/analyze_coverage.py

# Export detailed gap analysis
uv run python scripts/analyze_coverage.py --export-gaps

# Check against threshold
uv run python scripts/analyze_coverage.py --min-coverage 30
```

### 3. CI Coverage Monitoring
- Automated coverage reports on every PR
- Coverage artifacts uploaded for review
- Coverage trends tracked in GitHub Actions summary

## Priority Testing Areas

Based on current coverage analysis, these modules need immediate attention:

### High Priority (Critical modules with <20% coverage)
1. **coda/cli/interactive_cli.py** (48.6% coverage, 519 statements)
   - Key user interaction points
   - Command processing logic
   - Session management integration

2. **coda/session/commands.py** (10.8% coverage, 397 statements)
   - Session command execution
   - State management
   - Command history

3. **coda/providers/oci_genai.py** (18.4% coverage, 354 statements)
   - OCI provider implementation
   - Model discovery
   - Streaming responses

4. **coda/agents/agent.py** (6.4% coverage, 295 statements)
   - Core agent functionality
   - Tool execution
   - Response processing

5. **coda/cli/interactive.py** (0.0% coverage, 234 statements)
   - Interactive mode features
   - User input handling

## Coverage Enforcement

### Pull Request Requirements
- New features must include tests
- Coverage should not decrease
- Critical path changes require 80%+ coverage

### Exceptions
Coverage requirements may be relaxed for:
- Prototype/experimental features (marked as such)
- Platform-specific code (with appropriate markers)
- Third-party integration code (with mocks)

## Measuring Coverage

### Local Development
```bash
# Quick coverage check
make test-cov

# Detailed HTML report
pytest --cov=coda --cov-report=html
open htmlcov/index.html
```

### CI Pipeline
Coverage is automatically measured in CI with:
- Per-module coverage reports
- Coverage trend analysis
- Automatic PR comments with coverage delta

## Improving Coverage

### Writing Effective Tests
1. **Unit Tests**: Test individual functions/methods in isolation
2. **Integration Tests**: Test component interactions
3. **Edge Cases**: Include error conditions and boundary values
4. **Mock External Dependencies**: Use MockProvider for AI interactions

### Coverage Best Practices
- Focus on critical user paths first
- Write tests alongside new features
- Refactor untestable code for better coverage
- Use parametrized tests for multiple scenarios

## Coverage Exclusions

The following patterns are excluded from coverage:
- `pragma: no cover` - Explicitly excluded code
- Abstract methods and interfaces
- Debug-only code (`if self.debug`)
- Import error handlers
- Platform-specific code branches
- Main execution blocks

See `.coveragerc` for the complete exclusion list.

## Monitoring Progress

### Weekly Goals
- Increase overall coverage by 2-3% per week
- Focus on one critical module at a time
- Review and update priority list based on new features

### Monthly Reviews
- Analyze coverage trends
- Adjust thresholds based on project maturity
- Identify consistently low-coverage areas for refactoring

## Resources

- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)
- [Writing Testable Python Code](https://docs.python-guide.org/writing/tests/)