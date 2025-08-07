#!/usr/bin/env python3
"""
Simple Tool Validation Test
============================

Basic test to verify tool validation implementation is working correctly.
"""

import json
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_schemas import (
    validate_tool_definitions,
    validate_anthropic_tool_definitions,
    ToolCallingValidationError
)

def test_valid_openai_tool():
    """Test that valid OpenAI tools pass validation."""
    print("Testing valid OpenAI tool...")
    
    valid_tool = {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
    }
    
    try:
        result = validate_tool_definitions([valid_tool])
        print(f"✅ Valid tool passed validation: {result[0].function.name}")
        return True
    except Exception as e:
        print(f"❌ Valid tool failed validation: {e}")
        return False

def test_invalid_openai_tool():
    """Test that invalid OpenAI tools are rejected."""
    print("Testing invalid OpenAI tool (missing type field)...")
    
    invalid_tool = {
        "function": {
            "name": "test_func",
            "description": "Test function"
        }
    }
    
    try:
        result = validate_tool_definitions([invalid_tool])
        print(f"❌ Invalid tool incorrectly passed validation")
        return False
    except ToolCallingValidationError as e:
        if "missing required field: 'type'" in str(e):
            print(f"✅ Invalid tool correctly rejected: {e}")
            return True
        else:
            print(f"❌ Invalid tool rejected with wrong error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_invalid_parameter_type():
    """Test that invalid parameter types are rejected."""
    print("Testing invalid parameter type...")
    
    invalid_tool = {
        "type": "function",
        "function": {
            "name": "test_func",
            "description": "Test function",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "invalid_type",
                        "description": "Test parameter"
                    }
                }
            }
        }
    }
    
    try:
        result = validate_tool_definitions([invalid_tool])
        print(f"❌ Tool with invalid parameter type incorrectly passed validation")
        return False
    except ToolCallingValidationError as e:
        if "invalid type: 'invalid_type'" in str(e):
            print(f"✅ Tool with invalid parameter type correctly rejected: {e}")
            return True
        else:
            print(f"❌ Tool rejected with wrong error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_valid_anthropic_tool():
    """Test that valid Anthropic tools pass validation."""
    print("Testing valid Anthropic tool...")
    
    valid_tool = {
        "name": "get_weather",
        "description": "Get weather for a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name"
                }
            },
            "required": ["location"]
        }
    }
    
    try:
        result = validate_anthropic_tool_definitions([valid_tool])
        print(f"✅ Valid Anthropic tool passed validation: {result[0]['name']}")
        return True
    except Exception as e:
        print(f"❌ Valid Anthropic tool failed validation: {e}")
        return False

def test_invalid_anthropic_tool():
    """Test that invalid Anthropic tools are rejected."""
    print("Testing invalid Anthropic tool (missing required fields)...")
    
    invalid_tool = {
        "name": "test_func",
        # Missing description and input_schema
    }
    
    try:
        result = validate_anthropic_tool_definitions([invalid_tool])
        print(f"❌ Invalid Anthropic tool incorrectly passed validation")
        return False
    except ToolCallingValidationError as e:
        if "missing required fields" in str(e):
            print(f"✅ Invalid Anthropic tool correctly rejected: {e}")
            return True
        else:
            print(f"❌ Invalid Anthropic tool rejected with wrong error: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Tool Validation Test Suite")
    print("=" * 50)
    
    tests = [
        test_valid_openai_tool,
        test_invalid_openai_tool,
        test_invalid_parameter_type,
        test_valid_anthropic_tool,
        test_invalid_anthropic_tool
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Tool validation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)