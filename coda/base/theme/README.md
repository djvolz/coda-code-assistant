# Theme Module

The Theme module provides terminal UI formatting, syntax highlighting, and visual components for beautiful command-line interfaces.

## Features

- 🎨 **Multiple Themes**: Monokai, Dracula, GitHub, Solarized, Nord, and more
- 🖥️ **Rich Terminal UI**: Tables, panels, progress bars, spinners
- 🌈 **Syntax Highlighting**: Code highlighting for 50+ languages
- 📝 **Markdown Rendering**: Format markdown in the terminal
- ♿ **Accessibility**: High contrast and screen reader modes

## Quick Start

```python
from coda.base.theme import ThemeManager

# Initialize with a theme
theme = ThemeManager({"theme": {"name": "monokai"}})

# Display formatted messages
theme.print_success("✓ Operation completed!")
theme.print_error("✗ An error occurred")
theme.print_warning("⚠ This is a warning")
theme.print_info("ℹ Loading...")

# Syntax highlighting
code = '''def hello():
    print("Hello, World!")'''
theme.print_code(code, language="python")

# Interactive components
name = theme.prompt("Enter your name")
if theme.confirm("Continue?"):
    theme.print_success("Let's go!")
```

## Display Components

### Status Messages

```python
theme.print_success("✓ Tests passed")
theme.print_error("✗ Build failed")
theme.print_warning("⚠ Deprecated function")
theme.print_info("ℹ Processing...")
```

### Code Display

```python
# Syntax highlighting
theme.print_code("""
class Example:
    def __init__(self):
        self.value = 42
""", language="python")

# Markdown rendering
theme.print_markdown("""
# Header
- Item 1
- Item 2

**Bold** and *italic* text
""")
```

### Interactive Elements

```python
# Text prompt
name = theme.prompt("Name", default="Anonymous")

# Confirmation
if theme.confirm("Delete file?", default=False):
    delete_file()

# Selection menu
choice = theme.select(
    "Choose provider",
    ["OpenAI", "Anthropic", "Ollama"]
)

# Progress indicators
with theme.progress("Downloading..."):
    download_large_file()

# Spinner animation
with theme.spinner("Processing..."):
    process_data()
```

### Tables and Layout

```python
# Formatted table
theme.print_table(
    headers=["File", "Size", "Modified"],
    rows=[
        ["app.py", "2.5 KB", "2024-01-15"],
        ["config.toml", "512 B", "2024-01-14"]
    ]
)

# Bordered panel
theme.print_panel(
    "Important information goes here",
    title="Notice"
)

# Horizontal rule
theme.print_rule("Section Break")
```

## Built-in Themes

- **monokai** - Classic dark theme (default)
- **github** - GitHub-inspired light theme
- **dracula** - Popular dark theme
- **solarized** - Solarized color scheme
- **nord** - Nordic-inspired theme
- **minimal** - Minimal colors for accessibility

## Custom Themes

```python
custom_theme = {
    "name": "custom",
    "colors": {
        "primary": "#007ACC",
        "success": "#4CAF50",
        "error": "#F44336",
        "warning": "#FF9800",
        "info": "#2196F3",
        "text": "#FFFFFF",
        "background": "#1E1E1E"
    },
    "syntax": {
        "keyword": "#569CD6",
        "string": "#CE9178",
        "comment": "#6A9955",
        "function": "#DCDCAA"
    }
}

theme = ThemeManager({"theme": custom_theme})
```

## Configuration

```toml
[theme]
# Theme name or custom theme
name = "monokai"

# Enable/disable colors
use_colors = true

# Enable/disable Unicode symbols
use_unicode = true

# Terminal width for text wrapping
terminal_width = 80

# Show timestamps in output
show_timestamps = false

# Animation speed in milliseconds
spinner_speed = 100

# Accessibility options
[theme.accessibility]
high_contrast = false
reduce_motion = false
screen_reader_mode = false
```

## Advanced Usage

### Context Managers

```python
# Timed operations
with theme.timed_operation("Database query"):
    results = db.query("SELECT * FROM users")
    # Automatically shows duration

# Grouped output
with theme.group("Configuration"):
    theme.print_info("Loading config...")
    theme.print_success("✓ Config loaded")
```

### Custom Formatting

```python
# Colored text
theme.print_colored("Custom color", color="cyan")

# Styled text
theme.print_styled("Important!", style="bold underline")

# Combined styles
theme.print(
    "Status: [green]Active[/green] | [yellow]Warning: Low memory[/yellow]"
)
```

### Dynamic Themes

```python
# Auto-detect system theme
theme = ThemeManager({
    "theme": {"name": "auto"}
})

# Switch themes at runtime
theme.switch_theme("dracula")
```

## API Documentation

For detailed API documentation, see [Theme API Reference](../../../docs/api/theme.md).

## Examples

- [Themed CLI Example](../../../tests/examples/themed_cli/) - Complete themed application
- [All Theme Features](./example.py) - Comprehensive demonstration
- [Theme Tests](../../../tests/base/theme/) - Test implementations

## Tips

1. Use Unicode symbols sparingly - not all terminals support them
2. Test with `use_colors=false` for compatibility
3. Provide `--no-color` CLI option for users
4. Use semantic methods (`print_error` vs `print_colored`)
5. Consider accessibility - provide high contrast options