"""Unit tests for tool-cache CLI command."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from coda.apps.cli.tool_cache_command import tool_cache


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_tool_tester():
    """Create a mock OCIToolTester."""
    with patch('coda.apps.cli.tool_cache_command.OCIToolTester') as mock_class:
        mock_tester = MagicMock()
        mock_class.return_value = mock_tester
        yield mock_tester


class TestToolCacheCommand:
    """Test tool-cache CLI command."""
    
    def test_clear_cache(self, mock_tool_tester):
        """Test clearing the cache."""
        runner = CliRunner()
        result = runner.invoke(tool_cache, ['--clear'])
        
        assert result.exit_code == 0
        assert "Tool support cache cleared" in result.output
        mock_tool_tester.clear_cache.assert_called_once()
    
    def test_show_stats(self, mock_tool_tester):
        """Test showing cache statistics."""
        mock_tool_tester.get_cache_stats.return_value = {
            "total_cached": 10,
            "working": 5,
            "partial_support": 3,
            "not_working": 5,
            "cache_file": "/test/cache/file.json"
        }
        
        runner = CliRunner()
        result = runner.invoke(tool_cache, ['--stats'])
        
        assert result.exit_code == 0
        assert "OCI Tool Support Cache Statistics" in result.output
        assert "Total cached: 10 models" in result.output
        assert "Working: 5 models" in result.output
        assert "Partial support: 3 models" in result.output
        assert "Not working: 5 models" in result.output
        assert "Cache file: /test/cache/file.json" in result.output
    
    def test_test_model_success(self, mock_tool_tester):
        """Test testing a specific model successfully."""
        mock_tool_tester._test_model.return_value = {
            "tools_work": True,
            "streaming_tools": False,
            "tested": True,
            "error": None
        }
        
        with patch('coda.apps.cli.tool_cache_command.OCIGenAIProvider'):
            runner = CliRunner()
            result = runner.invoke(tool_cache, ['--test', 'test.model'])
            
            assert result.exit_code == 0
            assert "Testing model: test.model" in result.output
            assert "✅ Tools work: Yes" in result.output
            assert "⚠️  Streaming tools: No" in result.output
    
    def test_test_model_failure(self, mock_tool_tester):
        """Test testing a model that doesn't support tools."""
        mock_tool_tester._test_model.return_value = {
            "tools_work": False,
            "streaming_tools": False,
            "tested": True,
            "error": "fine-tuning base model"
        }
        
        with patch('coda.apps.cli.tool_cache_command.OCIGenAIProvider'):
            runner = CliRunner()
            result = runner.invoke(tool_cache, ['--test', 'test.model'])
            
            assert result.exit_code == 0
            assert "Testing model: test.model" in result.output
            assert "❌ Tools work: No" in result.output
            assert "Error: fine-tuning base model" in result.output
    
    def test_test_model_exception(self, mock_tool_tester):
        """Test handling exception during model testing."""
        with patch('coda.apps.cli.tool_cache_command.OCIGenAIProvider') as mock_provider:
            mock_provider.side_effect = Exception("Test error")
            
            runner = CliRunner()
            result = runner.invoke(tool_cache, ['--test', 'test.model'])
            
            assert result.exit_code == 0
            assert "Testing model: test.model" in result.output
            assert "❌ Test failed: Test error" in result.output
    
    def test_list_cache_empty(self, mock_tool_tester):
        """Test listing empty cache."""
        mock_tool_tester._cache = {}
        
        runner = CliRunner()
        result = runner.invoke(tool_cache)
        
        assert result.exit_code == 0
        assert "Tool support cache is empty" in result.output
    
    def test_list_cache_with_entries(self, mock_tool_tester):
        """Test listing cache with entries."""
        mock_tool_tester._cache = {
            "model1": {
                "tools_work": True,
                "streaming_tools": True,
                "tested": True,
                "test_date": "2025-07-29T10:00:00"
            },
            "model2": {
                "tools_work": True,
                "streaming_tools": False,
                "tested": True,
                "test_date": "2025-07-29T10:00:00"
            },
            "model3": {
                "tools_work": False,
                "streaming_tools": False,
                "tested": True,
                "error": "fine-tuning base model",
                "test_date": "2025-07-29T10:00:00"
            }
        }
        
        runner = CliRunner()
        result = runner.invoke(tool_cache)
        
        assert result.exit_code == 0
        assert "OCI Tool Support Cache" in result.output
        assert "model1" in result.output
        assert "model2" in result.output
        assert "model3" in result.output
        assert "Fully working" in result.output
        assert "Partial (non-streaming)" in result.output
        assert "Error: fine-tuning base model" in result.output
        assert "2025-07-29" in result.output
    
    def test_all_status_types(self, mock_tool_tester):
        """Test all different status types are displayed correctly."""
        mock_tool_tester._cache = {
            "fully_working": {
                "tools_work": True,
                "streaming_tools": True,
                "test_date": "2025-07-29T10:00:00"
            },
            "partial_working": {
                "tools_work": True,
                "streaming_tools": False,
                "test_date": "2025-07-29T10:00:00"
            },
            "not_working": {
                "tools_work": False,
                "streaming_tools": False,
                "test_date": "2025-07-29T10:00:00"
            },
            "error_model": {
                "tools_work": False,
                "streaming_tools": False,
                "error": "bad request (400)",
                "test_date": "2025-07-29T10:00:00"
            }
        }
        
        runner = CliRunner()
        result = runner.invoke(tool_cache)
        
        assert result.exit_code == 0
        # Check that all models appear with correct indicators
        assert "fully_working" in result.output
        assert "partial_working" in result.output
        assert "not_working" in result.output
        assert "error_model" in result.output
        
        # Check status descriptions
        assert "Fully working" in result.output
        assert "Partial (non-streaming)" in result.output
        assert "Not working" in result.output
        assert "Error: bad request (400)" in result.output