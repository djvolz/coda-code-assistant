# Coda Modular Library Implementation Strategy

## Executive Summary

This document outlines the complete strategy for transforming Coda from a monolithic CLI application into a modular Python library. Based on the analysis of the current codebase and the modular library plan, we'll follow a phased approach that ensures backward compatibility while achieving true module independence.

## Current State Analysis

### Existing Architecture
- **Monolithic Structure**: All code under single `coda/` package
- **Tight Coupling**: Heavy dependencies on `configuration.py` and `constants.py`
- **Shared State**: Global configuration accessed throughout
- **Complex Dependencies**: Cross-module imports and circular dependency risks

### Key Modules to Refactor
1. **Constants** - Static values and enums (minimal work needed)
2. **Configuration** - Currently tightly integrated, needs abstraction
3. **Themes** - UI/terminal styling, depends on config
4. **Providers** - LLM integrations, good existing abstraction
5. **Tools** - Various utilities, some with heavy dependencies
6. **Agents** - High-level orchestration, depends on many modules

## Implementation Phases

### Phase 1: Foundation Modules (Week 1-2)

#### 1.1 Constants Module
**Current State**: `coda/constants.py` contains mixed concerns
**Target State**: Pure Python module with categorized constants

**Implementation Steps**:
1. Create new module structure:
   ```
   coda/constants/
   ├── __init__.py
   ├── definitions.py  # All constants
   ├── models.py       # Data classes/enums
   └── example.py      # Standalone demo
   ```

2. Categorize constants:
   - `UI` - Terminal/display constants
   - `API` - Provider/network constants
   - `DEFAULTS` - Default values
   - `LIMITS` - System limits

3. Remove all imports and external dependencies

4. Create backward compatibility wrapper in main coda package

**Success Criteria**:
- Zero imports except Python stdlib
- Can be copy-pasted to any project
- All existing code continues to work

#### 1.2 Config Module
**Current State**: `coda/configuration.py` with global state
**Target State**: Standalone config manager with dependency injection

**Implementation Steps**:
1. Create new module structure:
   ```
   src/coda/config/
   ├── __init__.py
   ├── manager.py      # Core config logic
   ├── models.py       # Config schemas
   ├── backends.py     # Storage backends
   └── example.py      # Standalone demo
   ```

2. Design new API:
   ```python
   # Instead of global get_config()
   config = ConfigManager(path="~/.myapp")
   value = config.get("key", default="value")
   ```

3. Implement storage backends:
   - JSON (no dependencies)
   - YAML (optional: pyyaml)
   - TOML (optional: tomli)

4. Create migration utilities for existing configs

5. Add Coda-specific wrapper for backward compatibility

**Success Criteria**:
- Works without any Coda imports
- Multiple storage backends
- Thread-safe operations
- Easy migration path

#### 1.3 Theme Module
**Current State**: `coda/themes.py` depends on configuration
**Target State**: Standalone terminal styling library

**Implementation Steps**:
1. Create new module structure:
   ```
   src/coda/theme/
   ├── __init__.py
   ├── manager.py      # Theme management
   ├── models.py       # Color/style definitions
   ├── presets.py      # Built-in themes
   └── example.py      # Standalone demo
   ```

2. Remove configuration dependency:
   - Accept theme data via constructor
   - No global state access
   - Optional rich/colorama backends

3. Implement theme features:
   - Color management
   - Style definitions
   - Terminal capability detection
   - Theme inheritance

4. Create preset themes:
   - Default (basic ANSI)
   - Dark (enhanced colors)
   - Light (for light terminals)
   - Minimal (no colors)

**Success Criteria**:
- Zero Coda dependencies
- Works with basic ANSI or rich
- Graceful fallbacks
- Easy theme customization

### Phase 2: Intelligence Module (Week 3-4)

#### 2.1 Provider Abstraction
**Current State**: Good abstraction in `providers/base.py`
**Target State**: Completely standalone provider system

**Implementation Steps**:
1. Create new module structure:
   ```
   src/coda/intelligence/
   ├── __init__.py
   ├── base.py         # Abstract interfaces
   ├── registry.py     # Provider registration
   ├── providers/
   │   ├── __init__.py
   │   ├── openai.py   # OpenAI implementation
   │   ├── anthropic.py # Anthropic implementation
   │   ├── ollama.py   # Ollama implementation
   │   └── mock.py     # Testing provider
   └── example.py      # Standalone demo
   ```

2. Extract provider interface:
   - Remove Coda-specific imports
   - Use dependency injection for config
   - Standard error handling

