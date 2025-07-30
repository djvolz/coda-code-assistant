"""Unit tests for OCIToolTester."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coda.base.providers.oci_tool_tester import OCIToolTester


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tool_tester(temp_cache_dir):
    """Create an OCIToolTester with a temporary cache directory."""
    with patch('coda.base.providers.oci_tool_tester.get_config_service') as mock_config:
        mock_config_service = MagicMock()
        mock_config_service.get_cache_dir.return_value = temp_cache_dir
        mock_config.return_value = mock_config_service
        
        tester = OCIToolTester()
        yield tester


class TestOCIToolTester:
    """Test OCIToolTester functionality."""
    
    def test_init_creates_cache_directory(self, temp_cache_dir):
        """Test that initialization creates the cache directory."""
        with patch('coda.services.config.get_config_service') as mock_config:
            mock_config_service = MagicMock()
            mock_config_service.get_cache_dir.return_value = temp_cache_dir
            mock_config.return_value = mock_config_service
            
            # Also need to patch inside OCIToolTester.__init__
            with patch('coda.base.providers.oci_tool_tester.get_config_service') as mock_config2:
                mock_config2.return_value = mock_config_service
                
                OCIToolTester()
                
                oci_tools_dir = temp_cache_dir / "oci_tools"
                assert oci_tools_dir.exists()
                assert oci_tools_dir.is_dir()
    
    def test_load_cache_empty(self, tool_tester):
        """Test loading an empty cache."""
        assert tool_tester._cache == {}
    
    def test_save_and_load_cache(self, tool_tester):
        """Test saving and loading cache data."""
        test_data = {
            "test.model": {
                "tools_work": True,
                "streaming_tools": False,
                "tested": True,
                "test_date": datetime.now().isoformat()
            }
        }
        
        tool_tester._cache = test_data
        tool_tester._save_cache()
        
        # Create a new tester to load the saved cache
        new_tester = OCIToolTester()
        new_tester.cache_file = tool_tester.cache_file
        loaded_cache = new_tester._load_cache()
        
        assert loaded_cache == test_data
    
    def test_get_tool_support_cached(self, tool_tester):
        """Test getting tool support for a cached model."""
        model_id = "test.model"
        cached_data = {
            "tools_work": True,
            "streaming_tools": False,
            "tested": True,
            "test_date": datetime.now().isoformat()
        }
        
        tool_tester._cache[model_id] = cached_data
        result = tool_tester.get_tool_support(model_id)
        
        assert result == cached_data
    
    def test_get_tool_support_expired_cache(self, tool_tester):
        """Test that expired cache entries are not used."""
        model_id = "test.model"
        old_date = (datetime.now() - timedelta(days=8)).isoformat()
        
        tool_tester._cache[model_id] = {
            "tools_work": True,
            "streaming_tools": False,
            "tested": True,
            "test_date": old_date
        }
        
        # Without provider, should return unknown status
        result = tool_tester.get_tool_support(model_id)
        
        assert result["tools_work"] is False
        assert result["tested"] is False
        assert "No provider available" in result["error"]
    
    def test_get_tool_support_no_provider(self, tool_tester):
        """Test getting tool support without a provider."""
        result = tool_tester.get_tool_support("unknown.model")
        
        assert result["tools_work"] is False
        assert result["streaming_tools"] is False
        assert result["tested"] is False
        assert "No provider available" in result["error"]
    
    def test_test_model_success(self, tool_tester):
        """Test successful model testing."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = [MagicMock()]
        mock_provider.chat.return_value = mock_response
        
        # Mock streaming response
        mock_chunk = MagicMock()
        mock_chunk.tool_calls = [MagicMock()]
        mock_provider.chat_stream.return_value = [mock_chunk]
        
        result = tool_tester._test_model("test.model", mock_provider)
        
        assert result["tools_work"] is True
        assert result["streaming_tools"] is True
        assert result["tested"] is True
        assert result["error"] is None
    
    def test_test_model_no_tool_calls(self, tool_tester):
        """Test model that doesn't return tool calls."""
        mock_provider = MagicMock()
        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_provider.chat.return_value = mock_response
        
        result = tool_tester._test_model("test.model", mock_provider)
        
        assert result["tools_work"] is False
        assert result["streaming_tools"] is False
        assert result["tested"] is True
        assert result["error"] is None
    
    def test_test_model_error(self, tool_tester):
        """Test model testing with error."""
        mock_provider = MagicMock()
        mock_provider.chat.side_effect = Exception("Model test.model is a fine-tuning base model")
        
        result = tool_tester._test_model("test.model", mock_provider)
        
        assert result["tools_work"] is False
        assert result["streaming_tools"] is False
        assert result["tested"] is True
        assert result["error"] == "fine-tuning base model"
    
    def test_categorize_error(self, tool_tester):
        """Test error categorization."""
        assert tool_tester._categorize_error("fine-tuning base model error") == "fine-tuning base model"
        assert tool_tester._categorize_error("404 not found") == "model not found (404)"
        assert tool_tester._categorize_error("400 bad request") == "bad request (400)"
        assert tool_tester._categorize_error("feature not supported") == "not supported"
        assert tool_tester._categorize_error("short error") == "short error"
        assert tool_tester._categorize_error("a" * 60) == "a" * 50 + "..."
    
    def test_clear_cache_all(self, tool_tester):
        """Test clearing entire cache."""
        tool_tester._cache = {
            "model1": {"tools_work": True},
            "model2": {"tools_work": False}
        }
        
        tool_tester.clear_cache()
        
        assert tool_tester._cache == {}
    
    def test_clear_cache_single_model(self, tool_tester):
        """Test clearing cache for a single model."""
        tool_tester._cache = {
            "model1": {"tools_work": True},
            "model2": {"tools_work": False}
        }
        
        tool_tester.clear_cache("model1")
        
        assert "model1" not in tool_tester._cache
        assert "model2" in tool_tester._cache
    
    def test_get_cache_stats(self, tool_tester):
        """Test getting cache statistics."""
        tool_tester._cache = {
            "model1": {"tools_work": True, "streaming_tools": True},
            "model2": {"tools_work": True, "streaming_tools": False},
            "model3": {"tools_work": False, "streaming_tools": False}
        }
        
        stats = tool_tester.get_cache_stats()
        
        assert stats["total_cached"] == 3
        assert stats["working"] == 2
        assert stats["partial_support"] == 1
        assert stats["not_working"] == 1
        assert str(tool_tester.cache_file) in stats["cache_file"]
    
    def test_prepopulate_known_results(self, tool_tester):
        """Test prepopulating known results."""
        # Clear any existing cache
        tool_tester._cache = {}
        
        updated = tool_tester.prepopulate_known_results()
        
        # Should have prepopulated some models
        assert updated > 0
        assert len(tool_tester._cache) > 0
        
        # Check a known working model
        assert "cohere.command-r-plus" in tool_tester._cache
        assert tool_tester._cache["cohere.command-r-plus"]["tools_work"] is True
        assert tool_tester._cache["cohere.command-r-plus"]["streaming_tools"] is False
        
        # Check a known non-working model
        assert "meta.llama-3.3-70b-instruct" in tool_tester._cache
        assert tool_tester._cache["meta.llama-3.3-70b-instruct"]["tools_work"] is False
        assert tool_tester._cache["meta.llama-3.3-70b-instruct"]["error"] == "fine-tuning base model"
    
    def test_prepopulate_doesnt_overwrite_recent(self, tool_tester):
        """Test that prepopulate doesn't overwrite recent cache entries."""
        model_id = "cohere.command-r-plus"
        recent_data = {
            "tools_work": False,  # Different from prepopulated
            "streaming_tools": False,
            "tested": True,
            "test_date": datetime.now().isoformat()
        }
        
        tool_tester._cache[model_id] = recent_data
        updated = tool_tester.prepopulate_known_results()
        
        # Should not have updated the recent entry
        assert tool_tester._cache[model_id]["tools_work"] is False