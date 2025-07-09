# Testing Strategy - Containers vs Direct Execution

## Overview

We use a **tiered testing approach** to balance speed, cost, and coverage:

## Test Tiers

### 🟢 **Tier 1: Fast Tests** (Always run)
**Execution**: Direct on GitHub runners (no containers)
**Duration**: 1-3 minutes
**Triggers**: Every push, every PR

```bash
# What runs:
- Unit tests with mock providers
- Linting and formatting checks  
- Basic CLI functionality tests
- Code coverage analysis
```

**Why no containers needed:**
- ✅ Mock provider = no external dependencies
- ✅ Pure Python tests = no model downloads
- ✅ Fast feedback = quick PR validation
- ✅ Zero cost = no resource usage

### 🟡 **Tier 2: LLM Tests** (Selective)
**Execution**: Ollama container on GitHub runners
**Duration**: 5-10 minutes  
**Triggers**: Push to main/develop, manual trigger

```bash
# What runs:
- Real language model responses
- Ollama provider integration tests
- End-to-end conversation flows
- Performance timing tests
```

**Why containers needed:**
- 🐳 Ollama service = requires container runtime
- 📦 Model downloads = TinyLlama (~1GB)
- 🔄 Real inference = actual LLM responses
- 💰 Resource intensive = limited to important branches

### 🔴 **Tier 3: Integration Tests** (Manual/Release)
**Execution**: Direct with real API credentials
**Duration**: Variable
**Triggers**: Manual, pre-release validation

```bash
# What runs:
- OCI GenAI provider tests
- OpenAI/other cloud provider tests  
- Full multi-provider compatibility
- Performance benchmarks
```

## GitHub Workflows

### **test-fast.yml** ⚡ (No containers)
```yaml
# Runs on: Every push, every PR
# Duration: 1-3 minutes
# Dependencies: None

steps:
  - Install Python + uv directly
  - Run unit tests with mock providers
  - Run linting and formatting
  - Test basic CLI with mock responses
```

### **test-with-ollama.yml** 🐳 (Ollama container)
```yaml
# Runs on: Push to main/develop, manual trigger
# Duration: 5-10 minutes  
# Dependencies: Ollama container + TinyLlama model

steps:
  - Start Ollama service container
  - Download TinyLlama model (~1GB)
  - Run LLM tests with real responses
  - Test streaming and conversation context
```

## Developer Workflow

### **For Pull Requests:**
1. ✅ **Fast tests run automatically** (mock providers)
2. ✅ **Quick feedback** on code quality  
3. ✅ **No waiting** for expensive LLM tests
4. ✅ **Merge when green** checkmarks appear

### **For Main Branch:**
1. ✅ **Fast tests run first** (immediate feedback)
2. 🟡 **LLM tests run second** (comprehensive validation)
3. ✅ **Both must pass** for confidence
4. 🚀 **Deploy when all green**

### **For Development:**
```bash
# Local development (no containers)
make test-unit          # Mock provider tests
make test-fast          # Quick smoke tests
make lint               # Code quality

# Before merge (optional containers)  
make test-llm           # Local Ollama tests
make docker-test-llm    # Docker Ollama tests

# Pre-release (with credentials)
make test-integration   # Cloud provider tests
```

## Resource Optimization

### **Mock Tests = No Containers Needed**
- **Memory**: ~100MB (Python process only)
- **CPU**: Minimal (no inference)
- **Disk**: ~50MB (code + dependencies)
- **Network**: None (offline)
- **Time**: 10-30 seconds

### **LLM Tests = Ollama Container Required**  
- **Memory**: 2-4GB (model + inference)
- **CPU**: Significant (neural network inference)
- **Disk**: 1-2GB (model storage)
- **Network**: Model download on first run
- **Time**: 5-10 minutes

## When Each Approach Makes Sense

### **Use Direct Execution (No Containers) For:**
✅ Mock provider tests  
✅ Unit tests  
✅ Code linting/formatting  
✅ Basic CLI validation  
✅ Fast feedback loops  
✅ PR validation  

### **Use Containers For:**  
🐳 Real LLM inference  
🐳 Ollama integration tests  
🐳 End-to-end validation  
🐳 Performance testing  
🐳 Release validation  
🐳 Complex dependencies  

## Cost-Benefit Analysis

| Test Type | Container | Time | Resources | When to Run |
|-----------|-----------|------|-----------|-------------|
| **Unit** | ❌ No | 30s | Minimal | Every commit |
| **Mock** | ❌ No | 1min | Low | Every PR |  
| **LLM** | ✅ Yes | 5min | High | Main branch |
| **Integration** | ❌ No* | Variable | API costs | Manual |

*Integration tests use direct API calls, not containers

## Best Practices

### **For Speed:**
- Run mock tests first (fail fast)
- Use containers only when necessary  
- Cache models between runs
- Parallelize independent test suites

### **For Coverage:**
- Mock tests cover logic and edge cases
- LLM tests cover real-world behavior  
- Integration tests cover cloud compatibility
- All three together = comprehensive validation

### **For Cost:**
- Mock tests = free and unlimited
- LLM tests = GitHub runner minutes only
- Integration tests = API charges
- Smart triggering saves resources

## Summary

**Mock providers don't need containers** - they run directly on GitHub runners for fast, cost-effective testing. **Real LLM tests need Ollama containers** for actual model inference. This tiered approach gives you the best of both worlds: fast feedback for development and comprehensive validation for releases.