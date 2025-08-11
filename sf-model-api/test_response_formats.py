#!/usr/bin/env python3
"""
Test Different Salesforce Response Formats
==========================================

Since the basic XML parsing is working, the issue might be with different
response formats that Salesforce returns. Let's test various possible formats
to identify which one is causing the n8n issue.
"""

import sys
import os
sys.path.append('src')

from unified_response_formatter import UnifiedResponseFormatter
import json

def test_different_response_formats():
    """Test various Salesforce response formats to identify the problematic one."""
    
    print("🔍 Testing Different Salesforce Response Formats")
    print("=" * 60)
    
    formatter = UnifiedResponseFormatter(debug_mode=True)
    
    # Format 1: The working format from our previous test
    format1 = {
        "response": {
            "generations": [[{
                "text": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>""",
                "generationInfo": {"finish_reason": "stop"}
            }]]
        },
        "tokenUsageEstimate": {"completionTokens": 64, "promptTokens": 499, "totalTokens": 563}
    }
    
    # Format 2: Direct generations format (without response wrapper)
    format2 = {
        "generations": [[{
            "text": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>""",
            "generationInfo": {"finish_reason": "stop"}
        }]],
        "tokenUsageEstimate": {"completionTokens": 64, "promptTokens": 499, "totalTokens": 563}
    }
    
    # Format 3: Generation object format (single level)
    format3 = {
        "generation": {
            "generatedText": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>"""
        },
        "tokenUsageEstimate": {"completionTokens": 64, "promptTokens": 499, "totalTokens": 563}
    }
    
    # Format 4: Generation text format
    format4 = {
        "generation": {
            "text": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>"""
        },
        "tokenUsageEstimate": {"completionTokens": 64, "promptTokens": 499, "totalTokens": 563}
    }
    
    # Format 5: OpenAI-like pre-formatted response (might bypass XML parsing)
    format5 = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>"""
            },
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 499, "completion_tokens": 64, "total_tokens": 563}
    }
    
    # Format 6: Malformed XML (possible edge case)
    format6 = {
        "generation": {
            "generatedText": """<function_calls>
[
 {
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
 }
]
</function_calls>

Additional text after XML that might cause issues."""
        },
        "tokenUsageEstimate": {"completionTokens": 64, "promptTokens": 499, "totalTokens": 563}
    }
    
    # Format 7: XML without proper array formatting
    format7 = {
        "generation": {
            "generatedText": """<function_calls>
{
 "name": "Research_Agent",
 "arguments": {
 "System_Message": "Test message"
 }
}
</function_calls>"""
        },
        "tokenUsageEstimate": {"completionTokens": 64, "promptTokens": 499, "totalTokens": 563}
    }
    
    formats_to_test = [
        ("Format 1: response.generations[0][0].text (working)", format1),
        ("Format 2: generations[0][0].text (direct)", format2), 
        ("Format 3: generation.generatedText", format3),
        ("Format 4: generation.text", format4),
        ("Format 5: OpenAI-like pre-formatted", format5),
        ("Format 6: XML with trailing text", format6),
        ("Format 7: XML single object (not array)", format7)
    ]
    
    results = []
    
    for name, response_format in formats_to_test:
        print(f"\n🧪 Testing {name}")
        print("-" * 50)
        
        try:
            # Test text extraction
            extraction_result = formatter.extract_response_text(response_format)
            print(f"   📝 Text Extraction: {'✅ SUCCESS' if extraction_result.success else '❌ FAILED'}")
            if extraction_result.success:
                print(f"       Path: {extraction_result.extraction_path}")
                has_xml = '<function_calls>' in (extraction_result.text or '')
                print(f"       Has XML: {'✅ YES' if has_xml else '❌ NO'}")
            
            # Test tool call extraction
            tool_calls = formatter.extract_tool_calls(response_format)
            print(f"   🔧 Tool Calls: {'✅ SUCCESS' if len(tool_calls) > 0 else '❌ FAILED'} ({len(tool_calls)} found)")
            
            # Test full response formatting
            openai_response = formatter.format_openai_response(response_format, "test-model")
            has_tool_calls_field = (
                'choices' in openai_response and 
                len(openai_response['choices']) > 0 and
                'tool_calls' in openai_response['choices'][0].get('message', {})
            )
            print(f"   📤 OpenAI Response: {'✅ SUCCESS' if has_tool_calls_field else '❌ FAILED'}")
            
            overall_success = extraction_result.success and len(tool_calls) > 0 and has_tool_calls_field
            results.append((name, overall_success))
            
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            results.append((name, False))
    
    # Display summary
    print(f"\n📊 SUMMARY OF RESULTS")
    print("=" * 60)
    
    working_formats = []
    broken_formats = []
    
    for name, success in results:
        if success:
            working_formats.append(name)
            print(f"✅ {name}")
        else:
            broken_formats.append(name)
            print(f"❌ {name}")
    
    print(f"\n🎯 ANALYSIS:")
    print(f"   - Working formats: {len(working_formats)}")
    print(f"   - Broken formats: {len(broken_formats)}")
    
    if broken_formats:
        print(f"\n🔧 POTENTIAL ISSUES:")
        for broken in broken_formats:
            print(f"   - {broken}")
        print(f"\n💡 The user's n8n issue might be caused by one of these broken formats.")
    else:
        print(f"\n✅ All formats work correctly. The issue might be elsewhere in the pipeline.")
    
    return len(broken_formats) == 0

def test_streaming_vs_non_streaming():
    """Test if the issue is related to streaming vs non-streaming responses."""
    
    print(f"\n🔍 Testing Streaming vs Non-Streaming Response Handling")
    print("=" * 60)
    
    formatter = UnifiedResponseFormatter(debug_mode=True)
    
    # Non-streaming response (what we've been testing)
    non_streaming = {
        "generation": {
            "generatedText": """<function_calls>
[{"name": "Research_Agent", "arguments": {"System_Message": "Test"}}]
</function_calls>"""
        }
    }
    
    # Simulated streaming response format (chunks)
    streaming_chunks = [
        {"choices": [{"delta": {"content": "<function"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "_calls>\n["}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": '{"name": "Research_Agent"'}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": ', "arguments": {"System_Message": "Test"}}]'}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "\n</function_calls>"}, "finish_reason": "tool_calls"}]}
    ]
    
    print(f"📝 Non-streaming response test:")
    tool_calls = formatter.extract_tool_calls(non_streaming)
    print(f"   Tool calls extracted: {len(tool_calls)}")
    
    print(f"\n📝 Streaming response test:")
    # Reconstruct content from streaming chunks
    full_content = ""
    for chunk in streaming_chunks:
        if 'choices' in chunk and chunk['choices'] and 'delta' in chunk['choices'][0]:
            content = chunk['choices'][0]['delta'].get('content', '')
            full_content += content
    
    streaming_response = {"generation": {"generatedText": full_content}}
    tool_calls = formatter.extract_tool_calls(streaming_response)
    print(f"   Reconstructed content: {full_content}")
    print(f"   Tool calls extracted: {len(tool_calls)}")

if __name__ == "__main__":
    success1 = test_different_response_formats()
    test_streaming_vs_non_streaming()
    
    print(f"\n{'='*60}")
    if success1:
        print("✅ All response formats work correctly!")
        print("💡 The n8n issue might be in the request handling or a different edge case.")
    else:
        print("❌ Some response formats are failing!")
        print("💡 The n8n issue is likely caused by one of the failing formats.")
    
    exit(0 if success1 else 1)