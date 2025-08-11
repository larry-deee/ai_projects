#!/usr/bin/env python3
"""
Debug XML Parsing Issues
========================

Investigate the specific XML parsing issue we found with single object format.
This might be the root cause of the n8n tool calling issue.
"""

import sys
import os
sys.path.append('src')

from tool_schemas import parse_tool_calls_from_response
import json

def test_xml_parsing_edge_cases():
    """Test XML parsing with various edge cases that might cause issues."""
    
    print("🔍 Testing XML Parsing Edge Cases")
    print("=" * 60)
    
    # Test Case 1: Valid array format (should work)
    xml_array = """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>"""
    
    # Test Case 2: Single object format (currently failing)
    xml_single = """<function_calls>
{
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
}
</function_calls>"""
    
    # Test Case 3: Multiple objects in array (should work)
    xml_multiple = """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "First message"
 }
 },
 {
 "name": "Another_Agent",
 "arguments": {
 "query": "Second message"
 }
 }
]
</function_calls>"""
    
    # Test Case 4: Compact format (might be what Salesforce returns)
    xml_compact = """<function_calls>[{"name":"Research_Agent","arguments":{"System_Message":"Test message"}}]</function_calls>"""
    
    # Test Case 5: With extra whitespace and formatting
    xml_formatted = """<function_calls>
    [
        {
            "name": "Research_Agent",
            "arguments": {
                "System_Message": "Test message with formatting"
            }
        }
    ]
</function_calls>"""
    
    # Test Case 6: Invalid JSON (edge case)
    xml_invalid = """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message",
 }
 }
]
</function_calls>"""
    
    test_cases = [
        ("Array format (standard)", xml_array),
        ("Single object format (problematic)", xml_single),
        ("Multiple objects in array", xml_multiple),
        ("Compact format", xml_compact),
        ("Formatted with whitespace", xml_formatted),
        ("Invalid JSON (trailing comma)", xml_invalid)
    ]
    
    results = []
    
    for name, xml_content in test_cases:
        print(f"\n🧪 Testing: {name}")
        print("-" * 40)
        print(f"XML Content: {xml_content[:100]}{'...' if len(xml_content) > 100 else ''}")
        
        try:
            tool_calls = parse_tool_calls_from_response(xml_content)
            success = len(tool_calls) > 0
            print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'} ({len(tool_calls)} tool calls)")
            
            if success:
                for i, call in enumerate(tool_calls):
                    print(f"  Tool Call {i+1}:")
                    print(f"    - ID: {call.get('id', 'missing')}")
                    print(f"    - Function: {call.get('function', {}).get('name', 'missing')}")
                    print(f"    - Arguments: {call.get('function', {}).get('arguments', 'missing')}")
            
            results.append((name, success, len(tool_calls)))
            
        except Exception as e:
            print(f"Result: ❌ ERROR - {str(e)}")
            results.append((name, False, 0))
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 40)
    
    for name, success, count in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name} ({count} calls)")
    
    # Identify the specific issue
    failing_cases = [name for name, success, count in results if not success]
    if failing_cases:
        print(f"\n🔧 FAILING CASES:")
        for case in failing_cases:
            print(f"   - {case}")
        
        print(f"\n💡 ANALYSIS:")
        if "Single object format (problematic)" in failing_cases:
            print("   - Single object format is not supported")
            print("   - This might be what Salesforce returns in some scenarios")
            print("   - Need to enhance XML parsing to handle single objects")
        
        if "Invalid JSON (trailing comma)" in failing_cases:
            print("   - JSON parsing is strict and doesn't handle trailing commas")
            print("   - Might need JSON cleanup before parsing")
    
    return len(failing_cases) == 0

