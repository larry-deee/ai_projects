#!/usr/bin/env python3
"""
Response Normaliser Demo
========================

Demonstration script showing the response normalizer in action across different backends.
Shows how the normalizer ensures consistent OpenAI-compatible tool_calls format.

Usage:
    python demo_response_normaliser.py
"""

import json
import asyncio
from typing import Dict, Any

try:
    from src.response_normaliser import (
        ResponseNormaliser,
        to_openai_tool_call,
        normalise_assistant_tool_response,
        normalise_response_async
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    from response_normaliser import (
        ResponseNormaliser,
        to_openai_tool_call,
        normalise_assistant_tool_response,
        normalise_response_async
    )


def print_json(data: Dict[str, Any], title: str):
    """Pretty print JSON data with title."""
    print(f"\n{title}")
    print("-" * len(title))
    print(json.dumps(data, indent=2, ensure_ascii=False))


def demo_basic_tool_call_conversion():
    """Demonstrate basic tool call conversion to OpenAI format."""
    print("🔧 DEMO 1: Basic Tool Call Conversion")
    print("=" * 50)
    
    # Example: Weather function call
    weather_call = to_openai_tool_call(
        name="get_current_weather",
        args_obj={
            "location": "San Francisco, CA",
            "unit": "celsius",
            "include_forecast": True
        },
        call_id="call_weather_123"
    )
    
    print_json(weather_call, "Weather Tool Call (OpenAI Format)")
    
    # Example: Complex calculation function
    calc_call = to_openai_tool_call(
        name="calculate_mortgage",
        args_obj={
            "principal": 500000,
            "interest_rate": 3.5,
            "term_years": 30,
            "down_payment": 100000,
            "property_tax": 12000,
            "insurance": 2400,
            "pmi_required": True
        },
        call_id="call_calc_456"
    )
    
    print_json(calc_call, "Mortgage Calculator Tool Call (OpenAI Format)")
    
    # Example: Text processing with special characters
    text_call = to_openai_tool_call(
        name="translate_text",
        args_obj={
            "text": "Hello, world! 🌍 How are you today? 你好世界！",
            "source_language": "auto-detect",
            "target_language": "es",
            "preserve_formatting": True
        },
        call_id="call_translate_789"
    )
    
    print_json(text_call, "Translation Tool Call (OpenAI Format)")


def demo_assistant_response_normalization():
    """Demonstrate assistant response normalization."""
    print("\n\n🤖 DEMO 2: Assistant Response Normalization")
    print("=" * 50)
    
    # Example 1: Response with tool calls
    print("\n📋 Example 1: Response WITH tool calls")
    
    message_with_tools = {
        "role": "assistant",
        "content": "I'll help you get the current weather information for San Francisco."
    }
    
    tool_calls = [
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "San Francisco", "units": "metric"}'
            }
        }
    ]
    
    print_json(message_with_tools, "BEFORE normalization:")
    
    normalized_with_tools = normalise_assistant_tool_response(message_with_tools, tool_calls)
    
    print_json(normalized_with_tools, "AFTER normalization (note: content is now empty):")
    
    # Example 2: Response without tool calls
    print("\n📋 Example 2: Response WITHOUT tool calls")
    
    message_without_tools = {
        "role": "assistant",
        "content": "The weather in San Francisco is currently sunny with a temperature of 22°C."
    }
    
    print_json(message_without_tools, "BEFORE normalization:")
    
    normalized_without_tools = normalise_assistant_tool_response(message_without_tools, None)
    
    print_json(normalized_without_tools, "AFTER normalization (content preserved):")


async def demo_backend_response_normalization():
    """Demonstrate backend-specific response normalization."""
    print("\n\n🔄 DEMO 3: Backend Response Normalization")
    print("=" * 50)
    
    # Anthropic Claude response
    print("\n🧠 Anthropic Claude Response Normalization")
    anthropic_response = {
        "id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I'll help you check the weather in New York."
            },
            {
                "type": "tool_use",
                "id": "toolu_01A09q90qw90lq917835lq9",
                "name": "get_weather",
                "input": {
                    "location": "New York, NY",
                    "units": "fahrenheit"
                }
            }
        ],
        "model": "claude-3-sonnet-20240229",
        "stop_reason": "tool_use",
        "usage": {
            "input_tokens": 372,
            "output_tokens": 46
        }
    }
    
    print_json(anthropic_response, "Original Anthropic Response:")
    
    result = await normalise_response_async(anthropic_response, "anthropic", "claude-3-sonnet")
    
    print_json(result.normalized_response, "Normalized to OpenAI Format:")
    print(f"📊 Processing time: {result.processing_time_ms:.2f}ms")
    print(f"🔧 Tool calls detected: {result.tool_calls_count}")
    print(f"✅ Finish reason: {result.finish_reason}")
    
    # Google Vertex AI response
    print("\n\n🔍 Google Vertex AI Response Normalization")
    vertex_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "I'll check the current weather conditions for you."},
                        {
                            "functionCall": {
                                "name": "get_weather",
                                "args": {
                                    "location": "London, UK",
                                    "units": "celsius",
                                    "include_details": True
                                }
                            }
                        }
                    ]
                },
                "finishReason": "STOP",
                "index": 0,
                "safetyRatings": []
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 89,
            "candidatesTokenCount": 27,
            "totalTokenCount": 116
        }
    }
    
    print_json(vertex_response, "Original Vertex AI Response:")
    
    result = await normalise_response_async(vertex_response, "vertex", "gemini-pro")
    
    print_json(result.normalized_response, "Normalized to OpenAI Format:")
    print(f"📊 Processing time: {result.processing_time_ms:.2f}ms")
    print(f"🔧 Tool calls detected: {result.tool_calls_count}")
    print(f"✅ Finish reason: {result.finish_reason}")
    
    # Salesforce hosted model response
    print("\n\n🏢 Salesforce Hosted Model Response Normalization")
    salesforce_response = {
        "generation": {
            "generatedText": "I'll help you get the stock price information.",
            "parameters": {
                "usage": {
                    "inputTokenCount": 45,
                    "outputTokenCount": 12
                }
            }
        },
        "tool_calls": [
            {
                "id": "call_sf_123",
                "function": {
                    "name": "get_stock_price",
                    "arguments": {
                        "symbol": "AAPL",
                        "exchange": "NASDAQ",
                        "real_time": True
                    }
                }
            }
        ]
    }
    
    print_json(salesforce_response, "Original Salesforce Response:")
    
    result = await normalise_response_async(salesforce_response, "salesforce", "claude-3-haiku")
    
    print_json(result.normalized_response, "Normalized to OpenAI Format:")
    print(f"📊 Processing time: {result.processing_time_ms:.2f}ms")
    print(f"🔧 Tool calls detected: {result.tool_calls_count}")
    print(f"✅ Finish reason: {result.finish_reason}")


