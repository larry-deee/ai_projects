#!/usr/bin/env python3
"""
N8N Tool Call Warning Fix Validation
====================================

This test specifically validates that the "Tool call missing function name" warning
has been completely eliminated for the exact n8n LangChain XML format reported by the user.

This test uses VERBOSE_TOOL_LOGS=1 to ensure any warnings would be shown.
"""

import os
import sys
import logging
from io import StringIO

# Set verbose tool logs to catch any warnings
os.environ['VERBOSE_TOOL_LOGS'] = '1'

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tool_handler import ToolCallingHandler
from tool_schemas import ToolCallingConfig, validate_tool_definitions

def test_n8n_warning_elimination():
    """Test that the 'Tool call missing function name' warning is completely eliminated"""
    
    print("🔍 N8N WARNING ELIMINATION VALIDATION")
    print("=" * 60)
    print("Testing with VERBOSE_TOOL_LOGS=1 to catch any warnings...")
    print()
    
    # Capture all log output
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Get the tool_handler logger
    tool_handler_logger = logging.getLogger('tool_handler')
    tool_handler_logger.addHandler(handler)
    tool_handler_logger.setLevel(logging.DEBUG)
    
    # The exact n8n LangChain XML format that was failing
    n8n_xml_response = """<function_calls>[{"name": "Research_Agent", "arguments": {"System_Message": "Conduct evidence-first research on the latest news in AI and Generative AI, with a focus on GPT-5. Include findings, angles, keywords, and credible sources."}}]</function_calls>"""
    
    # Create tools definition
    tools_definition = [
        {
            "type": "function",
            "function": {
                "name": "Research_Agent",
                "description": "Conduct research on various topics and provide comprehensive information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "System_Message": {
                            "type": "string",
                            "description": "The research query or system message to process"
                        }
                    },
                    "required": ["System_Message"]
                }
            }
        }
    ]
    
    print(f"📋 Testing XML Response: {n8n_xml_response[:100]}...")
    print()
    
    try:
        # Validate tools
        validated_tools = validate_tool_definitions(tools_definition)
        print(f"✅ Tools validated: {len(validated_tools)} tools")
        
        # Create tool handler
        config = ToolCallingConfig()
        handler = ToolCallingHandler(config)
        
        # Parse tool calls - this is where the warning would occur
        tool_calls = handler._parse_tool_calls_from_response(n8n_xml_response, validated_tools)
        
        print(f"✅ Tool calls parsed: {len(tool_calls)} calls")
        
        if tool_calls:
            for i, call in enumerate(tool_calls):
                print(f"   Tool Call {i+1}:")
                print(f"     - Function Name: '{call.function_name}'")
                print(f"     - Arguments: {call.function_arguments}")
                print(f"     - ID: {call.id}")
        
        # Check captured logs for any warnings
        log_output = log_capture.getvalue()
        
        print()
        print("🔍 LOG ANALYSIS:")
        print("-" * 30)
        
        # Check for the specific warning message
        warning_found = "Tool call missing function name" in log_output
        
        if warning_found:
            print("❌ WARNING DETECTED!")
            print("   The 'Tool call missing function name' warning is still present")
            print("   Log output containing warning:")
            warning_lines = [line for line in log_output.split('\n') if 'Tool call missing function name' in line]
            for line in warning_lines:
                print(f"   {line}")
            return False
        else:
            print("✅ NO WARNING DETECTED!")
            print("   The 'Tool call missing function name' warning has been eliminated")
            
        # Show all debug logs for verification
        if log_output.strip():
            print()
            print("📋 All Tool Handler Logs:")
            for line in log_output.split('\n'):
                if line.strip() and 'tool_handler' in line:
                    print(f"   {line}")
        
        print()
        print("🎯 VALIDATION RESULT: SUCCESS")
        print("   The n8n tool calling warning fix is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up log handler
        tool_handler_logger.removeHandler(handler)


def test_multiple_n8n_formats():
    """Test multiple n8n XML formats to ensure comprehensive coverage"""
    
    print()
    print("🧪 TESTING MULTIPLE N8N FORMATS")
    print("=" * 60)
    
    # Various n8n XML formats that should all work without warnings
    test_cases = [
        {
            "name": "Standard n8n LangChain format",
            "xml": """<function_calls>[{"name": "Research_Agent", "arguments": {"System_Message": "test message"}}]</function_calls>"""
        },
        {
            "name": "Single object format",
            "xml": """<function_calls>{"name": "Research_Agent", "arguments": {"System_Message": "test message"}}</function_calls>"""
        },
        {
            "name": "Multi-line formatted XML",
            "xml": """<function_calls>
[
  {
    "name": "Research_Agent",
    "arguments": {
      "System_Message": "test message"
    }
  }
]
</function_calls>"""
        }
    ]
    
    tools_definition = [
        {
            "type": "function",
            "function": {
                "name": "Research_Agent",
                "description": "Test function",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "System_Message": {"type": "string"}
                    },
                    "required": ["System_Message"]
                }
            }
        }
    ]
    
    validated_tools = validate_tool_definitions(tools_definition)
    config = ToolCallingConfig()
    handler = ToolCallingHandler(config)
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        
        # Capture logs for this test case
        log_capture = StringIO()
        log_handler = logging.StreamHandler(log_capture)
        log_handler.setLevel(logging.DEBUG)
        
        tool_handler_logger = logging.getLogger('tool_handler')
        tool_handler_logger.addHandler(log_handler)
        
        try:
            tool_calls = handler._parse_tool_calls_from_response(test_case['xml'], validated_tools)
            
            log_output = log_capture.getvalue()
            warning_found = "Tool call missing function name" in log_output
            
            if warning_found:
                print(f"   ❌ FAILED - Warning detected")
                all_passed = False
            else:
                print(f"   ✅ PASSED - No warnings, {len(tool_calls)} calls parsed")
                
        except Exception as e:
            print(f"   ❌ FAILED - Exception: {e}")
            all_passed = False
            
        finally:
            tool_handler_logger.removeHandler(log_handler)
    
    return all_passed


if __name__ == "__main__":
    print("🚀 Starting N8N Tool Call Warning Fix Validation")
    print()
    
    # Test 1: Main n8n scenario
    test1_passed = test_n8n_warning_elimination()
    
    # Test 2: Multiple formats
    test2_passed = test_multiple_n8n_formats()
    
    print()
    print("=" * 60)
    print("📊 FINAL VALIDATION RESULTS")
    print("=" * 60)
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("   The 'Tool call missing function name' warning has been completely eliminated")
        print("   N8N LangChain tool calling will now work without warnings")
        exit(0)
    else:
        print("❌ SOME TESTS FAILED!")
        print("   The warning fix needs additional work")
        exit(1)