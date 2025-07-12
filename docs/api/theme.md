# Theme Module API Reference

## Overview

The Theme module provides terminal UI formatting, syntax highlighting, and visual components for building beautiful command-line interfaces. It supports multiple color schemes and rich text formatting.

## Installation

The Theme module is part of the base Coda package:

```bash
pip install coda-assistant
```

## Quick Start

```python
from coda.base.theme import ThemeManager

# Create theme manager
theme = ThemeManager({"theme": {"name": "monokai"}})

# Display formatted text
theme.print_success("Operation completed!")
theme.print_error("An error occurred")
theme.print_warning("This is a warning")

# Syntax highlighting
code = '''def hello():
    print("Hello, world!")'''
theme.print_code(code, language="python")

# Progress indicators
with theme.progress("Processing..."):
    # Long running operation
    time.sleep(2)
```

## API Reference

### ThemeManager Class

```python
class ThemeManager:
    """Manages terminal theming and formatting."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize theme manager.
        
        Args:
            config: Configuration with theme settings
        """
```

#### Display Methods

##### print_success(message: str) -> None

Display a success message with formatting.

```python
theme.print_success("✓ File saved successfully")
```

##### print_error(message: str) -> None

Display an error message with formatting.

```python
theme.print_error("✗ Failed to connect to server")
```

##### print_warning(message: str) -> None

Display a warning message with formatting.

```python
theme.print_warning("⚠ API rate limit approaching")
```

##### print_info(message: str) -> None

Display an informational message.

```python
theme.print_info("ℹ Loading configuration...")
```

##### print_code(code: str, language: str = "python") -> None

Display syntax-highlighted code.

```python
theme.print_code("""
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""", language="python")
```

##### print_markdown(text: str) -> None

Render markdown-formatted text.

```python
theme.print_markdown("""
# Header
- Item 1
- Item 2

**Bold text** and *italic text*
""")
```

#### Interactive Components

##### prompt(message: str, default: str | None = None) -> str

Display an interactive prompt.

```python
name = theme.prompt("Enter your name", default="Anonymous")
```

##### confirm(message: str, default: bool = False) -> bool

Display a yes/no confirmation.

```python
if theme.confirm("Do you want to continue?", default=True):
    process_data()
```

##### select(message: str, options: list[str]) -> str

Display a selection menu.

```python
choice = theme.select(
    "Choose a provider",
    ["openai", "anthropic", "ollama"]
)
```

##### progress(message: str) -> ProgressContext

Display a progress indicator.

```python
with theme.progress("Downloading..."):
    download_file()
```

##### spinner(message: str) -> SpinnerContext

Display a spinner animation.

```python
with theme.spinner("Processing..."):
    process_data()
```

#### Table and Layout

##### print_table(headers: list[str], rows: list[list[str]]) -> None

Display a formatted table.

```python
theme.print_table(
    headers=["Name", "Size", "Modified"],
    rows=[
        ["file1.py", "1.2 KB", "2024-01-15"],
        ["file2.py", "3.4 KB", "2024-01-16"],
    ]
)
```

##### print_panel(content: str, title: str | None = None) -> None

Display content in a bordered panel.

```python
theme.print_panel(
    "This is important information",
    title="Notice"
)
```

##### print_rule(title: str | None = None) -> None

Display a horizontal rule.

```python
theme.print_rule("Section Break")
```

### Theme Configuration

#### Built-in Themes

- `monokai` - Classic dark theme
- `github` - GitHub-inspired light theme
- `dracula` - Popular dark theme
- `solarized` - Solarized color scheme
- `nord` - Nordic-inspired theme
- `minimal` - Minimal colors for accessibility

#### Custom Themes

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

## Examples

### Basic Formatting

```python
from coda.base.theme import ThemeManager

theme = ThemeManager()

# Status messages
theme.print_success("✓ Tests passed")
theme.print_error("✗ Build failed")
theme.print_warning("⚠ Deprecated function used")
theme.print_info("ℹ Version 2.0.0")

# Formatted output
theme.print_markdown("# Results\n\n**Total**: 42")
theme.print_rule("Summary")
```

### Interactive CLI

```python
def interactive_setup(theme: ThemeManager):
    """Interactive configuration setup."""
    
    theme.print_panel(
        "Welcome to Coda Setup",
        title="Setup Wizard"
    )
    
    # Get user inputs
    name = theme.prompt("Project name")
    
    providers = ["OpenAI", "Anthropic", "Ollama", "None"]
    provider = theme.select("Choose AI provider", providers)
    
    if provider != "None":
        api_key = theme.prompt(f"Enter {provider} API key", default="")
    
    if theme.confirm("Save configuration?", default=True):
        save_config(name, provider, api_key)
        theme.print_success("Configuration saved!")
```

### Progress Indicators

```python
import time

def process_files(theme: ThemeManager, files: list[str]):
    """Process files with progress indication."""
    
    # Overall progress
    with theme.progress(f"Processing {len(files)} files..."):
        for i, file in enumerate(files):
            # Individual file progress
            with theme.spinner(f"Processing {file}"):
                # Simulate work
                time.sleep(0.5)
            
            # Update status
            theme.print_success(f"✓ {file} processed")
    
    theme.print_info(f"Completed {len(files)} files")
```

### Code Display with Context

