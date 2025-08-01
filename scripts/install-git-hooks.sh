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
# Runs the same quality checks as CI/CD pipeline
#
# This hook runs:
# - Code formatting with ruff format
# - Full linting with ruff check
# - Matches the quality-checks.yml workflow
#
# To bypass this hook temporarily, use: git commit --no-verify
#

set -e  # Exit on any error

echo "🔍 Running pre-commit checks (matching CI/CD quality checks)..."
echo

# Change to repository root to ensure commands work
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

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|pyi)$' || true)

if [ -z "$STAGED_FILES" ]; then
    echo "✅ No Python files to check"
    exit 0
fi

echo "📝 Checking staged Python files..."
echo

# Format code with ruff format (matching CI)
echo "🎨 Formatting code with ruff..."
if ! uv run ruff format $STAGED_FILES; then
    echo "❌ Code formatting failed"
    echo "   Please review and stage the formatting changes"
    exit 1
fi

# Check if formatting changed any files
if ! git diff --quiet $STAGED_FILES; then
    echo "⚠️  Formatting changes were made. Please review and stage them:"
    git diff --name-only $STAGED_FILES
    echo
    echo "Run 'git add -u' to stage the formatting changes"
    exit 1
fi

echo "✅ Code formatting passed"
echo

# Run full linting check (matching CI)
echo "🔍 Running linting checks with ruff..."
if ! uv run ruff check $STAGED_FILES --exclude archive; then
    echo "❌ Linting failed"
    echo "   Please fix the issues above and try again"
    echo "   Tip: Some issues can be auto-fixed with 'uv run ruff check --fix'"
    exit 1
fi

echo "✅ Linting passed"
echo

# Optional: Run black for additional formatting (if you want extra strictness)
echo "🖤 Running black formatter..."
if ! uv run black --check $STAGED_FILES 2>/dev/null; then
    echo "⚠️  Black would make changes. Running black..."
    uv run black $STAGED_FILES
    echo "   Please review and stage the black formatting changes"
    exit 1
fi

echo
echo "✅ All pre-commit checks passed!"
echo "   Code is properly formatted and linted"
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
echo "  - Format code with ruff format"
echo "  - Run full linting checks with ruff check"
echo "  - Run black formatting check"
echo "  - Match the same checks as CI/CD pipeline"
echo
echo "Note: The hook only checks staged Python files for efficiency"
echo
echo "To bypass the hook temporarily: git commit --no-verify"
echo "To run checks manually: uv run ruff check . --exclude archive"
echo