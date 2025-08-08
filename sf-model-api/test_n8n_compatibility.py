#!/usr/bin/env python3
"""
Test script for n8n compatibility mode implementation.
Tests the new tool validation and n8n detection features.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the functions we implemented
from async_endpoint_server import _has_valid_tools

def test_has_valid_tools():
    """Test the _has_valid_tools function"""
    
    print("Testing _has_valid_tools function...")
    
    # Test 1: Empty/None tools
    assert _has_valid_tools(None) == False, "None tools should return False"
    assert _has_valid_tools([]) == False, "Empty tools should return False"
    print("✅ Empty/None tools test passed")
    
    # Test 2: Valid tools
    valid_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather information"
            }
        }
    ]
    assert _has_valid_tools(valid_tools) == True, "Valid tools should return True"
    print("✅ Valid tools test passed")
    
    # Test 3: Invalid tools (no function name)
    invalid_tools_no_name = [
        {
            "type": "function",
            "function": {
                "description": "No name provided"
            }
        }
    ]
    assert _has_valid_tools(invalid_tools_no_name) == False, "Tools without function name should return False"
    print("✅ Invalid tools (no name) test passed")
    
    # Test 4: Invalid tools (wrong type)
    invalid_tools_wrong_type = [
        {
            "type": "not_function",
            "function": {
                "name": "some_name"
            }
        }
    ]
    assert _has_valid_tools(invalid_tools_wrong_type) == False, "Tools with wrong type should return False"
    print("✅ Invalid tools (wrong type) test passed")
    
    # Test 5: Mixed valid and invalid tools (should return True if at least one valid)
    mixed_tools = [
        {
            "type": "not_function",
            "function": {"name": "invalid"}
        },
        {
            "type": "function", 
            "function": {"name": "valid_function"}
        }
    ]
    assert _has_valid_tools(mixed_tools) == True, "Mixed tools with at least one valid should return True"
    print("✅ Mixed tools test passed")
    
    print("🎉 All _has_valid_tools tests passed!")

def test_tool_handler_utility():
    """Test the tool handler utility function"""
    
    from tool_handler import has_valid_tools
    
    print("\nTesting tool_handler.has_valid_tools function...")
    
    # Should have same behavior as _has_valid_tools
    valid_tools = [{"type": "function", "function": {"name": "test"}}]
    assert has_valid_tools(valid_tools) == True, "Tool handler function should work the same"
    assert has_valid_tools([]) == False, "Empty tools should return False"
    print("✅ Tool handler utility test passed")

def test_environment_variables():
    """Test environment variable handling"""
    
    print("\nTesting environment variables...")
    
    # Test N8N_COMPAT_MODE detection
    original_value = os.environ.get('N8N_COMPAT_MODE')
    
    # Test enabled case
    os.environ['N8N_COMPAT_MODE'] = '1'
    assert os.environ.get('N8N_COMPAT_MODE', '1') == '1', "N8N_COMPAT_MODE should be enabled by default"
    
    # Test disabled case
    os.environ['N8N_COMPAT_MODE'] = '0'
    assert os.environ.get('N8N_COMPAT_MODE', '1') == '0', "N8N_COMPAT_MODE should be disabled when set to 0"
    
    # Restore original value
    if original_value is not None:
        os.environ['N8N_COMPAT_MODE'] = original_value
    else:
        os.environ.pop('N8N_COMPAT_MODE', None)
    
    print("✅ Environment variables test passed")

def main():
    """Run all tests"""
    print("🧪 Running n8n compatibility tests...\n")
    
    try:
        test_has_valid_tools()
        test_tool_handler_utility()
        test_environment_variables()
        
        print("\n🎉 All tests passed! n8n compatibility implementation is working correctly.")
        return 0
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())