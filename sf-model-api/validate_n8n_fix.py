#!/usr/bin/env python3
"""
N8N Tool Calling Validation Script
==================================

Simple validation script to test that your n8n tool calling issue is resolved.
Run this script to verify the XML parsing fix is working correctly.
"""

import sys
import os
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from tool_schemas import parse_tool_calls_from_response, _validate_tool_call_compliance
except ImportError:
    print("❌ Error: Could not import tool_schemas module")
    print("   Make sure you're running this from the project root directory")
    sys.exit(1)

def test_n8n_fix():
    """Test the n8n XML parsing fix"""
    print("🔧 Testing n8n XML Function Call Parsing Fix...")
    print("=" * 60)
    
    # Test the problematic single object format
    test_response = \"""
    I'll help you with that request.
    
    <function_calls>
    {
        "name": "Research_Agent",
        "arguments": {
            "topic": "machine learning",
            "depth": "detailed",
            "sources": ["academic", "industry", "news"]
        }
    }
    </function_calls>
    
    Let me search for information on this topic.
    \"""
    
    try:
        # Parse the response
        parsed_calls = parse_tool_calls_from_response(test_response)
        
        if len(parsed_calls) == 0:
            print("❌ FAILED: No tool calls were parsed")
            return False
        
        if len(parsed_calls) != 1:
            print(f"❌ FAILED: Expected 1 tool call, got {len(parsed_calls)}")
            return False
        
        call = parsed_calls[0]
        
        # Verify OpenAI compliance
        if not _validate_tool_call_compliance(call):
            print("❌ FAILED: Tool call is not OpenAI compliant")
            return False
        
        # Verify function details
        if call['function']['name'] != 'Research_Agent':
            print(f"❌ FAILED: Expected function name 'Research_Agent', got '{call['function']['name']}'")
            return False
        
        # Verify arguments
        args = json.loads(call['function']['arguments'])
        if args.get('topic') != 'machine learning':
            print(f"❌ FAILED: Expected topic 'machine learning', got '{args.get('topic')}'")
            return False
        
        print("✅ SUCCESS: XML parsing fix is working correctly!")
        print(f"   - Function: {call['function']['name']}")
        print(f"   - Call ID: {call['id']}")
        print(f"   - Arguments: {len(args)} parameters parsed")
        print(f"   - OpenAI Compliant: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception occurred: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_n8n_fix()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Your n8n tool calling issue has been RESOLVED!")
        print("   The XML parsing fix is working correctly.")
        print("   You can now use single object XML function calls in n8n.")
    else:
        print("🚨 The n8n tool calling issue is NOT resolved.")
        print("   Please check the error messages above.")
    
    sys.exit(0 if success else 1)
