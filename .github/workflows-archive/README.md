# Archived GitHub Workflows

This directory contains archived GitHub Actions workflows from before the modular refactoring.

## Why These Were Archived

After the major refactoring that reorganized the codebase into a 3-layer architecture (base/services/apps), many of the old workflows became outdated with incorrect paths and assumptions about the code structure.

## Archived Workflows

### Test Workflows
- **test-agents.yml** - Tests for agents/tools (moved to services layer)
- **test-observability.yml** - Tests for observability (moved to base layer)
- **test-web-ui.yml** - Tests for web UI (moved to apps layer)
- **test-oci-genai.yml** - OCI GenAI specific tests
- **test-with-ollama.yml** - Ollama integration tests
- **test.yml** (old version) - Main test workflow with outdated paths

### Issues with Old Workflows
1. **Incorrect Paths**: Referenced old paths like `coda/agents/`, `coda/web/`, etc.
2. **Wrong Coverage Paths**: Coverage tracking used old module paths
3. **Complex Dependencies**: Overly complex test matrices and dependencies
4. **Redundant Tests**: Multiple workflows testing the same functionality

## Current Workflow Strategy

The new simplified workflow structure:
1. **test.yml** - Main test workflow that runs all tests
2. **test-base-modules.yml** - Tests base module independence
3. **test-service-modules.yml** - Tests service layer integration
4. **test-fast.yml** - Quick tests for PRs
5. **test-selector.yml** - Specific UI selector tests
6. **docker-build.yml** - Docker image building
7. **release.yml** - Automated releases

## Restoration

If you need to restore any of these workflows:
1. Copy the workflow file back to `.github/workflows/`
2. Update all paths to match the new structure:
   - `coda/agents/` → `coda/services/agents/`
   - `coda/tools/` → `coda/services/tools/`
   - `coda/web/` → `coda/apps/web/`
   - `coda/cli/` → `coda/apps/cli/`
   - `coda/observability/` → `coda/base/observability/`
3. Update coverage paths to match
4. Test the workflow thoroughly

## Archive Date
July 12, 2025 - Post modular refactoring