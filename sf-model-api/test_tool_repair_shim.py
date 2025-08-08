#!/usr/bin/env python3
"""
Test Tool-Call Repair Shim
==========================

Simple test to verify that the tool-call repair shim is working correctly
and fixes common "Tool call missing function name" errors.
"""

import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from openai_tool_fix import repair_openai_tool_calls, repair_openai_response, validate_tool_calls_format

def test_missing_function_name():
    """Test repair of tool calls with missing function name."""
    print("Testing missing function name repair...")
    
    # Malformed message with missing function.name
    message = {
        "role": "assistant",
        "content": "I'll help you with that.",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "arguments": '{"query": "test"}'
                    # Missing "name" field
                }
            }
        ]
    }
    
    # Tool definitions for context
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_database",
                "description": "Search the database"
            }
        }
    ]
    
    repaired_message, was_changed = repair_openai_tool_calls(message, tools)
    
    assert was_changed, "Expected repair to be needed"
    assert len(repaired_message["tool_calls"]) == 1, "Expected one tool call"
    assert repaired_message["tool_calls"][0]["function"]["name"] == "search_database", "Expected function name to be fixed"
    
    print("✅ Missing function name repair: PASSED")

def test_non_string_arguments():
    """Test repair of tool calls with non-string arguments."""
    print("Testing non-string arguments repair...")
    
    message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1", 
                "type": "function",
                "function": {
                    "name": "calculate",
                    "arguments": {"x": 5, "y": 10}  # Should be JSON string
                }
            }
        ]
    }
    
    repaired_message, was_changed = repair_openai_tool_calls(message, None)
    
    assert was_changed, "Expected repair to be needed"
    assert isinstance(repaired_message["tool_calls"][0]["function"]["arguments"], str), "Expected arguments to be string"
    
    # Verify it's valid JSON
    args = json.loads(repaired_message["tool_calls"][0]["function"]["arguments"])
    assert args["x"] == 5 and args["y"] == 10, "Expected arguments to be preserved"
    
    print("✅ Non-string arguments repair: PASSED")

def test_malformed_structure():
    """Test repair of completely malformed tool call structure."""
    print("Testing malformed structure repair...")
    
    message = {
        "role": "assistant", 
        "content": "",
        "tool_calls": [
            {
                # Missing id, type
                "name": "test_function",
                "input": {"param": "value"}
            }
        ]
    }
    
    repaired_message, was_changed = repair_openai_tool_calls(message, None)
    
    assert was_changed, "Expected repair to be needed"
    
    tool_call = repaired_message["tool_calls"][0]
    assert tool_call["id"], "Expected ID to be generated"
    assert tool_call["type"] == "function", "Expected type to be function"
    assert tool_call["function"]["name"] == "test_function", "Expected name to be preserved"
    
    print("✅ Malformed structure repair: PASSED")

def test_full_response_repair():
    """Test repair of full OpenAI response with multiple choices."""
    print("Testing full response repair...")
    
    response = {
        "id": "chatcmpl-test",
        "object": "chat.completion", 
        "created": 1234567890,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                # Missing name
                                "arguments": '{"param": "value"}'
                            }
                        }
                    ]
                },
                "finish_reason": "tool_calls"
            }
        ]
    }
    
    tools = [{"type": "function", "function": {"name": "fix_this"}}]
    
    repaired_response, was_changed = repair_openai_response(response, tools)
    
    assert was_changed, "Expected repair to be needed"
    assert repaired_response["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "fix_this"
    
    print("✅ Full response repair: PASSED")

def test_validation():
    """Test validation function."""
    print("Testing validation...")
    
    # Valid tool calls
    valid_calls = [
        {
            "id": "call_1",
            "type": "function", 
            "function": {
                "name": "test_func",
                "arguments": '{"param": "value"}'
            }
        }
    ]
    
    issues = validate_tool_calls_format(valid_calls)
    assert len(issues) == 0, f"Expected no issues, got: {issues}"
    
    # Invalid tool calls
    invalid_calls = [
        {
            # Missing id, type, function.name
            "type": "function",
            "function": {
                "arguments": "not_json"
            }
        }
    ]
    
    issues = validate_tool_calls_format(invalid_calls)
    assert len(issues) > 0, "Expected validation issues"
    
    print("✅ Validation: PASSED")

if __name__ == "__main__":
    print("🔧 Running Tool-Call Repair Shim Tests...")
    print()
    
    try:
        test_missing_function_name()
        test_non_string_arguments()
        test_malformed_structure() 
        test_full_response_repair()
        test_validation()
        
        print()
        print("🎉 All tests passed! Tool-call repair shim is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)