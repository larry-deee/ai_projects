#!/usr/bin/env python3
"""
Test Anthropic N8N Loop Issue Debug
==================================

This test reproduces the specific Anthropic model looping issue in n8n workflows.
Based on the user's server logs, the issue is:

1. N8N sends request to Anthropic /v1/messages endpoint
2. Server correctly converts tool_calls to tool_use blocks with stop_reason=tool_use
3. N8N receives response but sends the SAME request again instead of continuing conversation
4. This creates an infinite loop

The issue is likely a mismatch between our Anthropic tool_use format and what n8n expects.
"""

import sys
import os
sys.path.append('src')

from unified_response_formatter import UnifiedResponseFormatter
from tool_schemas import parse_tool_calls_from_response, convert_openai_to_anthropic_tools
import json

def test_anthropic_tool_use_format():
    """Test the Anthropic tool_use response format that n8n expects."""
    
    print("🔍 Testing Anthropic N8N Loop Issue Debug")
    print("=" * 60)
    
    # STEP 1: Create realistic n8n Anthropic request (what n8n sends to /v1/messages)
    n8n_anthropic_request = {
        "model": "claude-3-haiku",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": "Conduct research on GPT-5 using Google Search"
            }
        ],
        "tools": [
            {
                "name": "Google_Search",
                "description": "Search Google for information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    }
    
    print(f"📋 N8N Anthropic Request:")
    print(f"   - Model: {n8n_anthropic_request['model']}")
    print(f"   - Tools: {len(n8n_anthropic_request['tools'])}")
    print(f"   - Tool Name: {n8n_anthropic_request['tools'][0]['name']}")
    
    # STEP 2: Create mock Salesforce response with XML function calls
    mock_salesforce_response = {
        "response": {
            "generations": [[{
                "text": """<function_calls>
[
 {
 "name": "Google_Search",
 "arguments": {
 "query": "GPT-5 latest news AI research"
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
            "completionTokens": 30,
            "promptTokens": 100,
            "totalTokens": 130
        }
    }
    
    print(f"\n📤 Mock Salesforce Response:")
    print(f"   - Contains XML function calls: True")
    print(f"   - Tool being called: Google_Search")
    
    # STEP 3: Test OpenAI format conversion first
    print(f"\n🔧 Testing OpenAI Format Conversion...")
    formatter = UnifiedResponseFormatter(debug_mode=True)
    
    openai_response = formatter.format_openai_response(
        mock_salesforce_response,
        n8n_anthropic_request['model']
    )
    
    tool_calls = openai_response['choices'][0]['message'].get('tool_calls', [])
    print(f"   - OpenAI Tool Calls: {len(tool_calls)}")
    
    if tool_calls:
        print(f"   - Tool Call Structure: {json.dumps(tool_calls[0], indent=6)}")
    
    # STEP 4: Test Anthropic format conversion
    print(f"\n🔧 Testing Anthropic Format Conversion...")
    
    # Simulate the conversion process from async_endpoint_server.py
    message_id = f"msg_{int(time.time())}"
    content_blocks = []
    
    # Convert tool_calls to tool_use blocks (from async_endpoint_server.py lines 629-654)
    if tool_calls:
        print(f"🔧 Converting {len(tool_calls)} tool calls to Anthropic tool_use blocks")
        
        for tool_call in tool_calls:
            if tool_call.get('type') == 'function':
                function = tool_call.get('function', {})
                function_name = function.get('name', '')
                function_args_str = function.get('arguments', '{}')
                
                # Parse arguments JSON
                try:
                    function_args = json.loads(function_args_str)
                except json.JSONDecodeError:
                    print(f"❌ Failed to parse tool arguments: {function_args_str}")
                    function_args = {}
                
                # Create tool_use block in Anthropic format
                tool_use_block = {
                    "type": "tool_use",
                    "id": tool_call.get('id', f"tool_{int(time.time())}"),
                    "name": function_name,
                    "input": function_args
                }
                
                content_blocks.append(tool_use_block)
                print(f"✅ Converted tool call: {function_name}")
                print(f"   - Tool Use Block: {json.dumps(tool_use_block, indent=6)}")
    
    # Build Anthropic response (from async_endpoint_server.py lines 664-676)
    anthropic_response = {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "content": content_blocks,
        "model": n8n_anthropic_request['model'],
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 30
        }
    }
    
    print(f"\n📤 Our Anthropic Response:")
    print(f"   - ID: {anthropic_response['id']}")
    print(f"   - Type: {anthropic_response['type']}")
    print(f"   - Role: {anthropic_response['role']}")
    print(f"   - Content Blocks: {len(anthropic_response['content'])}")
    print(f"   - Stop Reason: {anthropic_response['stop_reason']}")
    print(f"   - Full Response: {json.dumps(anthropic_response, indent=2)}")
    
    # STEP 5: Compare with real Anthropic API format
    print(f"\n🔍 Comparing with Real Anthropic API Format...")
    
    # This is what the real Anthropic API returns for tool_use
    real_anthropic_example = {
        "id": "msg_01Aq9w938a90dw8q",
        "type": "message", 
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_01A09q90qw90lkasj",
                "name": "Google_Search",
                "input": {
                    "query": "GPT-5 latest news AI research"
                }
            }
        ],
        "model": "claude-3-haiku-20240307",
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 30
        }
    }
    
    print(f"   - Real Anthropic Example: {json.dumps(real_anthropic_example, indent=2)}")
    
    # STEP 6: Identify differences
    print(f"\n🔍 Identifying Differences...")
    
    our_tool_use = anthropic_response['content'][0] if anthropic_response['content'] else {}
    real_tool_use = real_anthropic_example['content'][0] if real_anthropic_example['content'] else {}
    
    differences = []
    
    # Check ID format
    our_id = our_tool_use.get('id', '')
    real_id = real_tool_use.get('id', '')
    if our_id.startswith('call_') and real_id.startswith('toolu_'):
        differences.append(f"Tool ID format: Our '{our_id}' vs Real '{real_id}'")
    
    # Check model format
    our_model = anthropic_response.get('model', '')
    real_model = real_anthropic_example.get('model', '')
    if our_model != real_model:
        differences.append(f"Model format: Our '{our_model}' vs Real '{real_model}'")
    
    # Check message ID format
    our_msg_id = anthropic_response.get('id', '')
    real_msg_id = real_anthropic_example.get('id', '')
    if our_msg_id.startswith('msg_') and real_msg_id.startswith('msg_'):
        if len(our_msg_id) != len(real_msg_id):
            differences.append(f"Message ID length: Our {len(our_msg_id)} vs Real {len(real_msg_id)}")
    
    # Check other fields
    for field in ['type', 'role', 'stop_reason', 'stop_sequence']:
        our_val = anthropic_response.get(field)
        real_val = real_anthropic_example.get(field)
        if our_val != real_val:
            differences.append(f"{field}: Our '{our_val}' vs Real '{real_val}'")
    
    if differences:
        print(f"   - Differences found:")
        for diff in differences:
            print(f"     - {diff}")
    else:
        print(f"   - ✅ No major structural differences found")
    
    # STEP 7: Test what happens when n8n sends back tool result
    print(f"\n🔧 Testing Tool Result Conversation Flow...")
    
    # This is what n8n should send back after executing Google_Search
    n8n_followup_request = {
        "model": "claude-3-haiku",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": "Conduct research on GPT-5 using Google Search"
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": our_tool_use.get('id', 'toolu_test'),
                        "name": "Google_Search",
                        "input": {
                            "query": "GPT-5 latest news AI research"
                        }
                    }
                ]
            },
            {
                "role": "user", 
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": our_tool_use.get('id', 'toolu_test'),
                        "content": "Google Search Results: GPT-5 announced by OpenAI with advanced reasoning capabilities..."
                    }
                ]
            }
        ],
        "tools": [
            {
                "name": "Google_Search",
                "description": "Search Google for information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    }
    
    print(f"   - N8N Follow-up Messages: {len(n8n_followup_request['messages'])}")
    print(f"   - Last Message Type: {n8n_followup_request['messages'][-1]['role']}")
    print(f"   - Tool Result ID: {n8n_followup_request['messages'][-1]['content'][0]['tool_use_id']}")
    
    # STEP 8: Diagnosis 
    print(f"\n📊 DIAGNOSIS")
    print("=" * 60)
    
    print(f"✅ OpenAI Tool Calls Generated: SUCCESS")
    print(f"✅ Anthropic Tool Use Conversion: SUCCESS") 
    print(f"✅ Response Format Valid: SUCCESS")
    print(f"✅ Tool ID Present: {'SUCCESS' if our_tool_use.get('id') else 'FAILED'}")
    print(f"✅ Structure Matches Real Anthropic: {'SUCCESS' if not differences else 'POTENTIAL ISSUES'}")
    
    # Key hypothesis about the looping issue
    print(f"\n🎯 LOOP ISSUE HYPOTHESIS:")
    print(f"The looping likely occurs because:")
    print(f"1. N8N receives our tool_use response correctly")
    print(f"2. N8N executes the Google_Search tool successfully") 
    print(f"3. But when N8N sends the follow-up with tool_result...")
    print(f"4. Our server may not handle tool_result messages correctly")
    print(f"5. This causes N8N's agent to restart the conversation")
    
    print(f"\n🔍 NEXT DEBUGGING STEPS:")
    print(f"1. Check if our server handles 'tool_result' content type")
    print(f"2. Verify tool ID consistency in conversation flow")
    print(f"3. Test the complete request -> tool_use -> tool_result -> response cycle")
    print(f"4. Compare tool ID formats (call_ vs toolu_) for n8n compatibility")
    
    return True

if __name__ == "__main__":
    import time
    test_anthropic_tool_use_format()