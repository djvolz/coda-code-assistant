# Enhanced Tab Completion

Coda's interactive CLI now features an enhanced tab completion system that makes command discovery and usage more efficient.

## Key Features

### 1. Fuzzy Command Matching
- **Exact match**: Type the full command name for highest priority
- **Prefix match**: Type the beginning of a command (e.g., `/ses` → `/session`)
- **Fuzzy match**: Type any characters in order (e.g., `/mdl` → `/model`)

### 2. Context-Aware Completions

#### Model Name Completion
When using `/model`, get completions for available models from your current provider:
```
/model gpt<TAB>
→ gpt-4
→ gpt-3.5-turbo
```

#### Session Name Completion
When using session commands, get completions for existing session names:
```
/session load proj<TAB>
→ project-review (10 messages, 2024-01-01)

/session delete bug<TAB>
→ bug-fix (5 messages, 2024-01-02)
```

#### Theme Name Completion
When switching themes, get completions for available themes:
```
/theme mono<TAB>
→ monokai
```

### 3. Command Aliases
Aliases are shown with their target command:
```
/h<TAB>
→ /h     → /help
→ /help  Show help
```

### 4. Subcommand Completion
After typing a command and space, get available subcommands:
```
/session <TAB>
→ save
→ load
→ list
→ delete
→ rename
```

### 5. File Path Completion
Automatic file path completion when typing paths:
- Paths starting with `/` or `~`
- Supports home directory expansion

## Visual Indicators

- **Bold cyan**: Exact or high-score command matches
- **Regular cyan**: Fuzzy command matches
- **Blue italic**: Command aliases
- **Green**: High-score subcommand matches
- **Yellow**: Fuzzy subcommand matches
- **Magenta**: Model names
- **Yellow**: Session names

## Performance Features

- **Completion caching**: Frequently used completions are cached
- **Threaded completion**: Completions run in separate thread for responsiveness
- **Smart sorting**: Results sorted by relevance score

## Usage Tips

1. **Press Tab once**: Show all available completions
2. **Type more characters**: Narrow down the results
3. **Use fuzzy matching**: Save keystrokes with partial matches
4. **Empty prompt + Tab**: See all available commands

## Technical Details

The enhanced completion system is built on:
- `prompt_toolkit`'s completion framework
- Custom fuzzy matching algorithm
- Dynamic completion architecture
- Command Registry integration

### Dynamic Completion System

The completion system automatically adapts to command registry changes:
1. **Commands**: Any command added to `CommandRegistry` is automatically available
2. **Subcommands**: Subcommands are loaded dynamically from the registry
3. **Completion Types**: Commands can specify a `completion_type` field:
   - `"model_name"`: Shows available models from current provider
   - `"session_name"`: Shows saved session names
   - `"theme_name"`: Shows available theme names
   - Custom types can be added by extending the `DynamicValueCompleter`

### Adding New Completions

To add completion for a new command:
1. Add the command to `CommandRegistry` in `command_registry.py`
2. Set the `completion_type` field if the command needs value completion
3. For subcommands needing completion, set `completion_type` on the subcommand

Example:
```python
CommandDefinition(
    name="mycommand",
    description="My new command",
    completion_type="my_value_type",  # Optional
)
```

No code changes needed in the completer - it's all dynamic!