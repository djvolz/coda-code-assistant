# Release Process

## Overview

Coda uses an automated release process based on conventional commits. Releases are triggered automatically when specific types of commits are merged to the main branch.

## Versioning

Coda uses date-based versioning in the format: `year.month.day.HHMM`
- Example: `2025.1.3.1430` for January 3, 2025 at 14:30 UTC
- Versions are automatically updated during the release process
- No manual version bumping is required

## Automated Release Triggers

Releases are automatically created when commits with the following prefixes are merged to main:

- `feat:` or `feature:` - New features (triggers release)
- `fix:` or `bugfix:` - Bug fixes (triggers release)
- `perf:` - Performance improvements (triggers release)
- `refactor:` - Code refactoring (triggers release)

Commits that do NOT trigger releases:
- `docs:` - Documentation changes
- `style:` - Code style changes
- `test:` - Test additions or changes
- `chore:` - Build process or auxiliary tool changes

## Commit Message Format

Follow the Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Examples

```bash
# Feature
feat(cli): add support for multiple providers

# Bug fix
fix(oci): handle streaming timeout errors

# Breaking change
feat(api)!: redesign provider interface

BREAKING CHANGE: The provider interface has been completely redesigned.
Old providers will need to be updated to the new interface.

# With GitHub issue reference
fix(cli): correct version display format

Fixes #123
```

## Release Workflow

1. **Automatic Trigger**: When commits are pushed to main, the release workflow checks for releasable commits
2. **Version Update**: The version is automatically updated to the current timestamp
3. **Tests Run**: ALL tests (unit and integration) are executed to ensure quality
4. **Build**: The package is built using `uv build`
5. **Changelog Generation**: A changelog is automatically generated from commit messages
6. **GitHub Release**: A new release is created with the changelog and built artifacts
7. **PyPI Upload**: If configured, the package is uploaded to PyPI

## Manual Release

To force a release without conventional commits:

1. Go to Actions → Release workflow
2. Click "Run workflow"
3. Check "Force a release even without conventional commits"
4. Click "Run workflow"

## Skipping Releases

To skip the release process for a commit, include `[skip ci]` or `[skip release]` in the commit message:

```bash
git commit -m "chore: update dependencies [skip release]"
```

## Local Version Update

To manually update the version locally:

```bash
make version
```

## Release Checklist

Before major releases:

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG reviewed
- [ ] Breaking changes documented
- [ ] Migration guide provided (if needed)

## Troubleshooting

### Release not triggered
- Check that your commit message follows conventional commits format
- Ensure the commit type is one that triggers releases
- Check GitHub Actions for any workflow errors

### Version not updating
- The version is only updated during the release process
- Local development always shows the last released version
- Use `make version` to update locally if needed

### PyPI upload failing
- Ensure `PYPI_API_TOKEN` is set in repository secrets
- Check that the package name is available on PyPI
- Verify the build artifacts are valid

## Branch Protection Setup

To ensure only quality code gets released, configure branch protection rules for the `main` branch:

1. Go to Settings → Branches in your GitHub repository
2. Add a branch protection rule for `main`
3. Enable these settings:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging**
     - Select: `quality` (from quality-checks.yml)
     - Select any other critical workflows
   - **Require branches to be up to date before merging**
   - **Include administrators** (optional but recommended)

This ensures:
- All code goes through PR review
- Quality checks must pass before merge
- Only tested, validated code reaches main
- Releases only happen with quality-assured code

## Best Practices

1. **Use conventional commits**: This ensures automatic releases work correctly
2. **Write descriptive commit messages**: They become part of the changelog
3. **Group related changes**: Use feature branches to group related commits
4. **Test before merging**: Ensure all tests pass before merging to main
5. **Document breaking changes**: Use the `BREAKING CHANGE:` footer when needed
6. **DO NOT SQUASH COMMITS**: When merging PRs, use "Create a merge commit" to preserve individual commit messages. The release workflow needs to see the conventional commit types (feat:, fix:, etc.) to trigger releases properly