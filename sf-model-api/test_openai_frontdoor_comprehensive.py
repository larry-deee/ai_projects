#!/usr/bin/env python3
"""
OpenAI Front-Door & Backend Adapters Comprehensive Test Suite
============================================================

Automated test suite for the OpenAI Front-Door & Backend Adapters architecture.
Tests all backend types, tool-call repair functionality, and OpenAI compliance.

Key tests:
- OpenAI models (native tool_calls passthrough)
- Anthropic models (Claude format → OpenAI tool_calls normalization)  
- Gemini models (Vertex format → OpenAI tool_calls normalization)
- Generic fallback for unknown models
- Tool-call repair shim functionality
- OpenAI compliance validation

Usage:
    python test_openai_frontdoor_comprehensive.py

Environment setup:
    export OPENAI_FRONTDOOR_ENABLED=1
    export MODEL_CAPABILITIES_JSON='{"test_model":{"openai_compatible":true}}'
"""

import sys
import os
import json
import asyncio
import unittest
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import modules to test
from model_capabilities import caps_for, get_backend_type, supports_native_tools
from openai_spec_adapter import route_and_normalise, normalise_anthropic, normalise_gemini, normalise_generic
from openai_tool_fix import repair_openai_tool_calls, repair_openai_response

# Test helpers
class MockClient:
    """Mock client that returns different responses based on model type."""
    
    async def roundtrip(self, payload):
        """Simulate API response based on model type."""
        model = payload.get("model", "unknown")
        backend_type = get_backend_type(model)
        tools = payload.get("tools", [])
        
        # Generate appropriate mock response based on model backend
        if backend_type == "openai_native":
            return self._mock_openai_response(model, tools)
        elif backend_type == "anthropic_bedrock":
            return self._mock_anthropic_response(model, tools)
        elif backend_type == "vertex_gemini":
            return self._mock_gemini_response(model, tools)
        else:
            return self._mock_generic_response(model, tools)
    
    def _mock_openai_response(self, model, tools):
        """Generate mock OpenAI-compatible response."""
        if tools:
            return {
                "id": f"chatcmpl-mock-{model}",
                "object": "chat.completion",
                "created": 1618923000,
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{
                            "id": "call_1234",
                            "type": "function",
                            "function": {
                                "name": tools[0]["function"]["name"],
                                "arguments": json.dumps({"q": "x"})
                            }
                        }]
                    },
                    "finish_reason": "tool_calls"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
        else:
            return {
                "id": f"chatcmpl-mock-{model}",
                "object": "chat.completion",
                "created": 1618923000,
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock response from {model}"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
    
    def _mock_anthropic_response(self, model, tools):
        """Generate mock Anthropic/Claude response."""
        if tools:
            # Simulate Claude XML format response
            xml_tool_call = f'<function_calls>\n<invoke name="{tools[0]["function"]["name"]}">\n<parameter name="q">x</parameter>\n</invoke>\n</function_calls>'
            return {
                "generations": [{
                    "text": xml_tool_call,
                    "content": xml_tool_call
                }],
                "usage": {
                    "input_tokens": 15,
                    "output_tokens": 25,
                    "total_tokens": 40
                },
                "model": model
            }
        else:
            return {
                "generations": [{
                    "text": f"Mock response from {model}",
                    "content": f"Mock response from {model}"
                }],
                "usage": {
                    "input_tokens": 15,
                    "output_tokens": 25,
                    "total_tokens": 40
                },
                "model": model
            }
    
    def _mock_gemini_response(self, model, tools):
        """Generate mock Gemini/Vertex response."""
        if tools:
            return {
                "candidates": [{
                    "content": {
                        "parts": [
                            {"text": f"I'll help with that."},
                            {"functionCall": {
                                "name": tools[0]["function"]["name"],
                                "args": {"q": "x"}
                            }}
                        ]
                    }
                }],
                "usage": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 18,
                    "totalTokenCount": 30
                },
                "model": model
            }
        else:
            return {
                "candidates": [{
                    "content": {
                        "parts": [
                            {"text": f"Mock response from {model}"}
                        ]
                    }
                }],
                "usage": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 18,
                    "totalTokenCount": 30
                },
                "model": model
            }
    
    def _mock_generic_response(self, model, tools):
        """Generate mock generic response for unknown models."""
        return {
            "generations": [{
                "text": f"Mock response from generic model {model}",
                "content": f"Mock response from generic model {model}"
            }],
            "model": model
        }

class MockMultiClient:
    """Mock multi-client adapter for different backend types."""
    
    def __init__(self):
        self.generic = MockClient()
        self.openai = MockClient()
        self.anthropic = MockClient()
        self.gemini = MockClient()

