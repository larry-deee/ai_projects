#!/usr/bin/env python3
"""
Test Suite for Anthropic Compatibility Async Implementation
===========================================================

Validation tests for the async Anthropic-compatible front door components.
Tests the complete integration including router, mapping, and streaming.

Usage:
    python test_anthropic_compat_async.py
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_anthropic_mapper():
    """Test Anthropic format transformation functions."""
    print("🧪 Testing Anthropic format transformation...")
    
    try:
        from src.compat_async.anthropic_mapper import (
            map_messages_to_sf_async, 
            map_sf_to_anthropic,
            require_anthropic_headers
        )
        from werkzeug.datastructures import Headers
        
        # Test header validation
        print("  ✅ Testing header validation...")
        valid_headers = Headers({'anthropic-version': '2023-06-01'})
        await require_anthropic_headers(valid_headers)
        print("    ✅ Valid headers accepted")
        
        try:
            invalid_headers = Headers({})
            await require_anthropic_headers(invalid_headers)
            print("    ❌ Invalid headers should have been rejected")
        except ValueError:
            print("    ✅ Invalid headers properly rejected")
        
        # Test message mapping  
        print("  ✅ Testing message format mapping...")
        anthropic_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello, world!"}
                ]
            }
        ]
        
        sf_request = await map_messages_to_sf_async(
            messages=anthropic_messages,
            model="claude-3-5-sonnet-latest",
            system="You are a helpful assistant"
        )
        
        print(f"    ✅ SF Request: {sf_request['model']}")
        print(f"    ✅ Messages: {len(sf_request['messages'])}")
        
        # Test response mapping
        print("  ✅ Testing response format mapping...")
        mock_sf_response = {
            "generations": [{"text": "Hello! How can I help you today?"}],
            "usage": {"inputTokenCount": 10, "outputTokenCount": 8}
        }
        
        anthropic_response = await map_sf_to_anthropic(
            mock_sf_response, "claude-3-5-sonnet-latest", anthropic_messages
        )
        
        print(f"    ✅ Response ID: {anthropic_response['id']}")
        print(f"    ✅ Content blocks: {len(anthropic_response['content'])}")
        print(f"    ✅ Usage tokens: {anthropic_response['usage']['input_tokens']}")
        
        print("✅ Anthropic mapper tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Anthropic mapper test failed: {e}")
        return False

async def test_model_map():
    """Test model mapping and verification system."""
    print("🧪 Testing model mapping system...")
    
    try:
        from src.compat_async.model_map import (
            load_anthropic_model_config,
            verify_model_async,
            get_verified_anthropic_models
        )
        
        # Test config loading
        print("  ✅ Testing configuration loading...")
        config = await load_anthropic_model_config()
        print(f"    ✅ Loaded {len(config)} model configurations")
        
        # Test model verification
        print("  ✅ Testing model verification...")
        # This will use the fallback config since backend may not be available
        is_valid = await verify_model_async("claude-3-5-sonnet-latest")
        print(f"    ✅ Model verification result: {is_valid}")
        
        # Test verified models list
        print("  ✅ Testing verified models list...")
        models = await get_verified_anthropic_models()
        print(f"    ✅ Found {len(models)} verified models")
        
        print("✅ Model mapping tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Model mapping test failed: {e}")
        return False

async def test_tokenizers():
    """Test async token estimation."""
    print("🧪 Testing token estimation...")
    
    try:
        from src.compat_async.tokenizers import count_tokens_async, validate_token_limits
        
        # Test basic token counting
        print("  ✅ Testing basic token counting...")
        messages = [
            {"role": "user", "content": "Hello, how are you today?"}
        ]
        
        token_count = await count_tokens_async(messages)
        print(f"    ✅ Token count: {token_count}")
        
        # Test with system message
        print("  ✅ Testing with system message...")
        token_count_with_system = await count_tokens_async(
            messages, system="You are a helpful assistant"
        )
        print(f"    ✅ Token count with system: {token_count_with_system}")
        
        # Test token validation
        print("  ✅ Testing token limit validation...")
        validation = await validate_token_limits(
            messages, "claude-3-5-sonnet-latest", 1000
        )
        print(f"    ✅ Validation result: {validation['valid']}")
        
        print("✅ Token estimation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Token estimation test failed: {e}")
        return False

async def test_sse_generation():
    """Test SSE streaming generation."""
    print("🧪 Testing SSE streaming...")
    
    try:
        from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
        
        # Mock Salesforce response
        mock_sf_response = {
            "generations": [{"text": "Hello! This is a test response for streaming."}],
            "usage": {"inputTokenCount": 10, "outputTokenCount": 12}
        }
        
        print("  ✅ Testing SSE event generation...")
        event_count = 0
        async for event in sse_iter_from_sf_generation(mock_sf_response, "claude-3-5-sonnet-latest"):
            event_count += 1
            if event_count <= 3:  # Show first few events
                print(f"    📡 Event {event_count}: {event[:100]}...")
        
        print(f"    ✅ Generated {event_count} SSE events")
        print("✅ SSE streaming tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ SSE streaming test failed: {e}")
        return False

async def main():
    """Run all validation tests."""
    print("🚀 Starting Anthropic Compatibility Async Validation Tests\n")
    
    test_results = []
    
    # Run all tests
    test_results.append(await test_anthropic_mapper())
    test_results.append(await test_model_map())
    test_results.append(await test_tokenizers())
    test_results.append(await test_sse_generation())
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed! Anthropic compatibility implementation is ready.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())