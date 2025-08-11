#!/usr/bin/env python3
"""
Comprehensive N8N Tool Call Debugging Script
=============================================

This script replicates the exact n8n workflow scenario described by the user
and traces through every step of the tool calling pipeline to identify where
the "Tool call missing function name" warning is being triggered.

The user reports:
- n8n LangChain workflow generates XML function calls: <function_calls>[{"name": "Research_Agent", "arguments": {...}}]</function_calls>
- Server logs show HTTP 200 but warning "Tool call missing function name"
- The function call should be properly parsed and executed

This script will:
1. Mock the exact n8n LangChain output format
2. Trace through the entire tool calling pipeline step by step
3. Enable detailed logging to see where the issue occurs
"""

import sys
import os
import logging
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Enable DEBUG logging to see all the details
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')

# Import necessary modules
from tool_schemas import parse_tool_calls_from_response, _validate_tool_call_compliance
from tool_handler import ToolCallingHandler
from tool_schemas import ToolCallingConfig, validate_tool_definitions

def test_exact_n8n_scenario():
    """Test the exact n8n scenario described by the user"""
    
    print("🔍 COMPREHENSIVE N8N DEBUGGING")
    print("=" * 80)
    print("Testing the exact scenario reported by the user...")
    print()
    
    # STEP 1: Create the exact n8n LangChain output format
    n8n_response_text = """<function_calls>[{"name": "Research_Agent", "arguments": {"System_Message": "Conduct evidence-first research on the latest news in AI and Generative AI, with a focus on GPT-5. Include findings, angles, keywords, and credible sources."}}]</function_calls>"""
    
    print("📋 N8N Response Text:")
    print(f"   Length: {len(n8n_response_text)} characters")
    print(f"   Contains XML tags: {'<function_calls>' in n8n_response_text}")
    print(f"   Raw text: {n8n_response_text}")
    print()
    
    # STEP 2: Test XML parsing directly
    print("🧪 STEP 1: Direct XML Parsing")
    print("-" * 40)
    
    try:
        # This is the exact function that should handle the XML parsing
        parsed_calls = parse_tool_calls_from_response(n8n_response_text)
        
        print(f"   Parsed calls count: {len(parsed_calls)}")
        
        if parsed_calls:
            for i, call in enumerate(parsed_calls):
                print(f"   Call {i+1}:")
                print(f"     - Raw structure: {json.dumps(call, indent=6)}")
                print(f"     - Has 'id' field: {'id' in call}")
                print(f"     - Has 'type' field: {'type' in call}")
                print(f"     - Has 'function' field: {'function' in call}")
                
                if 'function' in call:
                    func = call['function']
                    print(f"     - Function has 'name': {'name' in func}")
                    print(f"     - Function has 'arguments': {'arguments' in func}")
                    
                    if 'name' in func:
                        print(f"     - Function name: '{func['name']}'")
                        print(f"     - Function name type: {type(func['name'])}")
                        print(f"     - Function name empty: {not func['name']}")
                    else:
                        print(f"     - ❌ Function missing 'name' field!")
                        
                    if 'arguments' in func:
                        print(f"     - Arguments type: {type(func['arguments'])}")
                        if isinstance(func['arguments'], str):
                            try:
                                parsed_args = json.loads(func['arguments'])
                                print(f"     - Arguments JSON valid: True")
                                print(f"     - Arguments content: {parsed_args}")
                            except json.JSONDecodeError as e:
                                print(f"     - Arguments JSON invalid: {e}")
                        else:
                            print(f"     - Arguments not string: {func['arguments']}")
                    else:
                        print(f"     - ❌ Function missing 'arguments' field!")
                
                # Check OpenAI compliance
                compliant = _validate_tool_call_compliance(call)
                print(f"     - OpenAI compliant: {compliant}")
        else:
            print("   ❌ No tool calls parsed from XML!")
    
    except Exception as e:
        print(f"   ❌ XML parsing failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # STEP 3: Test through tool handler pipeline
    print("🧪 STEP 2: Tool Handler Pipeline")
    print("-" * 40)
    
    # Create tools definition (matching what n8n would send)
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
    
    try:
        # Validate tools first
        validated_tools = validate_tool_definitions(tools_definition)
        print(f"   Tools validation: SUCCESS ({len(validated_tools)} tools)")
        
        # Create tool handler
        config = ToolCallingConfig()
        handler = ToolCallingHandler(config)
        
        # Parse tool calls using the same method the handler uses
        tool_calls = handler._parse_tool_calls_from_response(n8n_response_text, validated_tools)
        
        print(f"   Tool calls from handler: {len(tool_calls)}")
        
        if tool_calls:
            for i, call in enumerate(tool_calls):
                print(f"   Handler Call {i+1}:")
                print(f"     - ID: {call.id}")
                print(f"     - Function name: '{call.function_name}'")
                print(f"     - Function arguments: {call.function_arguments}")
                print(f"     - Full structure: {call.dict()}")
        else:
            print("   ❌ Handler produced no tool calls!")
            
    except Exception as e:
        print(f"   ❌ Tool handler pipeline failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # STEP 4: Test the specific code path that generates the warning
    print("🧪 STEP 3: Specific Warning Code Path")
    print("-" * 40)
    
    # This replicates the exact code from tool_handler.py:_parse_tool_calls_from_response
    try:
        from tool_schemas import parse_tool_calls_from_response
        tool_call_dicts = parse_tool_calls_from_response(n8n_response_text)
        
        print(f"   Raw tool call dicts: {len(tool_call_dicts)}")
        
        for i, call_dict in enumerate(tool_call_dicts):
            print(f"   Processing call_dict {i+1}: {json.dumps(call_dict, indent=4)}")
            
            # This is the exact code that triggers the warning
            function_name = call_dict.get('name', '')
            function_args = call_dict.get('arguments', {})
            
            print(f"     - Extracted function_name: '{function_name}'")
            print(f"     - Function name type: {type(function_name)}")
            print(f"     - Function name truthiness: {bool(function_name)}")
            print(f"     - Extracted function_args: {function_args}")
            
            # The problematic check that triggers the warning
            if not function_name:
                print(f"     - ❌ THIS TRIGGERS THE WARNING: function_name is falsy!")
                print(f"     - Function name repr: {repr(function_name)}")
                print(f"     - Function name bool: {bool(function_name)}")
            else:
                print(f"     - ✅ Function name is valid: '{function_name}'")
                
            # Check if the issue is in the call_dict structure
            print(f"     - call_dict keys: {list(call_dict.keys())}")
            if 'function' in call_dict:
                print(f"     - call_dict['function']: {call_dict['function']}")
                if isinstance(call_dict['function'], dict):
                    print(f"     - call_dict['function']['name']: {call_dict['function'].get('name', 'MISSING')}")
    
    except Exception as e:
        print(f"   ❌ Warning code path test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # STEP 5: Test different XML formats that might be problematic
    print("🧪 STEP 4: Alternative XML Formats")
    print("-" * 40)
    
    problematic_formats = [
        # Format 1: No array wrapper (single object)
        """<function_calls>{"name": "Research_Agent", "arguments": {"System_Message": "test"}}</function_calls>""",
        
        # Format 2: With extra whitespace
        """<function_calls>
        [
            {
                "name": "Research_Agent", 
                "arguments": {
                    "System_Message": "test"
                }
            }
        ]
        </function_calls>""",
        
        # Format 3: Nested function format (this might be the issue!)
        """<function_calls>[{"function": {"name": "Research_Agent", "arguments": {"System_Message": "test"}}}]</function_calls>""",
        
        # Format 4: OpenAI-style nested format
        """<function_calls>[{"id": "call_123", "type": "function", "function": {"name": "Research_Agent", "arguments": "{\"System_Message\": \"test\"}"}}]</function_calls>""",
    ]
    
    for i, format_text in enumerate(problematic_formats, 1):
        print(f"   Testing Format {i}:")
        print(f"     Format: {format_text[:100]}...")
        
        try:
            calls = parse_tool_calls_from_response(format_text)
            print(f"     Parsed: {len(calls)} calls")
            
            if calls:
                call = calls[0]
                has_name = 'function' in call and 'name' in call['function']
                name_value = call.get('function', {}).get('name', 'MISSING') if has_name else call.get('name', 'MISSING')
                print(f"     Function name: '{name_value}'")
                print(f"     Would trigger warning: {not name_value}")
            else:
                print(f"     No calls parsed")
                
        except Exception as e:
            print(f"     Parse error: {e}")
        
        print()
    
    print("=" * 80)
    print("DEBUGGING COMPLETE")
    
if __name__ == "__main__":
    test_exact_n8n_scenario()