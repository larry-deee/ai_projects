#!/usr/bin/env python3
"""
Final API Compliance Test
=========================

Comprehensive test to verify 100% OpenAI and Anthropic API compliance.
Tests all the critical fixes implemented for tool validation.
"""

import json
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_schemas import (
    validate_tool_definitions,
    validate_anthropic_tool_definitions,
    ToolCallingValidationError,
    parse_tool_calls_from_response,
    _validate_tool_call_compliance
)

def test_openai_strict_validation():
    """Test that OpenAI validation strictly enforces specification."""
    print("Testing OpenAI strict validation...")
    
    test_cases = [
        # Missing type field
        ({
            "function": {"name": "test", "description": "test"}
        }, "missing required field: 'type'"),
        
        # Wrong type
        ({
            "type": "invalid",
            "function": {"name": "test", "description": "test"}
        }, "invalid 'type': 'invalid'"),
        
        # Missing function field
        ({
            "type": "function"
        }, "missing required field: 'function'"),
        
        # Missing function name
        ({
            "type": "function",
            "function": {"description": "test"}
        }, "missing required field: 'name'"),
        
        # Missing function description (CRITICAL FIX)
        ({
            "type": "function", 
            "function": {"name": "test"}
        }, "missing required field: 'description'"),
        
        # Invalid parameter type
        ({
            "type": "function",
            "function": {
                "name": "test",
                "description": "test",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "invalid_type"}
                    }
                }
            }
        }, "invalid type: 'invalid_type'"),
        
        # Array parameter missing items
        ({
            "type": "function",
            "function": {
                "name": "test",
                "description": "test", 
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "array"}
                    }
                }
            }
        }, "missing required 'items' schema"),
        
        # Object parameter missing properties
        ({
            "type": "function",
            "function": {
                "name": "test",
                "description": "test",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "object"}
                    }
                }
            }
        }, "missing required 'properties' schema"),
        
        # Required field not in properties
        ({
            "type": "function",
            "function": {
                "name": "test",
                "description": "test",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": ["missing_field"]
                }
            }
        }, "required properties don't exist"),
    ]
    
    passed = 0
    for i, (invalid_tool, expected_error) in enumerate(test_cases):
        try:
            validate_tool_definitions([invalid_tool])
            print(f"❌ Test case {i+1}: Invalid tool incorrectly passed validation")
        except ToolCallingValidationError as e:
            if expected_error.lower() in str(e).lower():
                print(f"✅ Test case {i+1}: Correctly rejected - {expected_error}")
                passed += 1
            else:
                print(f"❌ Test case {i+1}: Wrong error message - {str(e)}")
        except Exception as e:
            print(f"❌ Test case {i+1}: Unexpected error - {str(e)}")
    
    print(f"OpenAI Strict Validation: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)

def test_anthropic_strict_validation():
    """Test that Anthropic validation strictly enforces specification.""" 
    print("Testing Anthropic strict validation...")
    
    test_cases = [
        # Missing name
        ({
            "description": "test",
            "input_schema": {"type": "object", "properties": {}}
        }, "missing required fields: name"),
        
        # Missing description  
        ({
            "name": "test",
            "input_schema": {"type": "object", "properties": {}}
        }, "missing required fields: description"),
        
        # Missing input_schema
        ({
            "name": "test",
            "description": "test"
        }, "missing required fields: input_schema"),
        
        # Invalid input_schema type
        ({
            "name": "test",
            "description": "test",
            "input_schema": {"type": "invalid", "properties": {}}
        }, "input_schema 'type' must be 'object'"),
        
        # Missing properties in input_schema
        ({
            "name": "test",
            "description": "test", 
            "input_schema": {"type": "object"}
        }, "missing required fields: properties"),
    ]
    
    passed = 0
    for i, (invalid_tool, expected_error) in enumerate(test_cases):
        try:
            validate_anthropic_tool_definitions([invalid_tool])
            print(f"❌ Test case {i+1}: Invalid Anthropic tool incorrectly passed validation")
        except ToolCallingValidationError as e:
            if expected_error.lower() in str(e).lower():
                print(f"✅ Test case {i+1}: Correctly rejected - {expected_error}")
                passed += 1
            else:
                print(f"❌ Test case {i+1}: Wrong error message - {str(e)}")
        except Exception as e:
            print(f"❌ Test case {i+1}: Unexpected error - {str(e)}")
    
    print(f"Anthropic Strict Validation: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)

def test_tool_call_response_compliance():
    """Test that tool call responses are 100% OpenAI compliant."""
    print("Testing tool call response compliance...")
    
    # Test various response formats
    test_responses = [
        # Standard format
        """<function_calls>
        [{"name": "get_weather", "arguments": {"location": "NYC"}}]
        </function_calls>""",
        
        # n8n style format
        """<function_calls>
        [{"name": "send_email", "arguments": {"to": "user@test.com", "subject": "Test"}}]
        </function_calls>""",
        
        # Multiple calls
        """<function_calls>
        [
            {"name": "func1", "arguments": {"param1": "value1"}},
            {"name": "func2", "arguments": {"param2": "value2"}}
        ]
        </function_calls>""",
    ]
    
    total_calls = 0
    compliant_calls = 0
    
    for i, response_text in enumerate(test_responses):
        try:
            parsed_calls = parse_tool_calls_from_response(response_text)
            
            for call in parsed_calls:
                total_calls += 1
                if _validate_tool_call_compliance(call):
                    compliant_calls += 1
                    
                    # Verify specific OpenAI requirements
                    if not call['id'].startswith('call_'):
                        print(f"❌ Call ID doesn't start with 'call_': {call['id']}")
                        return False
                    
                    if call['type'] != 'function':
                        print(f"❌ Call type is not 'function': {call['type']}")
                        return False
                    
                    if not isinstance(call['function']['arguments'], str):
                        print(f"❌ Arguments not JSON string: {type(call['function']['arguments'])}")
                        return False
                    
                    # Verify arguments can be parsed as JSON
                    try:
                        json.loads(call['function']['arguments'])
                    except json.JSONDecodeError:
                        print(f"❌ Arguments not valid JSON: {call['function']['arguments']}")
                        return False
                else:
                    print(f"❌ Non-compliant tool call: {call}")
                    return False
        
        except Exception as e:
            print(f"❌ Failed to parse response {i+1}: {e}")
            return False
    
    print(f"✅ Tool call response compliance: {compliant_calls}/{total_calls} calls compliant")
    return compliant_calls == total_calls and total_calls > 0

def test_error_handling_compliance():
    """Test that validation errors are properly structured."""
    print("Testing error handling compliance...")
    
    # Test validation error structure
    try:
        validate_tool_definitions([{"invalid": "tool"}])
        print("❌ Invalid tool should have raised validation error")
        return False
    except ToolCallingValidationError as e:
        error_msg = str(e)
        if "Tool validation failed" not in error_msg:
            print(f"❌ Error message format incorrect: {error_msg}")
            return False
        
        # Test error has details
        if "errors:" not in error_msg:
            print(f"❌ Error message lacks detail: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ Wrong exception type: {type(e)} - {str(e)}")
        return False
    
    print("✅ Error handling compliance verified")
    return True

def main():
    """Run comprehensive API compliance tests."""
    print("🔥 COMPREHENSIVE API COMPLIANCE TEST SUITE")
    print("=" * 60)
    print("Testing fixes for 100% OpenAI and Anthropic API compliance")
    print()
    
    tests = [
        ("OpenAI Strict Validation", test_openai_strict_validation),
        ("Anthropic Strict Validation", test_anthropic_strict_validation),
        ("Tool Call Response Compliance", test_tool_call_response_compliance),
        ("Error Handling Compliance", test_error_handling_compliance),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"🧪 {test_name}")
        print("-" * 50)
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
        print()
    
    # Final results
    print("🎯 FINAL RESULTS")
    print("=" * 60)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 SUCCESS: All tests passed!")
        print("✅ API compliance fixes are working correctly")
        print("🚀 Ready for 100% OpenAI and Anthropic API compliance")
        return True
    else:
        print("❌ FAILURE: Some tests failed")
        print("🔧 Additional fixes needed for full API compliance")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)