def demo_performance_features():
    """Demonstrate performance features."""
    print("\n\n⚡ DEMO 4: Performance Features")
    print("=" * 50)
    
    normaliser = ResponseNormaliser()
    
    # Perform several normalizations
    print("\n📈 Performing multiple normalizations...")
    
    for i in range(10):
        message = {
            "role": "assistant",
            "content": f"Processing request {i+1}"
        }
        
        tool_calls = [{
            "id": f"call_{i}",
            "type": "function",
            "function": {
                "name": "process_data",
                "arguments": f'{{"batch_id": {i}, "priority": "high"}}'
            }
        }]
        
        normaliser.normalise_assistant_tool_response(message, tool_calls)
    
    # Show performance stats
    stats = normaliser.get_performance_stats()
    
    print_json(stats, "Performance Statistics:")


def demo_error_handling():
    """Demonstrate error handling capabilities."""
    print("\n\n🛡️ DEMO 5: Error Handling")
    print("=" * 50)
    
    print("\n🔍 Testing various error conditions...")
    
    # Test 1: Invalid function name
    try:
        result = to_openai_tool_call("", {"param": "value"}, "call_123")
        print("❌ Should have raised ValueError for empty function name")
    except ValueError as e:
        print(f"✅ Correctly caught error for empty function name: {e}")
    
    # Test 2: Invalid arguments
    try:
        result = to_openai_tool_call("func", "not_a_dict", "call_123")
        print("❌ Should have raised ValueError for non-dict arguments")
    except ValueError as e:
        print(f"✅ Correctly caught error for invalid arguments: {e}")
    
    # Test 3: Malformed tool calls in normalization
    malformed_tool_calls = [
        {"id": "call_123", "missing": "function_field"},
        {"incomplete": "tool_call"},
        None
    ]
    
    message = {"role": "assistant", "content": "Testing error handling"}
    
    result = normalise_assistant_tool_response(message, malformed_tool_calls)
    
    print(f"✅ Gracefully handled malformed tool calls:")
    print(f"   Result type: {type(result)}")
    print(f"   Has role: {'role' in result}")
    print(f"   Content preserved: {result.get('content', 'MISSING')}")
    
    # Test 4: None inputs
    result = normalise_assistant_tool_response(None, None)
    print(f"✅ Gracefully handled None inputs:")
    print(f"   Result: {result}")


async def main():
    """Main demo function."""
    print("🚀 Response Normaliser Comprehensive Demo")
    print("=" * 50)
    print("This demo shows the response normalizer ensuring consistent")
    print("OpenAI-compatible tool_calls format across all backends.")
    print("=" * 50)
    
    # Run all demos
    demo_basic_tool_call_conversion()
    demo_assistant_response_normalization()
    await demo_backend_response_normalization()
    demo_performance_features()
    demo_error_handling()
    
    print("\n\n🎉 Demo Complete!")
    print("=" * 50)
    print("Key takeaways:")
    print("• All backends now produce consistent OpenAI tool_calls format")
    print("• assistant.content is empty when tools are called")
    print("• finish_reason is predictable: 'tool_calls' or 'stop'")
    print("• High performance with caching and async operations")
    print("• Robust error handling for malformed responses")
    print("• Thread-safe for concurrent requests")
    
    # Show final performance stats
    from response_normaliser import default_normaliser
    final_stats = default_normaliser.get_performance_stats()
    print(f"\n📊 Total normalizations performed: {final_stats['normalizations_performed']}")
    print(f"⚡ Average processing time: {final_stats['avg_processing_time_ms']:.2f}ms")
    print(f"🎯 Cache hit rate: {final_stats['cache_hit_rate']:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())