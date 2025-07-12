# Testing Documentation

This directory contains all testing-related documentation for Coda.

## 📄 Documents

### [Testing Strategy](./TESTING_STRATEGY.md)
Comprehensive testing strategy covering:
- Test categories and organization
- Testing pyramid approach
- Module independence testing
- Integration testing patterns
- Performance testing guidelines

### [Session Testing Guide](./session_testing_guide.md)
Detailed guide for testing session functionality:
- Session creation and management
- Message handling and persistence
- Database operations testing
- Error handling scenarios

### [LLM Testing](./LLM_TESTING.md)
Guide for testing with Language Learning Models:
- Mock provider usage
- Testing LLM interactions
- Handling API responses
- Performance considerations

## 🧪 Quick Testing Reference

### Running Tests
```bash
# Run all tests
uv run pytest

# Run specific test category
uv run pytest tests/base/  # Base module tests
uv run pytest tests/services/  # Service layer tests
uv run pytest tests/apps/  # Application tests

# Run with coverage
uv run pytest --cov=coda --cov-report=html
```

### Test Organization
```
tests/
├── base/          # Base module tests (zero dependencies)
├── services/      # Service layer integration tests
├── apps/          # CLI and web app tests
└── utils/         # Test utilities and fixtures
```

## 📊 Testing Metrics

- **Total Tests**: 38+ tests across all layers
- **Module Independence Tests**: 8 tests
- **Integration Tests**: 15+ tests
- **UI Tests**: 9 tests
- **Coverage Target**: 80%+

## 🔗 Related

- [GitHub Issue #32](https://github.com/djvolz/coda-code-assistant/issues/32) - Comprehensive CLI test suite
- [Main Test Directory](../../tests/) - Actual test files
- [CI/CD Pipeline](https://github.com/djvolz/coda-code-assistant/issues/34) - Automated testing