# Coda Wiki Staging Documentation

This directory contains documentation **staged** for the project wiki. These documents are drafts and working copies that can be reviewed before being added to the actual wiki module. They provide in-depth information about features, design decisions, and usage guides.

**Note: This is NOT the wiki module itself, but a staging area for documentation that may be added to the wiki.**

## Tree-Sitter Intelligence Feature

### Documentation

1. **[Feature Branch Overview](./feature-branch-readme.md)**
   - Quick start guide for the tree-sitter feature branch
   - Installation and setup instructions
   - Command reference and examples

2. **[Design Document](./tree-sitter-intelligence-design.md)**
   - Architecture overview
   - Implementation details
   - Design decisions and rationale
   - Future enhancements

3. **[Usage Guide](./tree-sitter-intelligence-usage.md)**
   - Comprehensive usage examples
   - Tool descriptions and use cases
   - Tips and best practices
   - Troubleshooting guide

4. **[Examples Showcase](./tree-sitter-examples.md)**
   - Real-world usage examples
   - Common workflows
   - Advanced patterns
   - Tips for effective use

### Quick Links

- **Branch**: `feature/tree-sitter`
- **Main Module**: `coda/intelligence/`
- **Tests**: `tests/intelligence/`
- **Tools**: `coda/tools/intelligence_tools.py` (MCP), `coda/agents/intelligence_tools.py` (Native)

### Key Features

- 🌍 **30+ Language Support**: Python, JavaScript, TypeScript, Java, Kotlin, Go, Rust, and more
- 🔍 **Code Navigation**: Find definitions, analyze structures, track dependencies
- 🛠 **Hybrid Tools**: Native tools for speed, MCP tools for comprehensive analysis
- 📊 **Dependency Graphs**: Visualize code relationships and detect circular dependencies
- 🤖 **AI Integration**: Natural language queries for code understanding

### Example Usage

```bash
# Find a class definition
coda /intel find UserService

# Analyze file structure
coda /intel analyze src/main.py

# Build dependency graph
coda /intel graph src/ --output=deps.json

# In chat
> "What does the UserService class do?"
> "Find all Python functions in this directory"
```

## Contributing to Documentation

When adding new documentation:

1. Place files in this `docs/wiki-staging/` directory
2. Use descriptive filenames with hyphens (e.g., `feature-name-design.md`)
3. Update this README.md with links to new documents
4. Include:
   - Overview/purpose
   - Technical details
   - Usage examples
   - Troubleshooting tips

## Publishing to Wiki

These documents are designed to be copied to the project wiki:

1. Review and update content as needed
2. Copy markdown files to wiki
3. Update internal links to match wiki structure
4. Add navigation and categories as appropriate

---

*Note: This is a staging area for wiki documentation. These documents should be reviewed and refined before being added to the actual wiki module.*