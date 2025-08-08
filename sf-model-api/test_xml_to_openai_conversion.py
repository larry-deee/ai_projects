#!/usr/bin/env python3
"""
Test XML to OpenAI Tool Call Conversion Fix
==========================================

This script tests the critical fix for converting XML function_calls to OpenAI tool_calls format.
It simulates the exact scenario that was failing for n8n clients.

Usage:
    python test_xml_to_openai_conversion.py
"""

import json
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_xml_detection_and_conversion():
    """Test the XML function_calls detection and conversion logic."""
    print("🧪 Test 1: XML Detection and Conversion")
    print("-" * 40)
    
    try:
        from tool_schemas import parse_tool_calls_from_response
        from response_normaliser import to_openai_tool_call, normalise_assistant_tool_response
        
        # Mock response content with XML function_calls (the problematic format)
        xml_content = '''<function_calls>
[{"name": "research_agent", "arguments": {"q": "hello"}}]
</function_calls>'''
        
        print(f"Input XML content: {xml_content}")
        
        # Test parsing XML function_calls
        tool_calls = parse_tool_calls_from_response(xml_content)
        
        if tool_calls and len(tool_calls) > 0:
            print(f"✅ Successfully parsed {len(tool_calls)} tool calls from XML")
            
            # Tool calls are already in OpenAI format from parsing
            openai_tool_calls = tool_calls
            
            print(f"✅ Successfully converted to {len(openai_tool_calls)} OpenAI tool calls")
            
            # Print the converted result
            if openai_tool_calls:
                print("Converted OpenAI format:")
                print(json.dumps(openai_tool_calls[0], indent=2))
                
                # Test message normalization
                message = {
                    "role": "assistant",
                    "content": xml_content  # This should be replaced with empty content
                }
                
                normalized_message = normalise_assistant_tool_response(
                    message, openai_tool_calls, "tool_calls"
                )
                
                print("\nNormalized message:")
                print(json.dumps(normalized_message, indent=2))
                
                # Verify the fix
                assert normalized_message["content"] == "", "Content should be empty with tool calls"
                assert "tool_calls" in normalized_message, "Should have tool_calls field"
                assert len(normalized_message["tool_calls"]) > 0, "Should have at least one tool call"
                
                tool_call = normalized_message["tool_calls"][0]
                assert tool_call["type"] == "function", "Tool call should have type 'function'"
                assert tool_call["function"]["name"] == "research_agent", "Function name should be correct"
                
                # Parse and verify arguments
                args = json.loads(tool_call["function"]["arguments"])
                assert args["q"] == "hello", "Arguments should be preserved correctly"
                
                print("✅ All assertions passed - fix works correctly!")
                
        else:
            print("❌ Failed to parse tool calls from XML")
            return False
            
        print("✅ Test 1 PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mock_openai_response_conversion():
    """Test the complete OpenAI response conversion scenario."""
    print("🧪 Test 2: Mock OpenAI Response Conversion")
    print("-" * 40)
    
    try:
        from tool_schemas import parse_tool_calls_from_response
        from response_normaliser import to_openai_tool_call, normalise_assistant_tool_response
        
        # Mock OpenAI response with XML content (the problematic scenario)
        openai_response = {
            "id": "chatcmpl-test123",
            "object": "chat.completion",
            "created": 1703123456,
            "model": "sfdc_ai__DefaultGPT4Omni",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '''<function_calls>
[{"name": "research_agent", "arguments": {"q": "hello"}}]
</function_calls>'''
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 15,
                "total_tokens": 35
            }
        }
        
        print("Original problematic response:")
        print(json.dumps(openai_response["choices"][0]["message"], indent=2))
        
        # Simulate the conversion logic from our fix
        message = openai_response['choices'][0]['message']
        response_content = message.get('content', '')
        
        if response_content and isinstance(response_content, str) and "<function_calls>" in response_content:
            print("\n🔧 Detected XML function_calls, converting to OpenAI format...")
            
            # Parse tool calls from the XML content
            tool_calls = parse_tool_calls_from_response(response_content)
            
            if tool_calls and len(tool_calls) > 0:
                print(f"✅ Parsed {len(tool_calls)} tool calls from XML")
                
                # Tool calls are already in OpenAI format from parsing
                openai_tool_calls = tool_calls
                
                # Apply normalization
                if openai_tool_calls:
                    normalized_message = normalise_assistant_tool_response(
                        message, openai_tool_calls, "tool_calls"
                    )
                    
                    # Update the response
                    openai_response['choices'][0]['message'] = normalized_message
                    openai_response['choices'][0]['finish_reason'] = "tool_calls"
                    
                    print("✅ Conversion successful!")
                    
        print("\nFixed response:")
        print(json.dumps(openai_response["choices"][0]["message"], indent=2))
        
        # Verify the expected format
        fixed_message = openai_response["choices"][0]["message"]
        
        assert fixed_message["content"] == "", "Content should be empty"
        assert "tool_calls" in fixed_message, "Should have tool_calls field"
        assert openai_response["choices"][0]["finish_reason"] == "tool_calls", "Finish reason should be tool_calls"
        
        tool_call = fixed_message["tool_calls"][0]
        assert tool_call["id"], "Tool call should have ID"
        assert tool_call["type"] == "function", "Tool call should have type function"
        assert tool_call["function"]["name"] == "research_agent", "Function name should be correct"
        
        args = json.loads(tool_call["function"]["arguments"])
        assert args["q"] == "hello", "Arguments should be preserved"
        
        print("✅ All assertions passed - complete conversion works!")
        print("✅ Test 2 PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_false_positives():
    """Test that normal responses without XML are not affected."""
    print("🧪 Test 3: No False Positives")
    print("-" * 40)
    
    try:
        from response_normaliser import normalise_assistant_tool_response
        
        # Normal response without XML
        normal_response = {
            "role": "assistant", 
            "content": "I can help you with that. Let me search for information."
        }
        
        # Should not be affected by our fix
        result = normalise_assistant_tool_response(normal_response, None)
        
        assert result["content"] == "I can help you with that. Let me search for information.", "Normal content should be preserved"
        assert "tool_calls" not in result, "Should not have tool_calls field"
        
        print("✅ Normal responses are not affected")
        
        # Response with tool_calls but no XML content
        response_with_tools = {
            "role": "assistant",
            "content": ""
        }
        
        tool_calls = [{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "test_function",
                "arguments": '{"param": "value"}'
            }
        }]
        
        result = normalise_assistant_tool_response(response_with_tools, tool_calls)
        
        assert result["content"] == "", "Content should be empty with tool calls"
        assert "tool_calls" in result, "Should have tool_calls field"
        assert len(result["tool_calls"]) == 1, "Should preserve tool calls"
        
        print("✅ Normal tool call responses work correctly")
        print("✅ Test 3 PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        return False


def main():
    """Run all tests to validate the XML to OpenAI conversion fix."""
    print("🚀 XML to OpenAI Tool Call Conversion Test Suite")
    print("=" * 60)
    print("Testing the critical fix for n8n compatibility")
    print("=" * 60)
    
    test_results = []
    
    # Run tests
    tests = [
        test_xml_detection_and_conversion,
        test_mock_openai_response_conversion,
        test_no_false_positives
    ]
    
    for test in tests:
        result = test()
        test_results.append(result)
    
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
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ XML to OpenAI conversion fix is working correctly")
        print("✅ n8n clients should now receive proper tool_calls format")
        print("✅ Normal responses are not affected")
        print("\n🔧 The fix detects <function_calls> XML in response content")
        print("🔧 Parses the XML to extract tool call information")
        print("🔧 Converts to OpenAI tool_calls format using response_normaliser")
        print("🔧 Sets proper finish_reason and empties content field")
        return 0
    else:
        print("❌ Some tests failed - fix may need adjustments")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)