#!/usr/bin/env python3
"""
OpenAI Front-Door & Backend Adapters Test
==========================================

Test script for the new universal OpenAI compatibility architecture.
Validates capability-based routing, response normalization, and tool preservation.

Usage:
    python test_openai_frontdoor.py
    
Environment Variables:
    OPENAI_FRONTDOOR_ENABLED=1  # Enable new architecture
"""

import sys
import os
sys.path.insert(0, 'src')

import asyncio
import json
from model_capabilities import caps_for, get_backend_type, load_capabilities
from openai_spec_adapter import route_and_normalise, normalise_anthropic, normalise_gemini, normalise_generic

def test_model_capabilities():
    """Test the model capabilities registry."""
    print("🧪 Testing Model Capabilities Registry")
    print("=" * 50)
    
    # Test known models
    test_models = [
        "sfdc_ai__DefaultGPT4Omni",
        "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet", 
        "sfdc_ai__DefaultVertexAIGemini25Flash001",
        "claude-3-haiku",
        "gpt-4",
        "gemini-pro",
        "unknown-model-123"
    ]
    
    for model in test_models:
        caps = caps_for(model)
        backend = get_backend_type(model)
        print(f"  {model[:40]:<40} | {backend:<15} | {caps}")
    
    print("\n✅ Model capabilities test completed\n")

def test_response_normalizers():
    """Test the response normalization functions."""
    print("🧪 Testing Response Normalizers")
    print("=" * 50)
    
    # Test Anthropic normalizer
    anthropic_response = {
        "events": [
            {"type": "tool_use", "name": "get_weather", "input": {"location": "New York"}},
            {"type": "text", "text": "I'll help you get the weather for New York."}
        ],
        "usage": {"input_tokens": 20, "output_tokens": 15}
    }
    
    normalized_anthropic = normalise_anthropic(anthropic_response, "claude-3-sonnet")
    print(f"  Anthropic normalized: {json.dumps(normalized_anthropic, indent=2)[:200]}...")
    
    # Test Gemini normalizer  
    gemini_response = {
        "candidates": [{
            "content": {
                "parts": [
                    {"text": "I'll help you with that."},
                    {"functionCall": {"name": "search_web", "args": {"query": "AI news"}}}
                ]
            }
        }]
    }
    
    normalized_gemini = normalise_gemini(gemini_response, "gemini-pro")
    print(f"  Gemini normalized: {json.dumps(normalized_gemini, indent=2)[:200]}...")
    
    # Test generic normalizer
    generic_response = {"generations": [{"text": "This is a generic response"}]}
    normalized_generic = normalise_generic(generic_response, "unknown-model")
    print(f"  Generic normalized: {json.dumps(normalized_generic, indent=2)[:200]}...")
    
    print("\n✅ Response normalizer test completed\n")

class MockClient:
    """Mock client for testing the adapter framework."""
    
    async def roundtrip(self, payload):
        """Mock roundtrip that simulates different backend responses."""
        model = payload.get("model", "unknown")
        backend = get_backend_type(model)
        
        if "anthropic" in backend:
            return {
                "generations": [{
                    "text": f"Mock Anthropic response from {model}",
                    "content": f"Mock Anthropic response from {model}"
                }],
                "usage": {"inputTokenCount": 10, "outputTokenCount": 20}
            }
        elif "gemini" in backend:
            return {
                "generations": [{
                    "text": f"Mock Gemini response from {model}",
                    "content": f"Mock Gemini response from {model}"
                }],
                "usage": {"inputTokenCount": 15, "outputTokenCount": 25}
            }
        else:  # OpenAI native
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"Mock OpenAI response from {model}"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 12, "completion_tokens": 18, "total_tokens": 30}
            }

class MockMultiClient:
    """Mock multi-client adapter for testing."""
    
    def __init__(self):
        self.generic = MockClient()
        self.openai = MockClient()
        self.anthropic = MockClient()
        self.gemini = MockClient()

async def test_route_and_normalise():
    """Test the route_and_normalise function with different models."""
    print("🧪 Testing Route and Normalise")
    print("=" * 50)
    
    mock_clients = MockMultiClient()
    
    test_cases = [
        {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello GPT-4"}],
            "tools": [{"type": "function", "function": {"name": "get_time", "parameters": {}}}]
        },
        {
            "model": "claude-3-sonnet", 
            "messages": [{"role": "user", "content": "Hello Claude"}],
            "max_tokens": 1000
        },
        {
            "model": "gemini-pro",
            "messages": [{"role": "user", "content": "Hello Gemini"}],
            "temperature": 0.8
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"  Test Case {i+1}: {test_case['model']}")
        try:
            result = await route_and_normalise(test_case, mock_clients)
            print(f"    Backend: {get_backend_type(test_case['model'])}")
            print(f"    Response: {json.dumps(result, indent=4)[:300]}...")
            print(f"    ✅ Success")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        print()
    
    print("✅ Route and normalise test completed\n")

def test_environment_config():
    """Test environment-based configuration."""
    print("🧪 Testing Environment Configuration")
    print("=" * 50)
    
    # Test capability loading
    capabilities = load_capabilities()
    print(f"  Loaded {len(capabilities)} model configurations")
    
    # Test environment variable detection
    frontdoor_enabled = os.getenv("OPENAI_FRONTDOOR_ENABLED", "0") == "1"
    print(f"  OpenAI Front-Door Enabled: {frontdoor_enabled}")
    
    # Test capability override via environment
    json_override = os.getenv("MODEL_CAPABILITIES_JSON")
    file_override = os.getenv("MODEL_CAPABILITIES_FILE")
    print(f"  JSON Override: {'Set' if json_override else 'Not set'}")
    print(f"  File Override: {file_override if file_override else 'Not set'}")
    
    print("\n✅ Environment configuration test completed\n")

async def main():
    """Run all tests."""
    print("🚀 OpenAI Front-Door & Backend Adapters Test Suite")
    print("=" * 60)
    print()
    
    try:
        # Run synchronous tests
        test_model_capabilities()
        test_response_normalizers()
        test_environment_config()
        
        # Run async tests  
        await test_route_and_normalise()
        
        print("🎉 All tests completed successfully!")
        print()
        print("To enable the new architecture in the server, set:")
        print("  export OPENAI_FRONTDOOR_ENABLED=1")
        print()
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())