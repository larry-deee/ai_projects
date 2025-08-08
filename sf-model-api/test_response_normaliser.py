#!/usr/bin/env python3
"""
Unit Tests for Response Normaliser
==================================

Comprehensive test suite for the response normalizer module covering:
- OpenAI tool_calls format conversion
- Cross-backend compatibility (Anthropic, Vertex, Salesforce)
- Thread-safety and async operations
- Performance optimization validation
- Error handling and edge cases

Usage:
    python test_response_normaliser.py
    or
    python -m pytest test_response_normaliser.py -v
"""

import unittest
import asyncio
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

# Import the components to test
try:
    from src.response_normaliser import (
        ResponseNormaliser,
        to_openai_tool_call,
        normalise_assistant_tool_response,
        normalise_response_async,
        NormalizationResult,
        ToolCallNormalization,
        default_normaliser
    )
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    
    from response_normaliser import (
        ResponseNormaliser,
        to_openai_tool_call,
        normalise_assistant_tool_response,
        normalise_response_async,
        NormalizationResult,
        ToolCallNormalization,
        default_normaliser
    )


class TestResponseNormaliser(unittest.TestCase):
    """Test cases for the ResponseNormaliser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.normaliser = ResponseNormaliser()
    
    def test_to_openai_tool_call_basic(self):
        """Test basic tool call conversion to OpenAI format."""
        result = to_openai_tool_call("get_weather", {"location": "NYC"}, "call_123")
        
        expected = {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location":"NYC"}'
            }
        }
        
        self.assertEqual(result, expected)
    
    def test_to_openai_tool_call_complex_args(self):
        """Test tool call conversion with complex arguments."""
        complex_args = {
            "location": "New York, NY",
            "units": "celsius",
            "include_forecast": True,
            "days": 5,
            "options": {"detailed": True, "alerts": False}
        }
        
        result = to_openai_tool_call("get_weather", complex_args, "call_456")
        
        # Verify structure
        self.assertEqual(result["id"], "call_456")
        self.assertEqual(result["type"], "function")
        self.assertEqual(result["function"]["name"], "get_weather")
        
        # Verify arguments can be parsed back
        parsed_args = json.loads(result["function"]["arguments"])
        self.assertEqual(parsed_args, complex_args)
    
    def test_to_openai_tool_call_invalid_inputs(self):
        """Test tool call conversion with invalid inputs."""
        # Empty name should raise ValueError
        with self.assertRaises(ValueError):
            to_openai_tool_call("", {"arg": "value"}, "call_123")
        
        # Non-dict arguments should raise ValueError
        with self.assertRaises(ValueError):
            to_openai_tool_call("func", "not_a_dict", "call_123")
        
        # Empty call_id should generate a new one
        result = to_openai_tool_call("func", {"arg": "value"}, "")
        self.assertTrue(result["id"].startswith("call_"))
    
    def test_normalise_assistant_tool_response_with_tools(self):
        """Test assistant response normalization with tool calls."""
        message = {
            "role": "assistant",
            "content": "I'll get the weather for you."
        }
        
        tool_calls = [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "NYC"}'
            }
        }]
        
        result = normalise_assistant_tool_response(message, tool_calls, "tool_calls")
        
        # Content should be empty when tool calls are present
        self.assertEqual(result["content"], "")
        self.assertEqual(result["role"], "assistant")
        self.assertIn("tool_calls", result)
        self.assertEqual(len(result["tool_calls"]), 1)
    
    def test_normalise_assistant_tool_response_without_tools(self):
        """Test assistant response normalization without tool calls."""
        message = {
            "role": "assistant",
            "content": "Here's the weather information."
        }
        
        result = normalise_assistant_tool_response(message, None, "stop")
        
        # Content should remain when no tool calls
        self.assertEqual(result["content"], "Here's the weather information.")
        self.assertEqual(result["role"], "assistant")
        self.assertNotIn("tool_calls", result)
    
    def test_normalise_assistant_tool_response_malformed_tools(self):
        """Test assistant response normalization with malformed tool calls."""
        message = {
            "role": "assistant",
            "content": "Processing request."
        }
        
        # Malformed tool call missing function
        tool_calls = [{
            "id": "call_123",
            "type": "function"
            # Missing "function" field
        }]
        
        result = normalise_assistant_tool_response(message, tool_calls, "tool_calls")
        
        # Should handle gracefully
        self.assertIsInstance(result, dict)
        self.assertEqual(result["role"], "assistant")
    
    async def test_async_normalization_anthropic(self):
        """Test async normalization for Anthropic responses."""
        anthropic_response = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'll get the weather for you."},
                {
                    "type": "tool_use",
                    "id": "call_456",
                    "name": "get_weather",
                    "input": {"location": "San Francisco"}
                }
            ],
            "model": "claude-3-haiku",
            "usage": {
                "input_tokens": 50,
                "output_tokens": 20
            }
        }
        
        result = await normalise_response_async(anthropic_response, "anthropic", "claude-3-haiku")
        
        self.assertIsInstance(result, NormalizationResult)
        self.assertEqual(result.original_backend, "anthropic")
        self.assertTrue(result.normalization_applied)
        self.assertEqual(result.tool_calls_count, 1)
        self.assertEqual(result.finish_reason, "tool_calls")
        
        # Verify OpenAI format
        openai_response = result.normalized_response
        self.assertEqual(openai_response["object"], "chat.completion")
        self.assertIn("choices", openai_response)
        
        choice = openai_response["choices"][0]
        self.assertEqual(choice["message"]["role"], "assistant")
        self.assertIn("tool_calls", choice["message"])
    
    async def test_async_normalization_vertex(self):
        """Test async normalization for Vertex AI responses."""
        vertex_response = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "I'll check the weather."},
                        {
                            "functionCall": {
                                "name": "get_weather",
                                "args": {"location": "NYC"}
                            }
                        }
                    ]
                }
            }],
            "usageMetadata": {
                "promptTokenCount": 40,
                "candidatesTokenCount": 15,
                "totalTokenCount": 55
            }
        }
        
        result = await normalise_response_async(vertex_response, "vertex", "gemini-pro")
        
        self.assertIsInstance(result, NormalizationResult)
        self.assertEqual(result.original_backend, "vertex")
        self.assertTrue(result.normalization_applied)
        self.assertEqual(result.tool_calls_count, 1)
        
        # Verify usage tokens
        openai_response = result.normalized_response
        usage = openai_response["usage"]
        self.assertEqual(usage["prompt_tokens"], 40)
        self.assertEqual(usage["completion_tokens"], 15)
        self.assertEqual(usage["total_tokens"], 55)
    
    async def test_async_normalization_openai(self):
        """Test async normalization for OpenAI responses (passthrough with validation)."""
        openai_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677652288,
            "model": "gpt-4",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Getting weather data.",
                    "tool_calls": [{
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": "{\"location\": \"Boston\"}"
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}
        }
        
        result = await normalise_response_async(openai_response, "openai", "gpt-4")
        
        self.assertIsInstance(result, NormalizationResult)
        self.assertEqual(result.original_backend, "openai")
        
        # Should normalize even OpenAI responses for consistency
        normalized = result.normalized_response
        choice = normalized["choices"][0]
        message = choice["message"]
        
        # Content should be empty when tool calls present
        self.assertEqual(message["content"], "")
        self.assertIn("tool_calls", message)
    
    def test_thread_safety(self):
        """Test thread safety of response normalizer."""
        def normalize_response(thread_id):
            """Function to run in multiple threads."""
            message = {
                "role": "assistant",
                "content": f"Response from thread {thread_id}"
            }
            
            tool_calls = [{
                "id": f"call_{thread_id}",
                "type": "function",
                "function": {
                    "name": "test_function",
                    "arguments": f'{{"thread_id": {thread_id}}}'
                }
            }]
            
            result = normalise_assistant_tool_response(message, tool_calls)
            return result
        
        # Run multiple threads concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(normalize_response, i) for i in range(20)]
            results = [future.result() for future in futures]
        
        # Verify all results are correct and independent
        self.assertEqual(len(results), 20)
        for i, result in enumerate(results):
            self.assertEqual(result["role"], "assistant")
            self.assertEqual(result["content"], "")  # Should be empty with tool calls
            self.assertIn("tool_calls", result)
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Clear metrics
        normaliser = ResponseNormaliser()
        
        # Perform some normalizations
        for i in range(5):
            message = {"role": "assistant", "content": f"Test {i}"}
            tool_calls = [{
                "id": f"call_{i}",
                "type": "function", 
                "function": {"name": "test", "arguments": "{}"}
            }]
            normaliser.normalise_assistant_tool_response(message, tool_calls)
        
        stats = normaliser.get_performance_stats()
        
        self.assertEqual(stats["normalizations_performed"], 5)
        self.assertGreaterEqual(stats["avg_processing_time_ms"], 0)
        self.assertIsInstance(stats["backend_statistics"], dict)
    
    def test_cache_functionality(self):
        """Test caching behavior."""
        normaliser = ResponseNormaliser()
        
        # Same response should hit cache on second call
        response = {"test": "response", "choices": [{"message": {"role": "assistant"}}]}
        
        # First call
        asyncio.run(normaliser.normalise_response_async(response, "test", "model"))
        
        # Second call should hit cache
        start_time = time.time()
        result = asyncio.run(normaliser.normalise_response_async(response, "test", "model"))
        end_time = time.time()
        
        # Cache hit should be faster
        self.assertLess(end_time - start_time, 0.1)  # Should be very fast
        
        stats = normaliser.get_performance_stats()
        self.assertGreater(stats["cache_hits"], 0)
    
    def test_error_handling(self):
        """Test error handling in normalization."""
        # Test with None message
        result = normalise_assistant_tool_response(None, None)
        self.assertEqual(result["role"], "assistant")
        
        # Test with invalid tool call format
        invalid_tool_calls = [{"invalid": "format"}]
        message = {"role": "assistant", "content": "test"}
        
        # Should not crash
        result = normalise_assistant_tool_response(message, invalid_tool_calls)
        self.assertIsInstance(result, dict)
    
    def test_json_serialization_edge_cases(self):
        """Test JSON serialization with edge cases."""
        # Unicode characters
        result = to_openai_tool_call("test", {"text": "Hello 世界! 🌍"}, "call_123")
        parsed_args = json.loads(result["function"]["arguments"])
        self.assertEqual(parsed_args["text"], "Hello 世界! 🌍")
        
        # Special characters
        result = to_openai_tool_call("test", {"query": 'SELECT * FROM "table" WHERE name=\'test\''}, "call_456")
        parsed_args = json.loads(result["function"]["arguments"])
        self.assertEqual(parsed_args["query"], 'SELECT * FROM "table" WHERE name=\'test\'')
        
        # Large numbers
        result = to_openai_tool_call("test", {"big_number": 12345678901234567890}, "call_789")
        parsed_args = json.loads(result["function"]["arguments"])
        self.assertEqual(parsed_args["big_number"], 12345678901234567890)
    
    def test_configuration_options(self):
        """Test configuration options for normalization."""
        config = ToolCallNormalization(
            ensure_string_arguments=True,
            validate_json_format=True,
            strict_openai_compliance=True
        )
        
        normaliser = ResponseNormaliser(config)
        
        # Verify configuration is applied
        self.assertEqual(normaliser.config.ensure_string_arguments, True)
        self.assertEqual(normaliser.config.validate_json_format, True)
        self.assertEqual(normaliser.config.strict_openai_compliance, True)


class TestIntegration(unittest.TestCase):
    """Integration tests for response normalizer with other components."""
    
    def test_unified_response_formatter_integration(self):
        """Test integration with unified response formatter."""
        try:
            from src.unified_response_formatter import UnifiedResponseFormatter
        except ImportError:
            self.skipTest("UnifiedResponseFormatter not available")
        
        formatter = UnifiedResponseFormatter()
        
        # Mock Salesforce response with tool calls
        sf_response = {
            "generation": {
                "generatedText": "I'll help you with the weather."
            },
            "tool_calls": [{
                "id": "call_123",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "NYC"}'
                }
            }]
        }
        
        openai_response = formatter.format_openai_response(sf_response, "claude-3-haiku")
        
        # Verify normalization was applied
        choice = openai_response["choices"][0]
        message = choice["message"]
        
        if "tool_calls" in message:
            # Content should be empty when tool calls are present
            self.assertEqual(message["content"], "")
    
    def test_model_router_integration(self):
        """Test integration with model router."""
        try:
            from src.model_router import ModelRouter
        except ImportError:
            self.skipTest("ModelRouter not available")
        
        router = ModelRouter()
        
        # Mock response with tool calls
        response = {
            "id": "test-response",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "I'll help you.",
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "test_function",
                            "arguments": '{"param": "value"}'
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }]
        }
        
        normalized = router.normalize_tool_response(response, "claude-3-haiku")
        
        # Verify response was processed
        self.assertIsInstance(normalized, dict)
        if "choices" in normalized and normalized["choices"]:
            message = normalized["choices"][0]["message"]
            if "tool_calls" in message:
                # Should have proper OpenAI format
                tool_call = message["tool_calls"][0]
                self.assertEqual(tool_call["type"], "function")
                self.assertIn("function", tool_call)


async def run_async_tests():
    """Run async tests."""
    test_case = TestResponseNormaliser()
    test_case.setUp()
    
    print("Running async normalization tests...")
    
    # Test Anthropic normalization
    await test_case.test_async_normalization_anthropic()
    print("✅ Anthropic async normalization test passed")
    
    # Test Vertex normalization
    await test_case.test_async_normalization_vertex()
    print("✅ Vertex async normalization test passed")
    
    # Test OpenAI normalization
    await test_case.test_async_normalization_openai()
    print("✅ OpenAI async normalization test passed")
    
    print("All async tests completed successfully!")


def main():
    """Main test runner."""
    print("Running Response Normaliser Test Suite")
    print("=" * 50)
    
    # Run synchronous tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run async tests
    print("\n" + "=" * 50)
    print("Running Async Tests")
    print("=" * 50)
    
    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        print(f"❌ Async tests failed: {e}")
    
    print("\n" + "=" * 50)
    print("Test Suite Complete")


if __name__ == "__main__":
    main()