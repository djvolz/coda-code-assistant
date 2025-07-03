#!/bin/bash
# Test runner script for OCI GenAI provider tests

set -e

echo "🧪 Running OCI GenAI Provider Tests"
echo "=================================="

# Default to running only unit and mocked tests
RUN_INTEGRATION=${RUN_INTEGRATION:-false}
RUN_FUNCTIONAL=${RUN_FUNCTIONAL:-false}

# Install dev dependencies if needed
echo "📦 Installing dependencies..."
uv sync --dev

echo ""
echo "🔍 Running unit tests..."
uv run pytest tests/unit/test_oci_genai_provider.py -v

echo ""
echo "🔍 Running mocked tests (CI/CD safe)..."
uv run pytest tests/test_oci_genai_mocked.py -v

if [ "$RUN_INTEGRATION" = "true" ]; then
    echo ""
    echo "🔍 Running integration tests..."
    echo "⚠️  Note: Integration tests require OCI credentials"
    uv run pytest tests/integration/test_oci_genai_integration.py --run-integration -v
else
    echo ""
    echo "ℹ️  Skipping integration tests (set RUN_INTEGRATION=true to run)"
fi

if [ "$RUN_FUNCTIONAL" = "true" ]; then
    echo ""
    echo "🔍 Running functional tests..."
    echo "⚠️  Note: Functional tests require OCI credentials and expect"
    uv run pytest tests/functional/test_oci_genai_functional.py --run-functional -v
else
    echo ""
    echo "ℹ️  Skipping functional tests (set RUN_FUNCTIONAL=true to run)"
fi

echo ""
echo "📊 Test Summary"
echo "=============="

# Run all tests with summary
if [ "$RUN_INTEGRATION" = "true" ] && [ "$RUN_FUNCTIONAL" = "true" ]; then
    uv run pytest tests/ -v --tb=short --run-integration --run-functional
else
    uv run pytest tests/unit/ tests/test_oci_genai_mocked.py -v --tb=short
fi

echo ""
echo "✅ Test run complete!"