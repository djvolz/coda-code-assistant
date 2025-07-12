# TODO Fixes - Config and Theme Integration

## Summary

Fixed several TODOs related to config module integration and theme manager updates.

## Changes Made

### 1. Config Module Path Methods

Added standard directory methods to `ConfigManager` in `coda/base/config/manager.py`:
- `get_config_dir()` - Returns config directory (respects XDG_CONFIG_HOME)
- `get_data_dir()` - Returns data directory (respects XDG_DATA_HOME)  
- `get_cache_dir()` - Returns cache directory (respects XDG_CACHE_HOME)

### 2. Interactive CLI Updates

Fixed in `coda/apps/cli/interactive_cli.py`:
- **History File Path**: Now uses `config.get_config_dir()` instead of hardcoded path
- **Theme Manager Console**: Uses `ThemeManager().get_console()` instead of creating raw Console
- **Theme Switching**: Uses ThemeManager for theme changes instead of TODO placeholder

### 3. Observability Module Updates

Fixed in `coda/base/observability/manager.py`:
- **Export Directory**: Now uses `config.get_cache_dir()` for default observability export path

Fixed in `coda/base/observability/health.py`:
- **Database Path**: Now uses `config.get_data_dir()` for session database path
- **Directory Checks**: Now uses config methods to get directories for health checks

### 4. Bug Fix

Fixed a bug in `ConfigManager._load_environment_vars()` where it would crash if environment variables created conflicting nested structures.

## Benefits

1. **Centralized Path Management**: All paths now come from the config module
2. **XDG Compliance**: Respects XDG_CONFIG_HOME, XDG_DATA_HOME, XDG_CACHE_HOME environment variables
3. **Consistency**: All modules use the same path resolution logic
4. **Theme Integration**: Proper use of the new theme manager throughout the CLI

## Testing

All modified files compile successfully:
```bash
python3 -m py_compile coda/apps/cli/interactive_cli.py
python3 -m py_compile coda/base/observability/manager.py  
python3 -m py_compile coda/base/observability/health.py
python3 -m py_compile coda/base/config/manager.py
```

Path methods work correctly:
```python
from coda.base.config import ConfigManager
cm = ConfigManager('coda')
print(cm.get_config_dir())  # /Users/danny/.config/coda
print(cm.get_data_dir())    # /Users/danny/.local/share/coda
print(cm.get_cache_dir())   # /Users/danny/.cache/coda
```