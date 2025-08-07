#!/usr/bin/env python3
"""
Tool Call Compliance Test
=========================

Test to verify tool call response formatting is 100% OpenAI API compliant.
"""

import json
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_schemas import (
    parse_tool_calls_from_response,
    _create_openai_compliant_tool_call,
    _validate_tool_call_compliance,
    create_tool_call_id
)

def test_openai_compliant_tool_call_creation():
    """Test that tool calls are created in OpenAI-compliant format."""
    print("Testing OpenAI-compliant tool call creation...")
    
    # Test with raw tool call data (n8n style)
    raw_call = {
        "name": "get_weather",
        "arguments": {
            "location": "San Francisco",
            "unit": "fahrenheit"
        }
    }
    
    try:
        compliant_call = _create_openai_compliant_tool_call(raw_call)
        
        # Verify structure
        required_fields = ['id', 'type', 'function']
        for field in required_fields:
            if field not in compliant_call:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Verify values
        if compliant_call['type'] != 'function':
            print(f"❌ Invalid type: {compliant_call['type']}")
            return False
        
        if not compliant_call['id'].startswith('call_'):
            print(f"❌ Invalid ID format: {compliant_call['id']}")
            return False
        
        function_obj = compliant_call['function']
        if 'name' not in function_obj or 'arguments' not in function_obj:
            print(f"❌ Invalid function object structure")
            return False
        
        if function_obj['name'] != 'get_weather':
            print(f"❌ Invalid function name: {function_obj['name']}")
            return False
        
        # Verify arguments is JSON string
        if not isinstance(function_obj['arguments'], str):
            print(f"❌ Arguments must be JSON string, got: {type(function_obj['arguments'])}")
            return False
        
        # Verify arguments can be parsed
        try:
            parsed_args = json.loads(function_obj['arguments'])
            if parsed_args != {"location": "San Francisco", "unit": "fahrenheit"}:
                print(f"❌ Parsed arguments don't match: {parsed_args}")
                return False
        except json.JSONDecodeError as e:
            print(f"❌ Arguments not valid JSON: {e}")
            return False
        
        print("✅ OpenAI-compliant tool call created successfully")
        print(f"   Structure: {json.dumps(compliant_call, indent=2)}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to create compliant tool call: {e}")
        return False

def test_tool_call_compliance_validation():
    """Test that compliance validation correctly identifies valid/invalid tool calls."""
    print("Testing tool call compliance validation...")
    
    # Valid OpenAI tool call
    valid_call = {
        "id": "call_abc123",
        "type": "function",
        "function": {
            "name": "test_function",
            "arguments": "{\"param1\":\"value1\"}"
        }
    }
    
    if not _validate_tool_call_compliance(valid_call):
        print("❌ Valid tool call failed compliance check")
        return False
    
    # Invalid tool calls
    invalid_calls = [
        # Missing ID
        {
            "type": "function",
            "function": {"name": "test", "arguments": "{}"}
        },
        # Wrong type
        {
            "id": "call_123",
            "type": "invalid",
            "function": {"name": "test", "arguments": "{}"}
        },
        # Arguments not JSON string
        {
            "id": "call_123",
            "type": "function",
            "function": {"name": "test", "arguments": {}}
        },
        # Missing function name
        {
            "id": "call_123",
            "type": "function",
            "function": {"arguments": "{}"}
        }
    ]
    
    for i, invalid_call in enumerate(invalid_calls):
        if _validate_tool_call_compliance(invalid_call):
            print(f"❌ Invalid tool call {i+1} incorrectly passed compliance check")
            return False
    
    print("✅ Tool call compliance validation working correctly")
    return True

def test_tool_call_id_generation():
    """Test that tool call IDs are generated correctly."""
    print("Testing tool call ID generation...")
    
    # Test ID generation
    id1 = create_tool_call_id()
    id2 = create_tool_call_id()
    
    # IDs should be unique
    if id1 == id2:
        print("❌ Tool call IDs are not unique")
        return False
    
    # IDs should start with 'call_'
    if not id1.startswith('call_') or not id2.startswith('call_'):
        print(f"❌ Tool call IDs don't start with 'call_': {id1}, {id2}")
        return False
    
    print(f"✅ Tool call ID generation working correctly: {id1}")
    return True

def test_response_parsing_compliance():
    """Test that response parsing produces compliant tool calls."""
    print("Testing response parsing compliance...")
    
    # Test response with function calls
    response_text = """
    Here are the function calls:
    <function_calls>
    [
        {
            "name": "get_weather",
            "arguments": {
                "location": "New York",
                "unit": "celsius"
            }
        },
        {
            "name": "send_email",
            "arguments": {
                "to": "user@example.com",
                "subject": "Weather Update"
            }
        }
    ]
    </function_calls>
    """
    
    try:
        parsed_calls = parse_tool_calls_from_response(response_text)
        
        if len(parsed_calls) != 2:
            print(f"❌ Expected 2 tool calls, got {len(parsed_calls)}")
            return False
        
        # Verify each call is compliant
        for i, call in enumerate(parsed_calls):
            if not _validate_tool_call_compliance(call):
                print(f"❌ Parsed tool call {i+1} is not compliant: {call}")
                return False
        
        # Verify specific structure
        first_call = parsed_calls[0]
        if first_call['function']['name'] != 'get_weather':
            print(f"❌ Wrong function name in first call: {first_call['function']['name']}")
            return False
        
        # Verify arguments parsing
        args = json.loads(first_call['function']['arguments'])
        expected_args = {"location": "New York", "unit": "celsius"}
        if args != expected_args:
            print(f"❌ Wrong arguments in first call: {args} != {expected_args}")
            return False
        
        print("✅ Response parsing produces compliant tool calls")
        return True
    
    except Exception as e:
        print(f"❌ Response parsing failed: {e}")
        return False

def main():
    """Run all compliance tests."""
    print("🧪 Tool Call Compliance Test Suite")
    print("=" * 50)
    
    tests = [
        test_openai_compliant_tool_call_creation,
        test_tool_call_compliance_validation,
        test_tool_call_id_generation,
        test_response_parsing_compliance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Tool call responses are 100% OpenAI compliant.")
        return True
    else:
        print("❌ Some tests failed. Tool call compliance needs improvement.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)