def debug_parse_tool_calls_function():
    """Debug the internal workings of parse_tool_calls_from_response."""
    
    print(f"\n🔍 Debugging parse_tool_calls_from_response Function")
    print("=" * 60)
    
    # Test the problematic single object format
    xml_single = """<function_calls>
{
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
}
</function_calls>"""
    
    print(f"Testing single object format:")
    print(f"XML: {xml_single}")
    
    # Extract just the JSON part
    start_idx = xml_single.find('<function_calls>') + len('<function_calls>')
    end_idx = xml_single.find('</function_calls>')
    json_content = xml_single[start_idx:end_idx].strip()
    
    print(f"\nExtracted JSON content:")
    print(f"'{json_content}'")
    
    try:
        parsed = json.loads(json_content)
        print(f"\nJSON parsing result:")
        print(f"Type: {type(parsed)}")
        print(f"Content: {parsed}")
        
        if isinstance(parsed, dict):
            print(f"\n🔧 ISSUE IDENTIFIED: Parsed as dict, but parser expects list!")
            print(f"   - Parser assumes array format: [{{...}}]")
            print(f"   - But received single object format: {{...}}")
            print(f"   - Need to wrap single objects in array")
        
    except json.JSONDecodeError as e:
        print(f"\nJSON parsing failed: {e}")

def test_fixed_xml_parsing():
    """Test a potential fix for single object XML parsing."""
    
    print(f"\n🔧 Testing Potential Fix for Single Object XML")
    print("=" * 60)
    
    def parse_tool_calls_fixed(response_text: str):
        """Fixed version that handles both array and single object formats."""
        tool_calls = []
        
        # Extract XML content
        start_tag = "<function_calls>"
        end_tag = "</function_calls>"
        
        start_idx = response_text.find(start_tag)
        if start_idx == -1:
            return tool_calls
        
        end_idx = response_text.find(end_tag, start_idx)
        if end_idx == -1:
            return tool_calls
        
        json_content = response_text[start_idx + len(start_tag):end_idx].strip()
        
        try:
            parsed_calls = json.loads(json_content)
            
            # Handle both array and single object formats
            if isinstance(parsed_calls, list):
                calls_list = parsed_calls
            elif isinstance(parsed_calls, dict):
                # Wrap single object in array
                calls_list = [parsed_calls]
                print(f"   🔧 Wrapped single object in array")
            else:
                print(f"   ❌ Unexpected JSON type: {type(parsed_calls)}")
                return tool_calls
            
            # Convert to OpenAI format
            for i, call in enumerate(calls_list):
                if isinstance(call, dict) and 'name' in call:
                    from tool_schemas import create_tool_call_id
                    tool_call = {
                        "id": create_tool_call_id(),
                        "type": "function",
                        "function": {
                            "name": call['name'],
                            "arguments": json.dumps(call.get('arguments', {}))
                        }
                    }
                    tool_calls.append(tool_call)
                    
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parsing failed: {e}")
        
        return tool_calls
    
    # Test with both formats
    xml_array = """<function_calls>[{"name": "Test", "arguments": {"msg": "array"}}]</function_calls>"""
    xml_single = """<function_calls>{"name": "Test", "arguments": {"msg": "single"}}</function_calls>"""
    
    print(f"Testing array format:")
    calls1 = parse_tool_calls_fixed(xml_array)
    print(f"   Result: {len(calls1)} tool calls")
    
    print(f"\nTesting single object format:")
    calls2 = parse_tool_calls_fixed(xml_single)
    print(f"   Result: {len(calls2)} tool calls")
    
    if len(calls1) > 0 and len(calls2) > 0:
        print(f"\n✅ Fix works for both formats!")
        return True
    else:
        print(f"\n❌ Fix didn't work")
        return False

if __name__ == "__main__":
    basic_test = test_xml_parsing_edge_cases()
    debug_parse_tool_calls_function()
    fix_test = test_fixed_xml_parsing()
    
    print(f"\n{'='*60}")
    if basic_test:
        print("✅ All XML parsing edge cases work!")
    else:
        print("❌ Some XML parsing edge cases are failing!")
        if fix_test:
            print("✅ But the proposed fix resolves the issues!")
            print("💡 Need to implement the fix in tool_schemas.py")
        else:
            print("❌ The proposed fix also doesn't work")
    
    exit(0 if (basic_test or fix_test) else 1)