```python
def show_error_context(theme: ThemeManager, file: str, line: int, error: str):
    """Display error with code context."""
    
    theme.print_error(f"Error in {file}:{line}")
    theme.print_error(error)
    
    # Show code context
    with open(file) as f:
        lines = f.readlines()
    
    # Show 3 lines before and after
    start = max(0, line - 4)
    end = min(len(lines), line + 3)
    
    code_block = ""
    for i in range(start, end):
        prefix = ">>> " if i == line - 1 else "    "
        code_block += f"{prefix}{i+1}: {lines[i]}"
    
    theme.print_code(code_block, language="python")
```

### Custom Components

```python
class ChatDisplay:
    """Custom chat display using theme."""
    
    def __init__(self, theme: ThemeManager):
        self.theme = theme
    
    def show_message(self, role: str, content: str):
        """Display a chat message."""
        colors = {
            "user": "info",
            "assistant": "primary",
            "system": "warning"
        }
        
        # Role header
        self.theme.print_colored(
            f"[{role.upper()}]",
            color=colors.get(role, "text")
        )
        
        # Message content
        if "```" in content:
            # Extract and highlight code blocks
            self._render_with_code(content)
        else:
            self.theme.print_text(content)
        
        # Separator
        self.theme.print_rule()
```

## Advanced Usage

### Theme Context Manager

```python
class ThemedOperation:
    """Context manager for themed operations."""
    
    def __init__(self, theme: ThemeManager, title: str):
        self.theme = theme
        self.title = title
        self.start_time = None
    
    def __enter__(self):
        self.theme.print_rule(self.title)
        self.theme.print_info(f"Starting: {self.title}")
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        
        if exc_type is None:
            self.theme.print_success(
                f"✓ {self.title} completed in {elapsed:.2f}s"
            )
        else:
            self.theme.print_error(
                f"✗ {self.title} failed: {exc_val}"
            )
        
        self.theme.print_rule()

# Usage
with ThemedOperation(theme, "Database Migration"):
    migrate_database()
```

### Dynamic Theme Switching

```python
class DynamicTheme:
    """Support runtime theme switching."""
    
    def __init__(self):
        self.themes = {
            "light": ThemeManager({"theme": {"name": "github"}}),
            "dark": ThemeManager({"theme": {"name": "monokai"}}),
            "auto": self._auto_theme()
        }
        self.current = "auto"
    
    def _auto_theme(self) -> ThemeManager:
        """Detect system theme preference."""
        # Implementation depends on platform
        import subprocess
        try:
            # macOS example
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True
            )
            is_dark = result.returncode == 0
            return self.themes["dark" if is_dark else "light"]
        except:
            return self.themes["dark"]
    
    def switch(self, theme_name: str):
        """Switch active theme."""
        if theme_name in self.themes:
            self.current = theme_name
```

### Composable Formatting

```python
from functools import wraps

def with_timing(theme: ThemeManager):
    """Decorator to add timing to functions."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            theme.print_info(f"Starting {func.__name__}...")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                theme.print_success(
                    f"✓ {func.__name__} completed in {elapsed:.2f}s"
                )
                return result
            except Exception as e:
                theme.print_error(f"✗ {func.__name__} failed: {e}")
                raise
        
        return wrapper
    return decorator

# Usage
@with_timing(theme)
def process_data(data):
    # Processing logic
    return processed_data
```

## Styling Reference

### Color Names

Standard colors available in all themes:
- `primary` - Main theme color
- `success` - Success/positive actions
- `error` - Errors/failures  
- `warning` - Warnings/caution
- `info` - Informational messages
- `text` - Default text
- `muted` - De-emphasized text

### Text Styles

```python
# Bold
theme.print_text("**Bold text**", style="bold")

# Italic
theme.print_text("*Italic text*", style="italic")

# Underline
theme.print_text("Underlined", style="underline")

# Combined
theme.print_text("Important!", style="bold,underline")
```

### Unicode Support

```python
# Emoji and symbols
theme.print_success("✅ Complete")
theme.print_error("❌ Failed")
theme.print_warning("⚠️  Warning")
theme.print_info("📝 Note")

# Box drawing
theme.print_text("┌─────────┐")
theme.print_text("│ Content │")
theme.print_text("└─────────┘")
```

## Configuration

```toml
[theme]
# Theme name or "auto" for system detection
name = "monokai"

# Enable/disable colors
use_colors = true

# Enable/disable Unicode symbols
use_unicode = true

# Width for wrapped text
terminal_width = 80

# Syntax highlighting style
syntax_style = "monokai"

# Show timestamps in logs
show_timestamps = false

# Animation speed (ms)
spinner_speed = 100
```

## Accessibility

The theme module supports accessibility features:

```python
# High contrast mode
theme = ThemeManager({
    "theme": {
        "name": "high-contrast",
        "accessibility": {
            "high_contrast": true,
            "reduce_motion": true,
            "screen_reader_mode": true
        }
    }
})

# Minimal formatting for screen readers
if theme.is_accessible():
    theme.print_text("Error: File not found")
else:
    theme.print_error("❌ File not found")
```

## See Also

- [Integration Guide](../integration-guide.md) - Using themes in applications
- [Example: Themed CLI](../../tests/examples/themed_cli/) - Complete themed application
- [Terminal Colors](../reference/terminal-colors.md) - Color reference guide
- [Rich Documentation](https://rich.readthedocs.io/) - Underlying rich library