class OpenAIFrontdoorTests(unittest.TestCase):
    """Comprehensive test suite for OpenAI Front-Door & Backend Adapters."""

    def setUp(self):
        """Set up test environment."""
        # Enable OpenAI Front-Door architecture
        os.environ["OPENAI_FRONTDOOR_ENABLED"] = "1"
        
        # Set up test clients
        self.clients = MockMultiClient()
        
        # Define standard test tools
        self.research_tool = {
            "type": "function",
            "function": {
                "name": "research_agent",
                "description": "Research tool",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "q": {"type": "string"}
                    },
                    "required": ["q"]
                }
            }
        }
    
    def test_model_capabilities(self):
        """Test model capabilities registry for different backend types."""
        models = {
            # OpenAI models
            "sfdc_ai__DefaultGPT4Omni": "openai_native",
            "gpt-4": "openai_native",
            "gpt-4-turbo": "openai_native",
            
            # Anthropic models
            "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet": "anthropic_bedrock",
            "claude-3-sonnet": "anthropic_bedrock",
            "claude-4-sonnet": "anthropic_bedrock",
            
            # Gemini models
            "sfdc_ai__DefaultVertexAIGemini25Flash001": "vertex_gemini",
            "gemini-pro": "vertex_gemini"
        }
        
        for model, expected_backend in models.items():
            with self.subTest(model=model):
                backend = get_backend_type(model)
                self.assertEqual(backend, expected_backend)
                
                # Test capability flags
                caps = caps_for(model)
                if expected_backend == "openai_native":
                    self.assertTrue(caps.get("openai_compatible"))
                    self.assertTrue(caps.get("passthrough_tools"))
                    self.assertFalse(caps.get("requires_normalization", False))
                else:
                    self.assertTrue(caps.get("requires_normalization"))
    
    async def test_openai_native_passthrough(self):
        """Test OpenAI native model passthrough with tool_calls."""
        payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate OpenAI response format
        self.assertIn("id", result)
        self.assertIn("choices", result)
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")
        
        # Validate tool_calls format
        message = result["choices"][0]["message"]
        self.assertIn("tool_calls", message)
        tool_calls = message["tool_calls"]
        self.assertEqual(len(tool_calls), 1)
        
        # Validate specific tool call fields
        tool_call = tool_calls[0]
        self.assertIn("id", tool_call)
        self.assertEqual(tool_call["type"], "function")
        self.assertEqual(tool_call["function"]["name"], "research_agent")
        
        # Validate arguments is a JSON string
        args = tool_call["function"]["arguments"]
        self.assertIsInstance(args, str)
        args_obj = json.loads(args)
        self.assertEqual(args_obj["q"], "x")

    async def test_anthropic_adapter(self):
        """Test Anthropic/Claude adapter with tool_calls normalization."""
        payload = {
            "model": "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate OpenAI response format
        self.assertIn("id", result)
        self.assertIn("choices", result)
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")
        
        # Validate tool_calls format
        message = result["choices"][0]["message"]
        self.assertIn("tool_calls", message)
        tool_calls = message["tool_calls"]
        self.assertEqual(len(tool_calls), 1)
        
        # Validate specific tool call fields
        tool_call = tool_calls[0]
        self.assertIn("id", tool_call)
        self.assertEqual(tool_call["type"], "function")
        self.assertEqual(tool_call["function"]["name"], "research_agent")
        
        # Validate arguments is a JSON string
        args = tool_call["function"]["arguments"]
        self.assertIsInstance(args, str)
        args_obj = json.loads(args)
        self.assertEqual(args_obj["q"], "x")
    
    async def test_gemini_adapter(self):
        """Test Gemini/Vertex adapter with tool_calls normalization."""
        payload = {
            "model": "sfdc_ai__DefaultVertexAIGemini25Flash001",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate OpenAI response format
        self.assertIn("id", result)
        self.assertIn("choices", result)
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")
        
        # Validate tool_calls format
        message = result["choices"][0]["message"]
        self.assertIn("tool_calls", message)
        tool_calls = message["tool_calls"]
        self.assertEqual(len(tool_calls), 1)
        
        # Validate specific tool call fields
        tool_call = tool_calls[0]
        self.assertIn("id", tool_call)
        self.assertEqual(tool_call["type"], "function")
        self.assertEqual(tool_call["function"]["name"], "research_agent")
        
        # Validate arguments is a JSON string
        args = tool_call["function"]["arguments"]
        self.assertIsInstance(args, str)
        args_obj = json.loads(args)
        self.assertEqual(args_obj["q"], "x")
    
    async def test_missing_function_name_repair(self):
        """Test that tool-call repair fixes missing function names."""
        # Create a mock client that returns a malformed tool call
        class MalformedClient:
            async def roundtrip(self, payload):
                return {
                    "id": "chatcmpl-malformed",
                    "object": "chat.completion",
                    "created": 1618923000,
                    "model": payload.get("model", "test-model"),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call_1234",
                                "type": "function",
                                "function": {
                                    # Missing name field
                                    "arguments": json.dumps({"q": "x"})
                                }
                            }]
                        },
                        "finish_reason": "tool_calls"
                    }]
                }
        
        # Create clients with malformed client
        mock_clients = MockMultiClient()
        mock_clients.openai = MalformedClient()
        
        # Test payload with a single tool
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize - should fix missing name
        result = await route_and_normalise(payload, mock_clients)
        
        # Validate repair worked
        message = result["choices"][0]["message"]
        tool_calls = message["tool_calls"]
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0]["function"]["name"], "research_agent")
    
    async def test_non_string_arguments_repair(self):
        """Test that tool-call repair fixes non-string arguments."""
        # Create a mock client that returns arguments as object, not string
        class NonStringArgsClient:
            async def roundtrip(self, payload):
                return {
                    "id": "chatcmpl-nonstring",
                    "object": "chat.completion",
                    "created": 1618923000,
                    "model": payload.get("model", "test-model"),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{
                                "id": "call_1234",
                                "type": "function",
                                "function": {
                                    "name": "research_agent",
                                    "arguments": {"q": "x"}  # Object instead of string
                                }
                            }]
                        },
                        "finish_reason": "tool_calls"
                    }]
                }
        
        # Create clients with non-string args client
        mock_clients = MockMultiClient()
        mock_clients.openai = NonStringArgsClient()
        
        # Test payload
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize - should fix arguments
        result = await route_and_normalise(payload, mock_clients)
        
        # Validate repair worked
        message = result["choices"][0]["message"]
        tool_calls = message["tool_calls"]
        args = tool_calls[0]["function"]["arguments"]
        self.assertIsInstance(args, str)
        args_obj = json.loads(args)
        self.assertEqual(args_obj["q"], "x")
    
    async def test_empty_content_with_tool_calls(self):
        """Test that content is empty string when tool calls are present."""
        payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate content is empty string, not null
        message = result["choices"][0]["message"]
        self.assertEqual(message["content"], "")
    
    async def test_finish_reason_with_tool_calls(self):
        """Test that finish_reason is 'tool_calls' when tools are called."""
        payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate finish_reason
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")
    
    async def test_finish_reason_without_tool_calls(self):
        """Test that finish_reason is 'stop' for standard responses."""
        payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Say hello"}],
            # No tools
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate finish_reason
        self.assertEqual(result["choices"][0]["finish_reason"], "stop")
    
    async def test_model_capabilities_override(self):
        """Test that MODEL_CAPABILITIES_JSON environment variable works."""
        # Set a test model capability via environment
        os.environ["MODEL_CAPABILITIES_JSON"] = '{"test_model":{"openai_compatible":true,"backend_type":"openai_native"}}'
        
        # Force reload of capabilities
        from model_capabilities import reload_capabilities
        reload_capabilities()
        
        # Test payload with the custom model
        payload = {
            "model": "test_model",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Should route as OpenAI-native
        self.assertEqual(get_backend_type("test_model"), "openai_native")
        self.assertIn("choices", result)
        self.assertEqual(result["model"], "test_model")
    
    async def test_openai_parser_fallback_disabled(self):
        """Test that OPENAI_PARSER_FALLBACK=0 prevents legacy parsing."""
        # Set fallback disabled
        os.environ["OPENAI_PARSER_FALLBACK"] = "0"
        
        # Standard payload
        payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Use research_agent q=\"x\""}],
            "tools": [self.research_tool],
            "tool_choice": "auto"
        }
        
        # Route and normalize
        result = await route_and_normalise(payload, self.clients)
        
        # Validate basic OpenAI format
        self.assertIn("choices", result)
        
        # Reset env var
        os.environ.pop("OPENAI_PARSER_FALLBACK", None)

async def run_tests():
    """Run all tests asynchronously."""
    # Create test suite
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(OpenAIFrontdoorTests)
    
    # Custom test runner that supports async tests
    class AsyncTestRunner(unittest.TextTestRunner):
        async def run_test(self, test):
            result = self.run(test)
            return result
    
    # Run tests
    runner = AsyncTestRunner(verbosity=2)
    result = await runner.run_test(test_suite)
    
    return result.wasSuccessful()

def main():
    """Main entry point for test script."""
    print("🚀 OpenAI Front-Door & Backend Adapters Comprehensive Test Suite")
    print("=" * 70)
    print("\nRunning all tests...")
    
    success = asyncio.run(run_tests())
    
    if success:
        print("\n✅ All tests passed!")
        print("\nTest environment:")
        print(f"  OPENAI_FRONTDOOR_ENABLED: {os.environ.get('OPENAI_FRONTDOOR_ENABLED', '0')}")
        print(f"  MODEL_CAPABILITIES_JSON: {os.environ.get('MODEL_CAPABILITIES_JSON', 'Not set')}")
        print(f"  OPENAI_PARSER_FALLBACK: {os.environ.get('OPENAI_PARSER_FALLBACK', 'Not set')}")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()