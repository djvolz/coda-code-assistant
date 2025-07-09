# Plan: Fix Failing CI Checks

## Overview
The PR has 5 failing checks that need to be resolved:
1. Quick Checks - uv sync command error
2. Lint - 12 files need formatting with ruff
3. Web UI Unit Tests - 1 failing test
4. All Web UI Tests Passed - Meta check failing due to unit test failure
5. CI Summary - Meta check failing due to Quick Checks failure

## Root Cause Analysis

### 1. Quick Checks Failure
**Error**: `error: a value is required for '--no-extra <NO_EXTRA>' but none was supplied`
- The command `uv sync --no-extra` is incorrect
- Should be `uv sync --no-extras` (plural form)
- Location: `.github/workflows/ci.yml`

### 2. Lint Failures
**12 files need ruff formatting**:
- coda/observability/manager.py
- tests/integration/observability/test_enabled_disabled_states.py
- tests/integration/observability/test_thread_safety.py
- tests/intelligence/test_queries/test_query_validation.py
- tests/providers/test_mock_provider_conversations.py
- tests/providers/test_mock_provider_modes.py
- tests/session/test_end_to_end.py
- tests/session/test_interactive_integration.py
- tests/test_theme_colors.py
- tests/tools/test_intelligence_tools.py
- tests/web/test_functionality.py
- tests/web/test_navigation.py

### 3. Web UI Unit Test Failure
**Failing test**: `test_init_session_state_session_manager_error`
- File: `tests/web/unit/utils/test_state.py:114`
- Error: The test expects "DB error" or "Operation not supported" in the error message
- Actual error: "[Errno 13] Permission denied: '/home/user'"
- The mock is not working as expected; the actual code is trying to create a directory

## Fix Implementation Plan

### Phase 1: Fix Quick Checks (Immediate)
1. Update `.github/workflows/ci.yml` to use correct uv command
2. Search for all occurrences of `--no-extra` and replace with `--no-extras`

### Phase 2: Fix Linting Issues (Immediate)
1. Run `uv run ruff format` locally to auto-fix formatting
2. Review changes to ensure no functional modifications
3. Commit formatted files

### Phase 3: Fix Web UI Test (Requires Analysis)
1. Examine the test to understand the mocking strategy
2. The test is trying to mock SessionManager but the actual initialization is creating directories
3. Need to mock the Path operations or adjust the test expectations
4. Update the test to properly mock the directory creation or handle the permission error

### Phase 4: Verify Fixes
1. Run all tests locally before pushing
2. Ensure CI passes on the PR

## Commands to Execute

```bash
# Fix formatting
uv run ruff format .

# Run tests locally
uv run python -m pytest tests/web/unit/utils/test_state.py -v
make test

# Check CI workflow syntax
gh workflow view "CI Pipeline"
```

## Files to Modify

1. `.github/workflows/ci.yml` - Fix uv sync command
2. All 12 Python files listed above - Apply ruff formatting
3. `tests/web/unit/utils/test_state.py` - Fix the failing test

## Success Criteria
- All CI checks pass
- No functional changes to code (only formatting and test fixes)
- PR can be merged successfully

## Additional Issues Found - Observability Storage

### BatchWriter Test Issues
The BatchWriter tests are incorrectly designed. They expect individual keys to exist after writes, but BatchWriter is designed to:
1. Batch multiple writes together
2. Save them as timestamped batch files (e.g., `metrics_batch_20241209_143023`)
3. NOT save individual keys directly

### Missing Storage Backend Methods
The storage backends are missing methods that tests expect:
1. `clear()` - Clear all stored data
2. `size()` - Get total size of stored data
3. `base_dir` attribute in FileStorageBackend (should be `base_path`)

### Fix Strategy
1. **Implement missing methods** in both FileStorageBackend and MemoryStorageBackend
2. **Fix BatchWriter tests** to check for batch files instead of individual keys
3. **Remove the skip decorator** once tests are fixed
4. **Add proper cleanup** to ensure timer threads don't hang