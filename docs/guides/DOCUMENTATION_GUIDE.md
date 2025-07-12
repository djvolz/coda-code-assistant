# Coda Documentation Guide

## Overview

Coda maintains two parallel documentation systems to serve different audiences and use cases:

1. **In-Repository Documentation**: README files and inline docs for developers
2. **Wiki Documentation**: Comprehensive user guides and detailed references

## Documentation Types

### 1. In-Repository Documentation

**Location**: Throughout the codebase
**Audience**: Developers working with or extending Coda
**Format**: Markdown files, code comments, docstrings

#### Structure
```
coda/
├── README.md                    # Project overview, quick start
├── base/
│   ├── README.md               # Base layer overview
│   ├── config/
│   │   └── README.md          # Config module specifics
│   ├── theme/
│   │   └── README.md          # Theme module specifics
│   └── ...
├── services/
│   └── README.md               # Service layer overview
├── apps/
│   └── README.md               # Apps layer overview
└── docs/
    ├── api/                    # API reference docs
    ├── examples/               # Example applications
    └── architecture/           # Architecture documentation
```

#### Guidelines for In-Repo Docs
- Keep it concise and developer-focused
- Include quick start examples
- Link to wiki for detailed information
- Focus on "how to use" not "how it works"
- Update alongside code changes

### 2. Wiki Documentation

**Location**: `docs/wiki-staging/`
**Audience**: End users, administrators, contributors
**Format**: Comprehensive markdown documents

#### Wiki Staging Process
1. Write verbose documentation in `docs/wiki-staging/`
2. Include all details, examples, edge cases
3. Wiki writer process will:
   - Extract and format content
   - Create navigation structure
   - Maintain cross-references
   - Publish to actual wiki

#### Guidelines for Wiki Docs
- Be comprehensive and verbose
- Include background and context
- Provide multiple examples
- Cover edge cases and troubleshooting
- Include diagrams and visuals
- Don't worry about length - wiki writer will edit

## Documentation Workflow

### When Adding a New Feature

1. **Code Documentation**
   ```python
   def new_feature(param: str) -> dict:
       """Brief description of what this does.
       
       Args:
           param: What this parameter does
           
       Returns:
           What this returns
           
       Example:
           >>> new_feature("test")
           {"result": "success"}
       """
   ```

2. **Module README**
   ```markdown
   ## New Feature
   
   Brief description and quick example.
   
   ```python
   from coda.module import new_feature
   result = new_feature("test")
   ```
   
   For detailed documentation, see the [wiki](wiki-link).
   ```

3. **Wiki Staging**
   ```markdown
   # New Feature Comprehensive Guide
   
   ## Overview
   Detailed explanation of the feature, its purpose, and use cases.
   
   ## Background
   Why this feature was added, what problems it solves.
   
   ## Installation
   Step-by-step installation if needed.
   
   ## Configuration
   All configuration options with examples.
   
   ## Usage Examples
   ### Basic Usage
   [Simple example with explanation]
   
   ### Advanced Usage
   [Complex example with detailed walkthrough]
   
   ### Integration Examples
   [How to use with other features]
   
   ## API Reference
   [Complete API documentation]
   
   ## Troubleshooting
   [Common issues and solutions]
   
   ## Performance Considerations
   [Tips for optimal usage]
   
   ## Related Topics
   [Links to related documentation]
   ```

## Documentation Standards

### Markdown Formatting
- Use proper heading hierarchy (# > ## > ###)
- Include code blocks with language hints
- Use tables for structured data
- Add links for cross-references

### Code Examples
- Provide working, tested examples
- Include imports and setup code
- Show expected output
- Handle common errors

### Versioning
- Document version compatibility
- Note breaking changes
- Maintain historical documentation

## Wiki Staging Directory Structure

```
docs/wiki-staging/
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md
│   └── first-steps.md
├── user-guide/
│   ├── configuration.md
│   ├── providers.md
│   ├── themes.md
│   └── sessions.md
├── developer-guide/
│   ├── architecture.md
│   ├── contributing.md
│   ├── api-reference.md
│   └── creating-modules.md
├── tutorials/
│   ├── basic-chatbot.md
│   ├── multi-provider.md
│   └── custom-themes.md
└── reference/
    ├── cli-commands.md
    ├── configuration-options.md
    └── troubleshooting.md
```

## Best Practices

1. **Write Once, Use Twice**: Write detailed docs in wiki staging, extract key points for READMEs
2. **Keep in Sync**: Update both docs when making changes
3. **Link Liberally**: Connect related documentation
4. **Example-Driven**: Show, don't just tell
5. **User Perspective**: Write from the user's point of view
6. **Progressive Disclosure**: Simple first, details later
7. **Searchable**: Use clear headings and keywords

## Documentation Review Process

1. **Self-Review**: Check for completeness and accuracy
2. **Technical Review**: Ensure technical correctness
3. **User Review**: Verify clarity and usability
4. **Wiki Staging**: Full documentation ready
5. **Wiki Publishing**: Edited and published version

Remember: It's better to have verbose documentation that can be edited down than sparse documentation that leaves users confused.