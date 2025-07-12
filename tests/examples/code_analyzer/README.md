# Code Analyzer Example

An AI-powered code analysis tool using Coda's search and provider modules.

## Features

- **Semantic Code Search**: Find code by meaning, not just keywords
- **Code Analysis**: Get AI insights about code functionality
- **Function Explanation**: Detailed explanations of specific functions
- **Similar Code Detection**: Find code patterns across your repository
- **Code Review**: Get AI-powered code reviews for specific files
- **Repository Indexing**: Fast semantic search across entire codebases

## Prerequisites

- Python 3.8+
- Coda modules installed with search support
- At least one AI provider configured
- A code repository to analyze

## Setup

1. Install Coda with async support:
   ```bash
   pip install -e ../../..
   ```

2. Configure your AI provider (see simple-chatbot example)

3. Ensure your repository has readable source files

## Usage

Run the analyzer on a repository:

```bash
# Analyze current directory
python code_analyzer.py .

# Analyze specific repository
python code_analyzer.py /path/to/repository

# Pass path as argument
python code_analyzer.py ~/projects/my-app
```

### Menu Options

1. **Analyze code by query** - Search and analyze code semantically
2. **Explain a function** - Get detailed explanation of a function
3. **Find similar code** - Find code similar to a snippet
4. **Review a file** - Get AI code review for a specific file
5. **Re-index repository** - Update the search index
6. **Quit** - Exit the analyzer

## Example Sessions

### Code Analysis

```
Choice: 1
Enter search query: error handling in database connections

Searching for: error handling in database connections
Found 5 relevant code sections

Analyzing code with AI...

=== Analysis ===
Based on the code sections found, here's an analysis of error handling in database connections:

## Summary
The codebase implements error handling for database connections in several places:
1. Connection establishment with retry logic
2. Query execution with transaction rollback
3. Connection pool management with health checks

## Potential Issues
1. **Inconsistent Error Types**: Some modules catch generic Exception while others catch specific database errors
2. **Missing Timeout Handling**: Connection attempts don't have configurable timeouts
3. **Logging Gaps**: Not all database errors are logged with sufficient context

## Best Practices Applied
✓ Transaction rollback on errors
✓ Connection retry with exponential backoff
✓ Resource cleanup in finally blocks

## Improvement Suggestions
1. Standardize error handling with a DatabaseError base class
2. Add connection timeout configuration
3. Implement circuit breaker pattern for repeated failures
4. Add structured logging with error context
=== End Analysis ===

[Tokens used: 487]
```

### Function Explanation

```
Choice: 2
Enter function name: connect_to_database

Found 'connect_to_database' in src/db/connection.py

=== Explanation of connect_to_database ===
## Purpose and Functionality
The `connect_to_database` function establishes a connection to a PostgreSQL database with automatic retry logic and connection pooling.

## Parameters
- `config` (dict): Database configuration containing:
  - `host`: Database server hostname
  - `port`: Connection port (default: 5432)
  - `database`: Database name
  - `user`: Username for authentication
  - `password`: Password for authentication
  - `pool_size`: Maximum number of connections (default: 10)

## Return Values
- Returns: `DatabaseConnection` object on success
- Raises: `DatabaseConnectionError` after all retries fail

## Example Usage
```python
config = {
    "host": "localhost",
    "port": 5432,
    "database": "myapp",
    "user": "appuser",
    "password": "secure_password",
    "pool_size": 20
}

try:
    db = connect_to_database(config)
    # Use database connection
    result = db.execute("SELECT * FROM users")
finally:
    db.close()
```

## Side Effects and Dependencies
- Creates persistent database connections
- Logs connection attempts to application logger
- Depends on `psycopg2` library
- May block for up to 30 seconds (3 retries × 10s timeout)

## Edge Cases
1. Network interruptions trigger automatic retry
2. Invalid credentials fail immediately (no retry)
3. Pool exhaustion raises `PoolExhaustedError`
4. Handles PostgreSQL server restarts gracefully
=== End Explanation ===
```

### Finding Similar Code

```
Choice: 3
Enter code snippet (end with '---' on a new line):
def process_items(items):
    results = []
    for item in items:
        if item.is_valid():
            results.append(transform(item))
    return results
---

Searching for code similar to:
def process_items(items):
    results = []
    for item in items:
        if item.is_valid():
            results.append(transform(item))
    return results

=== Found 3 Similar Code Sections ===

1. src/data/processor.py:45 (similarity: 0.89)
```python
def process_records(records):
    processed = []
    for record in records:
        if record.validate():
            processed.append(convert(record))
    return processed
