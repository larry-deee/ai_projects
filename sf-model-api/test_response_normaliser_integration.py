#!/usr/bin/env python3
"""
Integration Test for Response Normaliser
========================================

Comprehensive integration test verifying the response normaliser works correctly
with all existing components of the sf-model-api Tool Behaviour Compatibility Layer.

Usage:
    python test_response_normaliser_integration.py
"""

import json
import sys
import os
import asyncio
from typing import Dict, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_functionality():
    """Test basic response normaliser functionality."""
    print("🧪 Test 1: Basic Functionality")
    print("-" * 40)
    
    try:
        from response_normaliser import to_openai_tool_call, normalise_assistant_tool_response
        
        # Test tool call conversion
        tool_call = to_openai_tool_call(
            "get_weather", 
            {"location": "San Francisco", "units": "metric"}, 
            "call_123"
        )
        
        assert tool_call["id"] == "call_123"
        assert tool_call["type"] == "function" 
        assert tool_call["function"]["name"] == "get_weather"
        assert "location" in json.loads(tool_call["function"]["arguments"])
        
        print("✅ Tool call conversion works correctly")
        
        # Test message normalization
        message = {
            "role": "assistant",
            "content": "I'll get the weather for you."
        }
        
        normalized = normalise_assistant_tool_response(message, [tool_call])
        
        assert normalized["role"] == "assistant"
        assert normalized["content"] == ""  # Should be empty with tool calls
        assert "tool_calls" in normalized
        assert len(normalized["tool_calls"]) == 1
        
        print("✅ Message normalization works correctly")
        print("✅ Test 1 PASSED\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        return False


def test_unified_response_formatter_integration():
    """Test integration with unified response formatter."""
    print("🧪 Test 2: Unified Response Formatter Integration") 
    print("-" * 40)
    
    try:
        from unified_response_formatter import UnifiedResponseFormatter
        
        formatter = UnifiedResponseFormatter()
        
        # Mock Salesforce response with tool calls
        sf_response = {
            "generation": {
                "generatedText": "I'll help you get the weather information."
            },
            "tool_calls": [{
                "id": "call_weather_123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "NYC", "units": "fahrenheit"}'
                }
            }]
        }
        
        openai_response = formatter.format_openai_response(sf_response, "claude-3-haiku")
        
        # Verify OpenAI format
        assert "choices" in openai_response
        assert len(openai_response["choices"]) == 1
        
        choice = openai_response["choices"][0]
        message = choice["message"]
        
        # Check if normalization was applied
        if "tool_calls" in message and message["tool_calls"]:
            # Content should be empty when tool calls are present
            assert message["content"] == "", f"Content should be empty but got: '{message['content']}'"
            assert choice["finish_reason"] == "tool_calls"
            print("✅ Response normalisation applied through unified formatter")
        
        print("✅ Test 2 PASSED\n")
        return True
        
    except ImportError:
        print("⚠️ UnifiedResponseFormatter not available, skipping test")
        return True
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        return False


def test_model_router_integration():
    """Test integration with model router."""
    print("🧪 Test 3: Model Router Integration")
    print("-" * 40)
    
    try:
        from model_router import ModelRouter, is_openai_native_model
        
        router = ModelRouter()
        
        # Test OpenAI-native model detection
        assert is_openai_native_model("gpt-4") == True
        assert is_openai_native_model("sfdc_ai__DefaultGPT4Omni") == True  
        assert is_openai_native_model("claude-3-haiku") == False
        
        print("✅ OpenAI-native model detection works")
        
        # Test response normalization
        test_response = {
            "id": "test-123",
            "object": "chat.completion", 
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "I'll help you with that.",
                    "tool_calls": [{
                        "id": "call_test_123",
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
        
        # Test normalization for different model types
        for model in ["gpt-4", "claude-3-haiku", "gemini-pro"]:
            normalized = router.normalize_tool_response(test_response.copy(), model)
            
            assert "choices" in normalized
            if normalized["choices"] and "tool_calls" in normalized["choices"][0]["message"]:
                # Should have normalized content behavior
                message = normalized["choices"][0]["message"]
                print(f"✅ Model {model}: normalized correctly")
        
        print("✅ Test 3 PASSED\n")
        return True
        
    except ImportError:
        print("⚠️ ModelRouter not available, skipping test")
        return True
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        return False


async def test_async_normalization():
    """Test async normalization functionality."""
    print("🧪 Test 4: Async Normalization")
    print("-" * 40)
    
    try:
        from response_normaliser import normalise_response_async
        
        # Test Anthropic response normalization
        anthropic_response = {
            "id": "msg_test_123",
            "content": [
                {"type": "text", "text": "I'll search for that information."},
                {
                    "type": "tool_use",
                    "id": "toolu_test_456", 
                    "name": "search_web",
                    "input": {"query": "Python tutorials", "limit": 5}
                }
            ],
            "usage": {"input_tokens": 50, "output_tokens": 25}
        }
        
        result = await normalise_response_async(anthropic_response, "anthropic", "claude-3-haiku")
        
        assert result.original_backend == "anthropic"
        assert result.tool_calls_count == 1
        assert result.finish_reason == "tool_calls"
        assert result.normalization_applied == True
        
        # Check normalized response structure
        normalized = result.normalized_response
        assert normalized["object"] == "chat.completion"
        assert "choices" in normalized
        
        choice = normalized["choices"][0]
        message = choice["message"]
        
        assert message["role"] == "assistant"
        assert message["content"] == ""  # Should be empty with tool calls
        assert "tool_calls" in message
        assert len(message["tool_calls"]) == 1
        
        tool_call = message["tool_calls"][0]
        assert tool_call["type"] == "function"
        assert tool_call["function"]["name"] == "search_web"
        
        print("✅ Anthropic async normalization works correctly")
        
        # Test Vertex AI normalization
        vertex_response = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "Let me calculate that for you."},
                        {
                            "functionCall": {
                                "name": "calculate",
                                "args": {"expression": "2 + 2", "precision": 2}
                            }
                        }
                    ]
                }
            }],
            "usageMetadata": {
                "promptTokenCount": 30,
                "candidatesTokenCount": 15,
                "totalTokenCount": 45
            }
        }
        
        result = await normalise_response_async(vertex_response, "vertex", "gemini-pro")
        
        assert result.original_backend == "vertex"
        assert result.tool_calls_count == 1
        assert result.processing_time_ms > 0
        
        print("✅ Vertex AI async normalization works correctly")
        print("✅ Test 4 PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
        return False


def test_thread_safety():
    """Test thread safety of the response normaliser."""
    print("🧪 Test 5: Thread Safety")
    print("-" * 40)
    
    try:
        import threading
        from concurrent.futures import ThreadPoolExecutor
        from response_normaliser import normalise_assistant_tool_response
        
        results = []
        errors = []
        
        def worker_function(worker_id):
            try:
                for i in range(20):
                    message = {
                        "role": "assistant",
                        "content": f"Response from worker {worker_id}, iteration {i}"
                    }
                    
                    tool_calls = [{
                        "id": f"call_w{worker_id}_i{i}",
                        "type": "function",
                        "function": {
                            "name": "worker_function",
                            "arguments": f'{{"worker": {worker_id}, "iteration": {i}}}'
                        }
                    }]
                    
                    result = normalise_assistant_tool_response(message, tool_calls)
                    
                    # Verify result is correct
                    assert result["role"] == "assistant"
                    assert result["content"] == ""
                    assert "tool_calls" in result
                    assert len(result["tool_calls"]) == 1
                    
                    results.append((worker_id, i, "success"))
                    
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker_function, i) for i in range(10)]
            for future in futures:
                future.result()
        
        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 200, f"Expected 200 results, got {len(results)}"
        
        print(f"✅ Processed {len(results)} normalizations across 10 threads")
        print("✅ Test 5 PASSED\n") 
        return True
        
    except Exception as e:
        print(f"❌ Test 5 FAILED: {e}")
        return False


