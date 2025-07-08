"""Unit tests for data sanitizer."""

import re

import pytest

from coda.observability.sanitizer import DataSanitizer


class TestDataSanitizer:
    """Test the DataSanitizer class."""

    @pytest.fixture
    def sanitizer(self):
        """Create a DataSanitizer instance."""
        return DataSanitizer()

    def test_password_sanitization(self, sanitizer):
        """Test password sanitization in strings."""
        test_cases = [
            ("My password is secret123", "My password is ***REDACTED***"),
            ("password=mysecret&user=john", "password=***REDACTED***&user=john"),
            ("pwd: topsecret", "pwd: ***REDACTED***"),
            ("PASSWORD='my_password'", "PASSWORD=***REDACTED***"),
            ("No passwords here", "No passwords here"),
        ]

        for input_str, expected in test_cases:
            result = sanitizer.sanitize_string(input_str)
            assert result == expected

    def test_api_key_sanitization(self, sanitizer):
        """Test API key sanitization."""
        test_cases = [
            ("api_key=sk-1234567890abcdef", "api_key=***REDACTED***"),
            ("API_KEY: AKIAIOSFODNN7EXAMPLE", "API_KEY: ***REDACTED***"),
            ("apikey='my-secret-key'", "apikey=***REDACTED***"),
            ("key=abc123xyz", "key=***REDACTED***"),
            ("The quick brown fox", "The quick brown fox"),
        ]

        for input_str, expected in test_cases:
            result = sanitizer.sanitize_string(input_str)
            assert result == expected

    def test_token_sanitization(self, sanitizer):
        """Test token sanitization."""
        test_cases = [
            ("token=eyJhbGciOiJIUzI1NiIs", "token=***REDACTED***"),
            ("auth_token: Bearer abc123", "auth_token: ***REDACTED***"),
            ("TOKEN='secret-token'", "TOKEN=***REDACTED***"),
            ("access_token=my_token_123", "access_token=***REDACTED***"),
        ]

        for input_str, expected in test_cases:
            result = sanitizer.sanitize_string(input_str)
            assert result == expected

    def test_secret_sanitization(self, sanitizer):
        """Test secret sanitization."""
        test_cases = [
            ("secret=topsecret123", "secret=***REDACTED***"),
            ("client_secret: mysecret", "client_secret: ***REDACTED***"),
            ("SECRET_KEY='django-secret'", "SECRET_KEY=***REDACTED***"),
        ]

        for input_str, expected in test_cases:
            result = sanitizer.sanitize_string(input_str)
            assert result == expected

    def test_dict_sanitization(self, sanitizer):
        """Test dictionary sanitization."""
        input_dict = {
            "username": "john_doe",
            "password": "mysecret123",
            "api_key": "sk-abc123",
            "data": {"token": "bearer-token", "safe_field": "this is safe"},
            "config": {"database": "mydb", "db_password": "dbpass123"},
        }

        result = sanitizer.sanitize_dict(input_dict)

        assert result["username"] == "john_doe"
        assert result["password"] == "***REDACTED***"
        assert result["api_key"] == "***REDACTED***"
        assert result["data"]["token"] == "***REDACTED***"
        assert result["data"]["safe_field"] == "this is safe"
        assert result["config"]["database"] == "mydb"
        assert result["config"]["db_password"] == "***REDACTED***"

    def test_dict_with_list_sanitization(self, sanitizer):
        """Test sanitization of dictionaries containing lists."""
        input_dict = {
            "items": [{"name": "item1", "key": "secret"}, {"name": "item2", "password": "pass123"}],
            "tokens": ["token1", "token2"],
            "safe_list": [1, 2, 3],
        }

        result = sanitizer.sanitize_dict(input_dict)

        assert result["items"][0]["key"] == "***REDACTED***"
        assert result["items"][1]["password"] == "***REDACTED***"
        assert result["tokens"] == ["token1", "token2"]  # List items as strings
        assert result["safe_list"] == [1, 2, 3]

    def test_mixed_data_sanitization(self, sanitizer):
        """Test sanitization of mixed data types."""
        input_data = {
            "string_field": "password=secret",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "none_field": None,
            "nested": {"api_key": "my-api-key"},
        }

        result = sanitizer.sanitize_dict(input_data)

        assert "password=" in result["string_field"]
        assert "***REDACTED***" in result["string_field"]
        assert result["int_field"] == 42
        assert result["float_field"] == 3.14
        assert result["bool_field"] is True
        assert result["none_field"] is None
        assert result["nested"]["api_key"] == "***REDACTED***"

    def test_case_insensitive_matching(self, sanitizer):
        """Test case-insensitive pattern matching."""
        test_cases = [
            ("PASSWORD=secret", "PASSWORD=***REDACTED***"),
            ("Password=secret", "Password=***REDACTED***"),
            ("password=secret", "password=***REDACTED***"),
            ("PaSsWoRd=secret", "PaSsWoRd=***REDACTED***"),
        ]

        for input_str, expected in test_cases:
            result = sanitizer.sanitize_string(input_str)
            assert result == expected

    def test_multiple_patterns_in_string(self, sanitizer):
        """Test multiple sensitive patterns in one string."""
        input_str = "password=secret123&api_key=sk-abc&token=bearer123"
        result = sanitizer.sanitize_string(input_str)

        assert "password=***REDACTED***" in result
        assert "api_key=***REDACTED***" in result
        assert "token=***REDACTED***" in result
        assert "secret123" not in result
        assert "sk-abc" not in result
        assert "bearer123" not in result

    def test_empty_inputs(self, sanitizer):
        """Test handling of empty inputs."""
        assert sanitizer.sanitize_string("") == ""
        assert sanitizer.sanitize_dict({}) == {}
        assert sanitizer.sanitize_string(None) == ""
        assert sanitizer.sanitize_dict(None) == {}

    def test_special_characters_in_values(self, sanitizer):
        """Test handling of special characters in sensitive values."""
        test_cases = [
            ("password=p@ssw0rd!", "password=***REDACTED***"),
            ("api_key=$ecret-key#123", "api_key=***REDACTED***"),
            ("token=my.token.with.dots", "token=***REDACTED***"),
        ]

        for input_str, expected in test_cases:
            result = sanitizer.sanitize_string(input_str)
            assert result == expected

    def test_url_with_credentials(self, sanitizer):
        """Test sanitization of URLs with embedded credentials."""
        input_str = "mongodb://user:password123@localhost:27017/db"
        result = sanitizer.sanitize_string(input_str)
        assert "password123" not in result
        assert "***REDACTED***" in result

    def test_json_string_sanitization(self, sanitizer):
        """Test sanitization of JSON strings."""
        import json

        data = {"password": "secret", "user": "john"}
        json_str = json.dumps(data)

        result = sanitizer.sanitize_string(json_str)
        assert "secret" not in result
        assert "***REDACTED***" in result
        assert "john" in result

    def test_custom_patterns(self):
        """Test adding custom patterns to sanitizer."""
        # Create sanitizer with custom patterns
        custom_patterns = [
            r'credit_card["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
            r'ssn["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
        ]

        # For this test, we'll modify the sanitizer's patterns
        sanitizer = DataSanitizer()
        _original_patterns = sanitizer.patterns.copy()

        # Add custom patterns
        for pattern in custom_patterns:
            sanitizer.patterns.append(re.compile(pattern, re.IGNORECASE))

        # Test custom patterns
        input_str = "credit_card=1234-5678-9012-3456 and ssn=123-45-6789"
        result = sanitizer.sanitize_string(input_str)

        assert "1234-5678-9012-3456" not in result
        assert "123-45-6789" not in result
        assert result.count("***REDACTED***") == 2

    def test_performance_with_large_data(self, sanitizer):
        """Test performance with large data structures."""
        # Create a large nested structure
        large_dict = {
            f"level1_{i}": {
                f"level2_{j}": {
                    "password": f"secret_{i}_{j}",
                    "data": "x" * 1000,
                    "api_key": f"key_{i}_{j}",
                }
                for j in range(10)
            }
            for i in range(10)
        }

        # Should complete without significant delay
        result = sanitizer.sanitize_dict(large_dict)

        # Verify sanitization worked
        for i in range(10):
            for j in range(10):
                level2 = result[f"level1_{i}"][f"level2_{j}"]
                assert level2["password"] == "***REDACTED***"
                assert level2["api_key"] == "***REDACTED***"
                assert len(level2["data"]) == 1000