```

2. src/utils/transformer.py:102 (similarity: 0.82)
```python
def filter_and_transform(data_list):
    output = []
    for data in data_list:
        if check_validity(data):
            transformed = apply_transformation(data)
            output.append(transformed)
    return output
```

3. src/handlers/batch.py:67 (similarity: 0.78)
```python
def batch_process(batch_items):
    results = []
    for item in batch_items:
        try:
            if item.is_valid():
                result = transform_item(item)
                results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {item}: {e}")
    return results
```
```

### Code Review

```
Choice: 4
Enter file path (relative to repository): src/auth/login.py

Reviewing src/auth/login.py...

=== Code Review ===
## Code Quality Assessment

### Strengths
- Clear function names and purpose
- Good separation of concerns
- Proper use of type hints

### Issues Found

1. **Security Concern - Timing Attack**
   ```python
   if user.password == provided_password:  # Line 23
   ```
   Use constant-time comparison to prevent timing attacks:
   ```python
   import secrets
   if secrets.compare_digest(user.password, provided_password):
   ```

2. **Missing Input Validation**
   The username and password aren't validated for length or content.
   Add validation:
   ```python
   if not (3 <= len(username) <= 50):
       raise ValueError("Username must be 3-50 characters")
   ```

3. **No Rate Limiting**
   Login attempts should be rate-limited to prevent brute force attacks.

4. **Plain Text Password Storage**
   Passwords appear to be stored in plain text. Use bcrypt or argon2:
   ```python
   from passlib.hash import argon2
   if argon2.verify(provided_password, user.password_hash):
   ```

### Performance Suggestions
- Add database index on username field for faster lookups
- Consider caching user sessions to reduce database queries

### Best Practices
- Add comprehensive logging for security events
- Implement account lockout after failed attempts
- Use prepared statements for SQL queries
- Add unit tests for authentication logic

### Priority Fixes
1. HIGH: Fix password storage (security)
2. HIGH: Add rate limiting (security)  
3. MEDIUM: Input validation (security)
4. LOW: Performance optimizations
=== End Review ===
```

## How It Works

1. **Repository Indexing**: The search module indexes all code files
2. **Semantic Search**: Finds relevant code by meaning, not just text matching
3. **Context Building**: Assembles relevant code snippets for analysis
4. **AI Analysis**: Sends context to AI provider for insights
5. **Structured Output**: Presents analysis in organized format

## Extending the Example

### Add Language-Specific Analysis

```python
async def analyze_python_code(self, query: str):
    results = await self.search.search(f"{query} language:python", limit=10)
    # Python-specific analysis prompt
    
async def analyze_javascript_code(self, query: str):
    results = await self.search.search(f"{query} language:javascript", limit=10)
    # JavaScript-specific analysis prompt
```

### Add Dependency Analysis

```python
async def analyze_dependencies(self, module_name: str):
    # Search for import statements
    import_results = await self.search.search(f"import {module_name}")
    from_results = await self.search.search(f"from {module_name}")
    
    # Build dependency graph
    # Analyze usage patterns
```

### Add Security Scanning

```python
async def security_scan(self):
    vulnerabilities = [
        "eval(", "exec(", "__import__", 
        "os.system", "subprocess.call",
        "pickle.loads", "yaml.load"
    ]
    
    for vuln in vulnerabilities:
        results = await self.search.search(vuln)
        if results:
            self.analyze_security_issue(vuln, results)
```

## Performance Tips

1. **Index Once**: Initial indexing can be slow for large repos
2. **Incremental Updates**: Re-index only changed files
3. **Limit Search Results**: Use appropriate limits for better performance
4. **Cache Results**: Store analysis results for repeated queries

## Troubleshooting

### Indexing fails
- Check file permissions
- Ensure sufficient disk space for index
- Verify supported file types
- Check for binary files causing issues

### Search returns no results  
- Verify repository was indexed successfully
- Try broader search terms
- Check if files have expected extensions
- Ensure files aren't in .gitignore

### AI analysis errors
- Verify AI provider is configured correctly
- Check API rate limits
- Ensure sufficient context length
- Monitor token usage

### Memory issues with large repos
- Index in batches
- Limit file size for indexing
- Exclude large binary files
- Use streaming for large files