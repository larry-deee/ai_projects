#!/usr/bin/env python3
"""
Test XML Function Call Detection Fix
====================================

Tests the enhanced unified formatter's ability to detect and convert
XML function calls to OpenAI tool_calls format.
"""

import sys
import os
sys.path.append('src')

from unified_response_formatter import UnifiedResponseFormatter

def test_xml_function_call_detection():
    """Test XML function call detection and conversion."""
    
    # Mock Salesforce response with XML function calls (like your example)
    mock_sf_response = {
        "response": {
            "generations": [[{
                "text": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Conduct evidence-first research on the latest news in AI and Generative AI, with a focus on GPT-5. Include findings, angles, keywords, and credible sources."
 }
 }
]
</function_calls>""",
                "generationInfo": {
                    "finish_reason": "stop"
                }
            }]]
        },
        "tokenUsageEstimate": {
            "completionTokens": 64,
            "promptTokens": 499,
            "totalTokens": 563
        }
    }
    
    # Test the formatter
    formatter = UnifiedResponseFormatter()
    
    print("🧪 Testing XML function call detection...")
    
    # Test tool call extraction
    tool_calls = formatter.extract_tool_calls(mock_sf_response)
    print(f"📊 Extracted {len(tool_calls)} tool calls")
    
    if tool_calls:
        print("✅ Tool calls detected successfully!")
        for i, call in enumerate(tool_calls):
            print(f"   {i+1}. {call.get('function', {}).get('name', 'Unknown')}")
    else:
        print("❌ No tool calls detected")
    
    # Test full OpenAI response formatting
    print("\n🔧 Testing full OpenAI response formatting...")
    openai_response = formatter.format_openai_response(mock_sf_response, "claude-3-haiku")
    
    if 'choices' in openai_response and openai_response['choices']:
        message = openai_response['choices'][0].get('message', {})
        if 'tool_calls' in message:
            print(f"✅ OpenAI response has tool_calls: {len(message['tool_calls'])}")
            print(f"✅ Finish reason: {openai_response['choices'][0].get('finish_reason')}")
        else:
            print("❌ OpenAI response missing tool_calls")
            print(f"Content: {message.get('content', '')[:100]}...")
    else:
        print("❌ Invalid OpenAI response structure")
    
    return len(tool_calls) > 0

if __name__ == "__main__":
    success = test_xml_function_call_detection()
    if success:
        print("\n✅ XML function call detection fix is working!")
    else:
        print("\n❌ XML function call detection fix needs more work")
    
    exit(0 if success else 1)