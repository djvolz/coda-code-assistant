# Test Plan for OCI GenAI Tool Support

## Prerequisites
- Ensure `OCI_COMPARTMENT_ID` is set
- Ensure OCI CLI is configured (`~/.oci/config`)

## Test 1: Basic Tool Cache Command
```bash
# Check if command is registered
uv run coda tool-cache --help

# View cache statistics
uv run coda tool-cache --stats

# List cached results (should show prepopulated data)
uv run coda tool-cache

# Test a specific model
uv run coda tool-cache --test cohere.command-r-plus
```

## Test 2: Model Selection UI
```bash
# Start interactive mode with tools
uv run coda chat --tools

# When selecting a model, you should see:
# - 🔧 Tools - for models with full support
# - ⚠️ Partial Tools - for models with non-streaming only
# - 🚫 Tool Error - for models that don't work
```

## Test 3: Tool Support Errors
```bash
# Test with a model that doesn't support tools
uv run coda agent --provider oci_genai --model meta.llama-3.3-70b-instruct --tools "What's the weather?"

# Expected: Clear error message about fine-tuning base model

# Test with a model that has partial support
uv run coda agent --provider oci_genai --model cohere.command-r-plus --tools "What's the weather?"

# Expected: Should work (may show warning about streaming)
```

## Test 4: Python Test Scripts
```bash
# Test the OCIToolTester directly
uv run python test_oci_tool_support.py

# Test the CLI command programmatically
uv run python test_tool_cache_cli.py
```

## Test 5: Cache Behavior
```bash
# Clear cache
uv run coda tool-cache --clear

# List (should be empty or just prepopulated)
uv run coda tool-cache

# Test a new model (will populate cache)
uv run coda tool-cache --test xai.grok-3

# List again (should show the tested model)
uv run coda tool-cache
```

## Test 6: Actual Tool Usage
```bash
# Test with a working model
uv run coda agent --provider oci_genai --model cohere.command-r-plus --tools << 'EOF'
Use the get_current_directory tool to show me where we are
EOF

# Test one-shot mode
uv run coda agent --provider oci_genai --model cohere.command-r-plus --tools --one-shot "Use the get_current_directory tool"
```

## Expected Results

### Cache File Location
Check that cache file exists at:
```bash
ls -la ~/.cache/coda/oci_tools/tool_support.json
```

### Prepopulated Data
The cache should contain entries for all tested models with:
- `tools_work`: boolean
- `streaming_tools`: boolean  
- `tested`: true
- `test_date`: ISO timestamp
- `error`: (optional) error category

### Error Messages
When using tools with unsupported models, you should see:
```
Model 'MODEL_NAME' does not support tool/function calling. 
Known issue: ERROR_TYPE. 
Please use a model that supports tools or disable tool usage.
```

## Debugging
If tests fail, check:
1. `~/.cache/coda/oci_tools/tool_support.json` contents
2. OCI configuration with `oci iam user get --user-id $(oci iam user list --query 'data[0].id' --raw-output)`
3. Python imports: `uv run python -c "from coda.base.providers.oci_tool_tester import OCIToolTester"`
4. Logs for any error messages