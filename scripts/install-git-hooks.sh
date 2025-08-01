#!/bin/bash
#
# Install Git hooks for Coda development
#
# This script installs pre-commit hooks that run code quality checks
# before allowing commits.
#

set -e

# Get the repository root
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SCRIPTS_DIR="$REPO_ROOT/scripts"

echo "🔧 Installing Git hooks for Coda..."

# Ensure we're in a Git repository
if [[ ! -d "$REPO_ROOT/.git" ]]; then
    echo "❌ Error: Not in a Git repository"
    exit 1
fi

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Install pre-commit hook
echo "📝 Installing pre-commit hook..."
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
#
# Git pre-commit hook for Coda
# Runs code quality checks before allowing commits
#
# This hook runs:
# - Code formatting (black, ruff --fix)
# - Linting (ruff check)
# - Fast smoke tests
#
# To bypass this hook temporarily, use: git commit --no-verify
#

set -e  # Exit on any error

echo "🔍 Running pre-commit checks..."
echo

# Change to repository root to ensure make commands work
cd "$(git rev-parse --show-toplevel)"

# Check if we're in a Git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a Git repository"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed or not in PATH"
    echo "   Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Check if Makefile exists
if [[ ! -f "Makefile" ]]; then
    echo "❌ Error: Makefile not found in repository root"
    exit 1
fi

# Run the pre-commit checks using the project's Makefile
echo "📝 Formatting code..."
if ! make format; then
    echo "❌ Code formatting failed"
    echo "   Please fix formatting issues and try again"
    exit 1
fi

echo
echo "🔍 Running linters..."
if ! make lint; then
    echo "❌ Linting failed"
    echo "   Please fix linting issues and try again"
    exit 1
fi

echo
echo "🧪 Running fast tests..."
if ! make test-fast; then
    echo "❌ Fast tests failed"
    echo "   Please fix test failures and try again"
    exit 1
fi

echo
echo "✅ All pre-commit checks passed!"
echo "   Ready to commit"
echo

exit 0
EOF

# Make the hook executable
chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Pre-commit hook installed successfully!"
echo
echo "The hook will now run automatically before each commit."
echo "It will:"
echo "  - Format your code automatically"
echo "  - Run linting checks"
echo "  - Run fast smoke tests"
echo
echo "To bypass the hook temporarily: git commit --no-verify"
echo "To test the hook manually: make pre-commit"
echo