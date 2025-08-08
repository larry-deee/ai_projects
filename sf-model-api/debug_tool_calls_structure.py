#!/usr/bin/env python3
"""
Debug Tool Calls Structure
==========================

Debug script to understand the structure of parsed tool calls.
"""

import json
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def debug_parsed_tool_calls():
    """Debug the structure of parsed tool calls."""
    try:
        from tool_schemas import parse_tool_calls_from_response
        
        # Test XML content
        xml_content = '''<function_calls>
[{"name": "research_agent", "arguments": {"q": "hello"}}]
</function_calls>'''
        
        print("Debugging tool calls structure...")
        print(f"Input: {xml_content}")
        
        # Parse tool calls
        tool_calls = parse_tool_calls_from_response(xml_content)
        
        print(f"Parsed tool calls count: {len(tool_calls)}")
        print(f"Type: {type(tool_calls)}")
        
        if tool_calls:
            for i, call in enumerate(tool_calls):
                print(f"\nTool call {i}:")
                print(f"  Type: {type(call)}")
                print(f"  Content: {call}")
                
                if isinstance(call, dict):
                    print("  Dictionary keys:", list(call.keys()))
                    for key, value in call.items():
                        print(f"    {key}: {value} (type: {type(value)})")
                else:
                    print(f"  Attributes: {dir(call)}")
                    if hasattr(call, 'function_name'):
                        print(f"    function_name: {call.function_name}")
                    if hasattr(call, 'function_arguments'):
                        print(f"    function_arguments: {call.function_arguments}")
                    if hasattr(call, 'id'):
                        print(f"    id: {call.id}")
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_parsed_tool_calls()