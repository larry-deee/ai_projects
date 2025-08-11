#!/usr/bin/env python3
"""
Test Anthropic Endpoint Tool Calling Issue
==========================================

This test specifically targets the Anthropic endpoint (/v1/messages) to identify
why tool calling works with OpenAI endpoint but not with Anthropic endpoint.

The user reports:
- n8n workflow using Anthropic Chat Model (@n8n/n8n-nodes-langchain.lmChatAnthropic) doesn't call tools
- Same workflow works with OpenAI endpoint but fails with Anthropic endpoint
- Server logs show HTTP 200 but no tool calling activity
- Large response size suggests content returned but tools not triggered
"""

import requests
import json
import time

def test_anthropic_endpoint_tool_calling():
    """Test the Anthropic endpoint /v1/messages with tool calling."""
    
    print("🔍 Testing Anthropic Endpoint Tool Calling")
    print("=" * 60)
    
    # Test the /v1/messages endpoint (Anthropic format)
    anthropic_url = "http://localhost:8000/v1/messages"
    
    # Create a request similar to what n8n would send
    anthropic_request = {
        "model": "claude-3-haiku",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": "Use the research tool to find information about GPT-5 developments."
            }
        ],
        "tools": [
            {
                "name": "research_tool",
                "description": "Tool for conducting research on various topics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The research query"
                        },
                        "domain": {
                            "type": "string", 
                            "description": "Research domain (tech, science, etc.)"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    print(f"🚀 Making request to Anthropic endpoint...")
    print(f"   URL: {anthropic_url}")
    print(f"   Model: {anthropic_request['model']}")
    print(f"   Tools: {len(anthropic_request['tools'])}")
    print(f"   Headers: {headers}")
    
    try:
        start_time = time.time()
        response = requests.post(anthropic_url, json=anthropic_request, headers=headers, timeout=30)
        response_time = time.time() - start_time
        
        print(f"\n📊 Response Analysis:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
        print(f"   Response Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"\n🔍 Response Structure Analysis:")
                print(f"   Response Type: {response_data.get('type', 'Not specified')}")
                print(f"   Response ID: {response_data.get('id', 'Not specified')}")
                print(f"   Model: {response_data.get('model', 'Not specified')}")
                print(f"   Role: {response_data.get('role', 'Not specified')}")
                print(f"   Stop Reason: {response_data.get('stop_reason', 'Not specified')}")
                
                # Check content
                content = response_data.get('content', [])
                print(f"   Content Blocks: {len(content)}")
                
                if content:
                    for i, block in enumerate(content):
                        block_type = block.get('type', 'unknown')
                        print(f"     Block {i+1}: type={block_type}")
                        
                        if block_type == 'text':
                            text = block.get('text', '')
                            print(f"              text_length={len(text)}")
                            # Check if text contains tool calls
                            if 'function_calls' in text or 'tool_use' in text:
                                print(f"              ⚠️ Contains tool indicators in text!")
                                print(f"              Text preview: {text[:200]}...")
                        elif block_type == 'tool_use':
                            tool_name = block.get('name', 'unknown')
                            tool_input = block.get('input', {})
                            print(f"              ✅ TOOL USE BLOCK FOUND!")
                            print(f"              tool_name={tool_name}")
                            print(f"              tool_input={tool_input}")
                
                # Check usage
                usage = response_data.get('usage', {})
                if usage:
                    print(f"   Usage:")
                    print(f"     Input tokens: {usage.get('input_tokens', 0)}")
                    print(f"     Output tokens: {usage.get('output_tokens', 0)}")
                
                # Determine if tool calling worked
                has_tool_use_blocks = any(
                    block.get('type') == 'tool_use' 
                    for block in content
                )
                
                has_tool_indicators_in_text = any(
                    block.get('type') == 'text' and 
                    ('function_calls' in block.get('text', '') or 'tool_use' in block.get('text', ''))
                    for block in content
                )
                
                print(f"\n🎯 Tool Calling Analysis:")
                print(f"   Has tool_use blocks: {'✅ YES' if has_tool_use_blocks else '❌ NO'}")
                print(f"   Has tool indicators in text: {'⚠️ YES' if has_tool_indicators_in_text else '❌ NO'}")
                
                if has_tool_use_blocks:
                    print(f"   🎉 SUCCESS: Anthropic endpoint properly triggered tool calling!")
                    return True
                elif has_tool_indicators_in_text:
                    print(f"   ⚠️ PARTIAL: Tool calls found in text but not in proper tool_use blocks")
                    print(f"   This suggests a response formatting issue")
                    return False
                else:
                    print(f"   ❌ FAILURE: No tool calling activity detected")
                    print(f"   This is the reported issue - tools are not being triggered")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"   ❌ Invalid JSON response: {e}")
                print(f"   Raw response: {response.text[:500]}...")
                return False
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Error response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False

def test_openai_endpoint_comparison():
    """Test the OpenAI endpoint for comparison."""
    
    print(f"\n🔍 Testing OpenAI Endpoint for Comparison")
    print("=" * 60)
    
    # Test the /v1/chat/completions endpoint (OpenAI format)
    openai_url = "http://localhost:8000/v1/chat/completions"
    
    # Create equivalent OpenAI request
    openai_request = {
        "model": "claude-3-haiku",
        "messages": [
            {
                "role": "user",
                "content": "Use the research tool to find information about GPT-5 developments."
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "research_tool",
                    "description": "Tool for conducting research on various topics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The research query"
                            },
                            "domain": {
                                "type": "string",
                                "description": "Research domain (tech, science, etc.)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"🚀 Making request to OpenAI endpoint...")
    print(f"   URL: {openai_url}")
    print(f"   Model: {openai_request['model']}")
    print(f"   Tools: {len(openai_request['tools'])}")
    
    try:
        start_time = time.time()
        response = requests.post(openai_url, json=openai_request, headers=headers, timeout=30)
        response_time = time.time() - start_time
        
        print(f"\n📊 Response Analysis:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response_time:.2f}s")
        print(f"   Response Size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"\n🔍 Response Structure Analysis:")
                print(f"   Response ID: {response_data.get('id', 'Not specified')}")
                print(f"   Object: {response_data.get('object', 'Not specified')}")
                print(f"   Model: {response_data.get('model', 'Not specified')}")
                
                choices = response_data.get('choices', [])
                print(f"   Choices: {len(choices)}")
                
                if choices:
                    choice = choices[0]
                    message = choice.get('message', {})
                    finish_reason = choice.get('finish_reason', 'unknown')
                    
                    print(f"   Message Role: {message.get('role', 'unknown')}")
                    print(f"   Finish Reason: {finish_reason}")
                    
                    # Check for tool calls
                    tool_calls = message.get('tool_calls', [])
                    content = message.get('content', '')
                    
                    print(f"   Tool Calls: {len(tool_calls)}")
                    print(f"   Content Length: {len(content) if content else 0}")
                    
                    if tool_calls:
                        print(f"   ✅ SUCCESS: OpenAI endpoint triggered {len(tool_calls)} tool calls!")
                        for i, call in enumerate(tool_calls):
                            print(f"     Tool Call {i+1}:")
                            print(f"       ID: {call.get('id', 'unknown')}")
                            print(f"       Type: {call.get('type', 'unknown')}")
                            function = call.get('function', {})
                            print(f"       Function: {function.get('name', 'unknown')}")
                            print(f"       Arguments: {function.get('arguments', 'none')}")
                        return True
                    else:
                        print(f"   ❌ FAILURE: No tool calls in OpenAI response")
                        if content:
                            print(f"   Content preview: {content[:200]}...")
                        return False
                        
            except json.JSONDecodeError as e:
                print(f"   ❌ Invalid JSON response: {e}")
                return False
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Error response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Anthropic vs OpenAI Endpoint Tool Calling Comparison")
    print("="*70)
    
    # Test both endpoints
    anthropic_success = test_anthropic_endpoint_tool_calling()
    openai_success = test_openai_endpoint_comparison()
    
    print(f"\n" + "="*70)
    print(f"📊 FINAL COMPARISON RESULTS:")
    print(f"   Anthropic Endpoint (/v1/messages): {'✅ WORKING' if anthropic_success else '❌ NOT WORKING'}")
    print(f"   OpenAI Endpoint (/v1/chat/completions): {'✅ WORKING' if openai_success else '❌ NOT WORKING'}")
    
    if not anthropic_success and openai_success:
        print(f"\n🎯 ISSUE CONFIRMED: Anthropic endpoint doesn't trigger tools but OpenAI does!")
        print(f"   This matches the reported n8n issue.")
    elif anthropic_success and openai_success:
        print(f"\n✅ Both endpoints are working - issue may be elsewhere")
    elif not anthropic_success and not openai_success:
        print(f"\n⚠️ Both endpoints failing - server configuration issue")
    else:
        print(f"\n🤔 Unexpected result pattern - needs investigation")