3. Implement provider registry:
   - Dynamic provider loading
   - Capability detection
   - Fallback mechanisms

4. Create unified API:
   ```python
   from coda.intelligence import get_provider
   
   provider = get_provider("openai", config={"api_key": "..."})
   response = provider.complete("Hello")
   ```

#### 2.2 Tool System Refactoring
**Current State**: Tools depend on various Coda modules
**Target State**: Plugin-based tool system

**Implementation Steps**:
1. Create tool abstraction layer
2. Remove Coda dependencies from tool implementations
3. Use dependency injection for required services
4. Create tool registry system

### Phase 3: Integration Layer (Week 5)

#### 3.1 Coda CLI Adapter
**Purpose**: Use all modular components in unified CLI

**Implementation Steps**:
1. Create integration module:
   ```
   src/coda/cli/
   ├── __init__.py
   ├── main.py         # Entry point
   ├── adapters.py     # Module adapters
   └── commands/       # CLI commands
   ```

2. Implement adapters for each module:
   - Config adapter (maintains backward compatibility)
   - Theme adapter (integrates with config)
   - Provider adapter (adds Coda-specific features)

3. Preserve existing CLI interface

#### 3.2 Migration Utilities
**Purpose**: Help users migrate to modular structure

**Tools to Create**:
1. Config migration script
2. Import rewriter for existing code
3. Dependency analyzer
4. Module extraction tool

### Phase 4: Testing & Documentation (Week 6)

#### 4.1 Independence Tests
**For each module**:
1. Copy-paste test (module works in isolation)
2. Import test (no Coda dependencies)
3. Minimal dependency test
4. API compatibility test

#### 4.2 Documentation
1. Module-specific READMEs
2. Migration guides
3. API documentation
4. Example applications

## Migration Strategy

### Step 1: Parallel Development
- Develop new modules alongside existing code
- No breaking changes initially
- Gradual adoption path

### Step 2: Adapter Layer
- Create adapters for backward compatibility
- Map old APIs to new modules
- Deprecation warnings for old usage

### Step 3: Incremental Migration
- Migrate one component at a time
- Update imports incrementally
- Maintain test coverage

### Step 4: Clean Break
- After stability period, remove old code
- Update all documentation
- Release as major version

## Technical Considerations

### Dependency Management
```toml
[project]
name = "coda"
dependencies = []  # Core has no dependencies

[project.optional-dependencies]
theme = ["rich>=10.0.0"]
config = ["pyyaml>=6.0", "tomli>=2.0"]
intelligence-openai = ["openai>=1.0"]
intelligence-anthropic = ["anthropic>=0.8"]
intelligence-all = ["openai>=1.0", "anthropic>=0.8", "litellm>=1.0"]
all = ["coda[theme,config,intelligence-all]"]
```

### Import Structure
```python
# Standalone usage
from coda.theme import Theme
from coda.config import Config
from coda.intelligence import get_provider

# Or after copy-paste
from theme import Theme
from config import Config
from intelligence import get_provider
```

### Backward Compatibility
```python
# Old code continues to work
from coda import get_config  # Adapter to new Config
from coda.themes import get_theme  # Adapter to new Theme
```

## Success Metrics

1. **Module Independence**
   - Each module has zero Coda imports
   - Modules work via copy-paste
   - Minimal third-party dependencies

2. **API Simplicity**
   - Intuitive interfaces
   - Clear documentation
   - Good defaults

3. **Performance**
   - No regression in speed
   - Reduced memory usage
   - Faster imports

4. **Adoption**
   - Easy migration path
   - Community feedback
   - External usage

## Risk Mitigation

### Risk: Breaking Changes
**Mitigation**: Comprehensive adapter layer, extensive testing

### Risk: Performance Regression
**Mitigation**: Benchmark before/after, optimize critical paths

### Risk: User Confusion
**Mitigation**: Clear documentation, migration tools, examples

### Risk: Maintenance Burden
**Mitigation**: Automated testing, clear module boundaries

## Timeline

- **Week 1-2**: Foundation modules (Constants, Config, Theme)
- **Week 3-4**: Intelligence module and providers
- **Week 5**: Integration layer and CLI
- **Week 6**: Testing, documentation, and release prep

## Next Steps

1. Review and approve this strategy
2. Set up new module structure
3. Begin with Constants module (simplest)
4. Iterate based on learnings

This modular approach will transform Coda into a flexible toolkit where developers can use exactly what they need, while maintaining the full-featured CLI experience for those who want everything.