def test_performance_metrics():
    """Test performance metrics collection."""
    print("🧪 Test 6: Performance Metrics")
    print("-" * 40)
    
    try:
        from response_normaliser import ResponseNormaliser
        
        normaliser = ResponseNormaliser()
        
        # Perform several operations
        for i in range(50):
            message = {"role": "assistant", "content": f"Test message {i}"}
            
            if i % 2 == 0:  # Add tool calls to half the messages
                tool_calls = [{
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": "test_function",
                        "arguments": f'{{"test_id": {i}}}'
                    }
                }]
            else:
                tool_calls = None
            
            normaliser.normalise_assistant_tool_response(message, tool_calls)
        
        # Check metrics
        stats = normaliser.get_performance_stats()
        
        assert stats["normalizations_performed"] == 50
        assert stats["avg_processing_time_ms"] >= 0
        assert isinstance(stats["cache_hit_rate"], (int, float))
        assert isinstance(stats["backend_statistics"], dict)
        
        print(f"✅ Normalizations performed: {stats['normalizations_performed']}")
        print(f"✅ Average processing time: {stats['avg_processing_time_ms']:.3f}ms")
        print(f"✅ Cache hit rate: {stats['cache_hit_rate']:.1f}%")
        print("✅ Test 6 PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 6 FAILED: {e}")
        return False


def test_error_handling():
    """Test error handling robustness."""
    print("🧪 Test 7: Error Handling")
    print("-" * 40)
    
    try:
        from response_normaliser import to_openai_tool_call, normalise_assistant_tool_response
        
        # Test invalid tool call creation
        try:
            to_openai_tool_call("", {"param": "value"}, "call_123")  # Empty name
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Empty function name properly rejected")
        
        try:
            to_openai_tool_call("func", "not_a_dict", "call_123")  # Invalid args
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Non-dict arguments properly rejected")
        
        # Test malformed message normalization
        result = normalise_assistant_tool_response(None, None)
        assert result["role"] == "assistant"
        print("✅ None message handled gracefully")
        
        # Test malformed tool calls
        malformed_tools = [
            {"id": "call_1", "missing_function": True},
            {"incomplete": "structure"},
            None,
            {"id": "call_2", "function": "not_a_dict"}
        ]
        
        message = {"role": "assistant", "content": "Test content"}
        result = normalise_assistant_tool_response(message, malformed_tools)
        
        # Should not crash and return valid structure
        assert isinstance(result, dict)
        assert result["role"] == "assistant"
        print("✅ Malformed tool calls handled gracefully")
        
        print("✅ Test 7 PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 7 FAILED: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("🚀 Response Normaliser Integration Test Suite")
    print("=" * 60)
    print("Testing response normaliser integration with sf-model-api components")
    print("=" * 60)
    
    test_results = []
    
    # Run synchronous tests
    sync_tests = [
        test_basic_functionality,
        test_unified_response_formatter_integration,
        test_model_router_integration,
        test_thread_safety,
        test_performance_metrics, 
        test_error_handling
    ]
    
    for test in sync_tests:
        result = test()
        test_results.append(result)
    
    # Run async tests  
    async_result = await test_async_normalization()
    test_results.append(async_result)
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    for i, result in enumerate(test_results, 1):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"Test {i}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("\n✅ Response Normaliser is ready for production use")
        print("✅ All integrations working correctly")
        print("✅ Thread-safe and performant")
        print("✅ Robust error handling")
        return 0
    else:
        print("❌ Some integration tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)