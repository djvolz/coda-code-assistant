# Base Config Module

A standalone, flexible configuration management module that can be used in any Python project.

> **Note**: This is the low-level configuration module with zero dependencies. If you're building a Coda application, you probably want to use `coda.services.config.AppConfig` instead, which integrates this module with themes and provides application-specific defaults.

## Features

- **Zero Dependencies**: Uses only Python standard library
- **Multiple Sources**: Load from files, environment variables, and defaults
- **Layered Priority**: Configs merge in order: defaults → files → environment → runtime
- **Multiple Formats**: Supports JSON, TOML, YAML, and INI files
- **Type-Safe Access**: Typed getter methods with defaults
- **Nested Keys**: Access nested values with dot notation
- **Copy-Paste Ready**: Can be copied to any project and used immediately

## Installation

### As part of Coda

```python
from coda.config import Config
```

### Standalone Usage

1. Copy the entire `config/` directory to your project
2. Import directly:

```python
from config import Config
```

## Quick Start

### Basic Usage

```python
from coda.config import Config

# Create config with defaults
config = Config(
    app_name="myapp",
    defaults={
        "debug": False,
        "server": {
            "host": "localhost",
            "port": 8080
        }
    }
)

# Access configuration
debug = config.get_bool("debug")
host = config.get_string("server.host")
port = config.get_int("server.port", default=3000)
```

### Loading from File

```python
# Load from specific file
config = Config(
    app_name="myapp",
    config_file="config.json"  # or .toml, .yaml, .ini
)

# Or let it find configs automatically
config = Config(app_name="myapp")
# Looks for:
# - /etc/myapp/config.toml (or .json)
# - ~/.config/myapp/config.toml (or .json)  
# - .myapp/config.toml (or .json)
```

### Environment Variables

```python
# Set environment variables
os.environ["MYAPP_DEBUG"] = "true"
os.environ["MYAPP_SERVER_PORT"] = "9000"

# Config with env prefix
config = Config(
    app_name="myapp",
    env_prefix="MYAPP_"  # Optional, defaults to APP_NAME_
)

# Environment vars override file values
debug = config.get_bool("debug")  # True (from env)
port = config.get_int("server.port")  # 9000 (from env)
```

### Runtime Changes

```python
# Set values at runtime (highest priority)
config.set("server.timeout", 30)
config.set("features.experimental", True)

# Runtime values override everything else
timeout = config.get_int("server.timeout")  # 30
```

## Configuration Priority

Configuration sources are merged in priority order (highest to lowest):

1. **Runtime** - Values set with `config.set()`
2. **Environment** - Environment variables with prefix
3. **Project Config** - `.myapp/config.toml` in current directory
4. **User Config** - `~/.config/myapp/config.toml`
5. **System Config** - `/etc/myapp/config.toml`
6. **Package Defaults** - `default.toml` in the package (if exists)
7. **Constructor Defaults** - Provided in constructor

### Package Default Loading

The ConfigManager automatically looks for `default.toml` in these locations:
- `{app_name}/default.toml` - Package root
- `{app_name}/config/default.toml` - Config subpackage
- `{app_name}/services/config/default.toml` - Services config subpackage

This allows packages to ship with comprehensive default configurations.

## API Reference

### Config Class

```python
Config(
    app_name: str = "app",
    config_file: Optional[str] = None,
    env_prefix: Optional[str] = None,
    defaults: Optional[Dict[str, Any]] = None
)
```

### Getter Methods

- `get(key: str, default: Any = None) -> Any` - Get any value
- `get_bool(key: str, default: bool = False) -> bool` - Get boolean
- `get_int(key: str, default: int = 0) -> int` - Get integer
- `get_float(key: str, default: float = 0.0) -> float` - Get float
- `get_string(key: str, default: str = "") -> str` - Get string
- `get_list(key: str, default: List = None) -> List` - Get list
- `get_dict(key: str, default: Dict = None) -> Dict` - Get dictionary

### Other Methods

- `set(key: str, value: Any) -> None` - Set runtime value
- `to_dict() -> Dict[str, Any]` - Get entire config as dict
- `save(path: Path, format: ConfigFormat) -> None` - Save to file

## Advanced Usage

### Multiple Config Files

```python
from coda.config import ConfigManager
from coda.config.models import ConfigPath, ConfigFormat

config = ConfigManager(
    app_name="myapp",
    config_paths=[
        ConfigPath(Path("/etc/myapp/base.toml"), ConfigFormat.TOML),
        ConfigPath(Path("./override.json"), ConfigFormat.JSON),
    ]
)
```

### Custom Environment Parsing

Environment variables are automatically parsed:
- `"true"/"false"` → boolean
- `"123"` → integer
- `"3.14"` → float
- `'{"key": "value"}'` → JSON object
- `"item1,item2"` → list (when using get_list)

### Nested Configuration

```python
# config.json
{
    "database": {
        "primary": {
            "host": "db1.example.com",
            "port": 5432
        },
        "replica": {
            "host": "db2.example.com",
            "port": 5432
        }
    }
}

# Access nested values
primary_host = config.get_string("database.primary.host")
replica_port = config.get_int("database.replica.port")
```

## File Format Examples

### JSON
```json
{
    "debug": true,
    "server": {
        "host": "0.0.0.0",
        "port": 8080
    }
}
```

### TOML
```toml
debug = true

[server]
host = "0.0.0.0"
port = 8080
```

### YAML
```yaml
debug: true
server:
  host: 0.0.0.0
  port: 8080
```

### INI
```ini
[DEFAULT]
debug = true

[server]
host = 0.0.0.0
port = 8080
```

## Testing

Run the standalone example to verify the module works independently:

```bash
python -m coda.config.example
```

## Notes

- TOML support uses Python 3.11+ `tomllib` or falls back to `tomli` if available
- YAML support requires `PyYAML` to be installed
- Basic TOML parsing is included as fallback for zero-dependency usage
- All file formats are optional - JSON works out of the box