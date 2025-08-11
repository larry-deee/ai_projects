#!/usr/bin/env python3
"""
Test N8N Tool Calling Issue Reproduction
========================================

This test reproduces the exact issue reported by the user where n8n tool calling 
worked before but is now broken after recent XML conversion changes.

The user reports:
- n8n sends requests with tools defined 
- Model returns XML function calls instead of proper OpenAI tool_calls format
- Real OpenAI API (gpt-5-mini) works but the gateway doesn't
- Tool calling worked before but broke after recent XML conversion changes

Test Strategy:
1. Create a realistic n8n-style request with tools
2. Mock a Salesforce response with XML function calls 
3. Test the entire pipeline through the unified formatter
4. Identify where the conversion is failing
"""

import sys
import os
sys.path.append('src')

from unified_response_formatter import UnifiedResponseFormatter
from tool_schemas import parse_tool_calls_from_response
from response_normaliser import normalise_assistant_tool_response
import json

def test_n8n_tool_calling_issue():
    """Test the complete n8n tool calling pipeline to identify the issue."""
    
    print("🔍 Testing N8N Tool Calling Issue Reproduction")
    print("=" * 60)
    
    # STEP 1: Create realistic n8n request with tools (similar to what n8n sends)
    n8n_request = {
        "model": "sfdc_ai__DefaultGPT4Omni",
        "messages": [
            {
                "role": "user", 
                "content": "Conduct evidence-first research on the latest news in AI and Generative AI, with a focus on GPT-5. Include findings, angles, keywords, and credible sources."
            }
        ],
        "tools": [
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
        ],
        "tool_choice": "auto"
    }
    
    print(f"📋 N8N Request Model: {n8n_request['model']}")
    print(f"📋 N8N Request Tools: {len(n8n_request['tools'])}")
    print(f"📋 N8N Request Tool Choice: {n8n_request['tool_choice']}")
    
    # STEP 2: Create mock Salesforce response that contains XML function calls
    # This simulates what Salesforce actually returns
    mock_salesforce_response = {
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
        },
        "model": "sfdc_ai__DefaultGPT4Omni"
    }
    
    print(f"\n📤 Mock Salesforce Response Structure:")
    print(f"   - Response path: response.generations[0][0].text")
    print(f"   - Contains XML: {'<function_calls>' in str(mock_salesforce_response)}")
    print(f"   - Model: {mock_salesforce_response.get('model', 'not specified')}")
    
    # STEP 3: Test the unified response formatter 
    print(f"\n🧪 Testing Unified Response Formatter...")
    formatter = UnifiedResponseFormatter(debug_mode=True)
    
    # Test response text extraction first
    print(f"\n🔍 Testing Response Text Extraction...")
    extraction_result = formatter.extract_response_text(mock_salesforce_response)  
    print(f"   - Extraction Success: {extraction_result.success}")
    print(f"   - Extraction Path: {extraction_result.extraction_path}")
    if extraction_result.text:
        print(f"   - Extracted Text Length: {len(extraction_result.text)}")
        print(f"   - Contains XML: {'<function_calls>' in extraction_result.text}")
        if len(extraction_result.text) < 500:
            print(f"   - Full Text: {extraction_result.text}")
    else:
        print(f"   - No text extracted!")
    
    # Test tool call extraction
    print(f"\n🔍 Testing Tool Call Extraction...")
    tool_calls = formatter.extract_tool_calls(mock_salesforce_response)
    print(f"   - Tool Calls Extracted: {len(tool_calls)}")
    
    if tool_calls:
        for i, call in enumerate(tool_calls):
            print(f"   - Tool Call {i+1}:")
            print(f"     - ID: {call.get('id', 'missing')}")
            print(f"     - Type: {call.get('type', 'missing')}")
            print(f"     - Function Name: {call.get('function', {}).get('name', 'missing')}")
            print(f"     - Function Args: {call.get('function', {}).get('arguments', 'missing')}")
            
            # Validate OpenAI compliance
            is_compliant = (
                'id' in call and
                'type' in call and call['type'] == 'function' and
                'function' in call and
                'name' in call['function'] and
                'arguments' in call['function'] and
                isinstance(call['function']['arguments'], str)
            )
            print(f"     - OpenAI Compliant: {is_compliant}")
    else:
        print(f"   - ❌ No tool calls extracted!")
    
    # STEP 4: Test full OpenAI response formatting
    print(f"\n🔧 Testing Full OpenAI Response Formatting...")
    openai_response = formatter.format_openai_response(
        mock_salesforce_response, 
        n8n_request['model'],
        request_context={"tools": n8n_request['tools']}
    )
    
    print(f"   - Response ID: {openai_response.get('id', 'missing')}")
    print(f"   - Response Object: {openai_response.get('object', 'missing')}")
    print(f"   - Response Model: {openai_response.get('model', 'missing')}")
    
    if 'choices' in openai_response and openai_response['choices']:
        choice = openai_response['choices'][0]
        message = choice.get('message', {})
        
        print(f"   - Message Role: {message.get('role', 'missing')}")
        print(f"   - Message Content: '{message.get('content', 'missing')}'")
        print(f"   - Finish Reason: {choice.get('finish_reason', 'missing')}")
        
        if 'tool_calls' in message:
            print(f"   - Tool Calls Count: {len(message['tool_calls'])}")
            print(f"   - ✅ SUCCESS: tool_calls field present")
            
            # Validate each tool call
            for i, call in enumerate(message['tool_calls']):
                print(f"     - Tool Call {i+1} Structure: {json.dumps(call, indent=8)}")
        else:
            print(f"   - ❌ FAILURE: No tool_calls field in message")
            print(f"   - Message keys: {list(message.keys())}")
    else:
        print(f"   - ❌ FAILURE: No choices in response")
        print(f"   - Response keys: {list(openai_response.keys())}")
    
    # STEP 5: Test direct XML parsing (what should work)
    print(f"\n🔍 Testing Direct XML Parsing...")
    if extraction_result.text and '<function_calls>' in extraction_result.text:
        try:
            direct_tool_calls = parse_tool_calls_from_response(extraction_result.text)
            print(f"   - Direct XML Parsing: {len(direct_tool_calls)} tool calls")
            
            if direct_tool_calls:
                for i, call in enumerate(direct_tool_calls):
                    print(f"     - Direct Tool Call {i+1}: {json.dumps(call, indent=8)}")
            else:
                print(f"   - ❌ Direct XML parsing failed!")
        except Exception as e:
            print(f"   - ❌ Direct XML parsing error: {e}")
    
    # STEP 6: Test response normalization
    print(f"\n🔧 Testing Response Normalization...")
    if 'choices' in openai_response and openai_response['choices']:
        message = openai_response['choices'][0]['message']
        tool_calls = message.get('tool_calls', [])
        
        try:
            normalized_message = normalise_assistant_tool_response(
                message, tool_calls, "tool_calls" if tool_calls else "stop"
            )
            print(f"   - Normalization Success: True")
            print(f"   - Normalized Message Keys: {list(normalized_message.keys())}")
            print(f"   - Normalized Content: '{normalized_message.get('content', 'missing')}'")
            
            if 'tool_calls' in normalized_message:
                print(f"   - Normalized Tool Calls: {len(normalized_message['tool_calls'])}")
            else:
                print(f"   - ❌ No tool_calls in normalized message")
                
        except Exception as e:
            print(f"   - ❌ Normalization error: {e}")
    
    # STEP 7: Summary and diagnosis
    print(f"\n📊 DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    extraction_success = extraction_result.success and extraction_result.text
    xml_detected = extraction_success and '<function_calls>' in extraction_result.text
    tool_calls_extracted = len(tool_calls) > 0
    openai_response_valid = 'choices' in openai_response and len(openai_response['choices']) > 0
    has_tool_calls_field = (
        openai_response_valid and 
        'tool_calls' in openai_response['choices'][0].get('message', {})
    )
    
    print(f"✅ Response Text Extraction: {'SUCCESS' if extraction_success else 'FAILED'}")
    print(f"✅ XML Function Calls Detected: {'SUCCESS' if xml_detected else 'FAILED'}")
    print(f"✅ Tool Calls Parsed from XML: {'SUCCESS' if tool_calls_extracted else 'FAILED'}")
    print(f"✅ OpenAI Response Generated: {'SUCCESS' if openai_response_valid else 'FAILED'}")
    print(f"✅ Tool Calls Field Present: {'SUCCESS' if has_tool_calls_field else 'FAILED'}")
    
    overall_success = all([
        extraction_success,
        xml_detected, 
        tool_calls_extracted,
        openai_response_valid,
        has_tool_calls_field
    ])
    
    print(f"\n🎯 OVERALL RESULT: {'SUCCESS - N8N should work' if overall_success else 'FAILURE - Issue identified'}")
    
    if not overall_success:
        print(f"\n🔧 ISSUES IDENTIFIED:")
        if not extraction_success:
            print(f"   - Response text extraction failed")
        if not xml_detected:
            print(f"   - XML function calls not detected in response")
        if not tool_calls_extracted:
            print(f"   - XML parsing did not produce tool calls")
        if not openai_response_valid:
            print(f"   - OpenAI response generation failed")
        if not has_tool_calls_field:
            print(f"   - tool_calls field missing from final response")
    
    return overall_success

if __name__ == "__main__":
    success = test_n8n_tool_calling_issue()
    print(f"\n{'='*60}")
    if success:
        print("✅ N8N tool calling pipeline is working correctly!")
    else:
        print("❌ N8N tool calling pipeline has issues that need to be fixed")
    
    exit(0 if success else 1)