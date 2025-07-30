"""Dynamic tool testing for OCI GenAI models."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from coda.services.config import get_config_service

from .base import Message, Role, Tool


class OCIToolTester:
    """Tests and caches tool support for OCI GenAI models."""
    
    def __init__(self):
        """Initialize the tool tester using centralized config."""
        # Use centralized cache directory from config service
        config_service = get_config_service()
        cache_dir = config_service.get_cache_dir() / "oci_tools"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = cache_dir / "tool_support.json"
        self.cache_duration = timedelta(days=7)  # Cache for a week
        self.logger = logging.getLogger(__name__)
        
        # Load cached results at startup
        self._cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cached test results from JSON file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to JSON file."""
        try:
            # Write to temp file first for safety
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, "w") as f:
                json.dump(self._cache, f, indent=2)
            # Atomic rename
            temp_file.replace(self.cache_file)
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
    
    def get_tool_support(self, model_id: str, provider=None) -> Dict[str, Any]:
        """
        Get tool support information for a model.
        
        Returns dict with:
        - tools_work: bool - whether tools work at all
        - streaming_tools: bool - whether tools work in streaming
        - error: str - error message if tools don't work
        - tested: bool - whether this has been tested
        - test_date: str - when it was tested
        """
        # Check cache first
        if model_id in self._cache:
            entry = self._cache[model_id]
            test_date = datetime.fromisoformat(entry.get("test_date", "2000-01-01"))
            if datetime.now() - test_date < self.cache_duration:
                return entry
        
        # If no provider given, return unknown status
        if not provider:
            return {
                "tools_work": False,
                "streaming_tools": False,
                "tested": False,
                "error": "No provider available for testing"
            }
        
        # Test the model
        result = self._test_model(model_id, provider)
        
        # Cache the result
        result["test_date"] = datetime.now().isoformat()
        self._cache[model_id] = result
        self._save_cache()
        
        return result
    
    def _test_model(self, model_id: str, provider) -> Dict[str, Any]:
        """Test a model's tool support."""
        # Create a simple test tool
        test_tool = Tool(
            name="get_test_result",
            description="Get a test result",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        messages = [
            Message(role=Role.USER, content="Please use the get_test_result tool.")
        ]
        
        result = {
            "tools_work": False,
            "streaming_tools": False,
            "tested": True,
            "error": None
        }
        
        # Test non-streaming
        try:
            response = provider.chat(
                messages=messages,
                model=model_id,
                tools=[test_tool],
                max_tokens=100,
                temperature=0.1
            )
            
            if response.tool_calls:
                result["tools_work"] = True
                self.logger.info(f"Model {model_id} supports tools (non-streaming)")
            else:
                self.logger.info(f"Model {model_id} returned no tool calls")
                
        except Exception as e:
            error_msg = str(e)
            result["error"] = self._categorize_error(error_msg)
            self.logger.warning(f"Model {model_id} tool test failed: {result['error']}")
            return result
        
        # Test streaming only if non-streaming works
        if result["tools_work"]:
            try:
                stream = provider.chat_stream(
                    messages=messages,
                    model=model_id,
                    tools=[test_tool],
                    max_tokens=100,
                    temperature=0.1
                )
                
                tool_calls_found = False
                for chunk in stream:
                    if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                        tool_calls_found = True
                        break
                
                if tool_calls_found:
                    result["streaming_tools"] = True
                    self.logger.info(f"Model {model_id} supports tools in streaming")
                else:
                    self.logger.info(f"Model {model_id} does not support tools in streaming")
                    
            except Exception as e:
                self.logger.warning(f"Model {model_id} streaming test failed: {e}")
        
        return result
    
    def _categorize_error(self, error_msg: str) -> str:
        """Categorize error messages for better user feedback."""
        if "fine-tuning base model" in error_msg:
            return "fine-tuning base model"
        elif "404" in error_msg:
            return "model not found (404)"
        elif "400" in error_msg:
            return "bad request (400)"
        elif "not supported" in error_msg.lower():
            return "not supported"
        else:
            # Return first 50 chars of error
            return error_msg[:50] + "..." if len(error_msg) > 50 else error_msg
    
    def clear_cache(self, model_id: Optional[str] = None):
        """Clear cache for a specific model or all models."""
        if model_id:
            if model_id in self._cache:
                del self._cache[model_id]
                self._save_cache()
        else:
            self._cache = {}
            self._save_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        total_models = len(self._cache)
        working_models = sum(1 for m in self._cache.values() if m.get("tools_work"))
        partial_models = sum(1 for m in self._cache.values() 
                           if m.get("tools_work") and not m.get("streaming_tools"))
        
        return {
            "total_cached": total_models,
            "working": working_models,
            "partial_support": partial_models,
            "not_working": total_models - working_models,
            "cache_file": str(self.cache_file)
        }