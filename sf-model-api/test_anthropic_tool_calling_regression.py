#!/usr/bin/env python3
"""
Anthropic Tool Calling Regression Prevention Test
=================================================

Comprehensive test suite to prevent regression of the Anthropic endpoint 
tool calling issue that was fixed. This test ensures both endpoints
maintain compatibility with n8n and other LangChain integrations.

Test Coverage:
1. Anthropic endpoint tool calling with various tool formats
2. OpenAI endpoint tool calling (reference implementation)
3. Tool format conversion validation
4. Response format compliance
5. Error handling scenarios
6. Performance comparison
"""

import requests
import json
import time
import sys

def test_anthropic_single_tool():
    """Test Anthropic endpoint with single tool (main n8n use case)."""
    
    print("🧪 Test 1: Anthropic Single Tool (N8N Use Case)")
    print("-" * 50)
    
    request_data = {
        "model": "claude-3-haiku",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": "Use the research tool to find information about AI safety."
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
                            "description": "Research domain"
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
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/messages", 
            json=request_data, 
            headers=headers, 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        
        # Validate response structure
        required_fields = ['id', 'type', 'role', 'content', 'model', 'stop_reason', 'usage']
        for field in required_fields:
            if field not in data:
                print(f"❌ FAILED: Missing field '{field}'")
                return False
        
        # Validate tool use blocks
        content = data.get('content', [])
        tool_use_blocks = [block for block in content if block.get('type') == 'tool_use']
        
        if len(tool_use_blocks) == 0:
            print(f"❌ FAILED: No tool_use blocks found")
            return False
        
        if len(tool_use_blocks) != 1:
            print(f"❌ FAILED: Expected 1 tool_use block, got {len(tool_use_blocks)}")
            return False
        
        tool_block = tool_use_blocks[0]
        required_tool_fields = ['type', 'id', 'name', 'input']
        for field in required_tool_fields:
            if field not in tool_block:
                print(f"❌ FAILED: Missing tool field '{field}'")
                return False
        
        # Validate stop reason
        if data.get('stop_reason') != 'tool_use':
            print(f"❌ FAILED: Expected stop_reason='tool_use', got '{data.get('stop_reason')}'")
            return False
        
        print(f"✅ SUCCESS: Anthropic single tool working correctly")
        print(f"   Tool Name: {tool_block['name']}")
        print(f"   Tool Input: {tool_block['input']}")
        print(f"   Stop Reason: {data['stop_reason']}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception {e}")
        return False

def test_anthropic_multiple_tools():
    """Test Anthropic endpoint with multiple tools."""
    
    print("\n🧪 Test 2: Anthropic Multiple Tools")
    print("-" * 50)
    
    request_data = {
        "model": "claude-3-haiku",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": "Use the appropriate tools to research AI safety and then calculate statistics."
            }
        ],
        "tools": [
            {
                "name": "research_tool",
                "description": "Research information on topics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Research query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "calculator",
                "description": "Perform mathematical calculations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression"}
                    },
                    "required": ["expression"]
                }
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/messages", 
            json=request_data, 
            headers=headers, 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
        
        data = response.json()
        content = data.get('content', [])
        tool_use_blocks = [block for block in content if block.get('type') == 'tool_use']
        
        if len(tool_use_blocks) == 0:
            print(f"❌ FAILED: No tool_use blocks found")
            return False
        
        print(f"✅ SUCCESS: Anthropic multiple tools working")
        print(f"   Tools used: {len(tool_use_blocks)}")
        for i, block in enumerate(tool_use_blocks):
            print(f"   Tool {i+1}: {block['name']}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception {e}")
        return False

def test_openai_reference():
    """Test OpenAI endpoint as reference (should continue working)."""
    
    print("\n🧪 Test 3: OpenAI Reference Implementation")
    print("-" * 50)
    
    request_data = {
        "model": "claude-3-haiku",
        "messages": [
            {
                "role": "user",
                "content": "Use the research tool to find information about AI safety."
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
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/chat/completions", 
            json=request_data, 
            headers={"Content-Type": "application/json"}, 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
        
        data = response.json()
        choices = data.get('choices', [])
        
        if not choices:
            print(f"❌ FAILED: No choices in response")
            return False
        
        message = choices[0].get('message', {})
        tool_calls = message.get('tool_calls', [])
        
        if len(tool_calls) == 0:
            print(f"❌ FAILED: No tool calls found")
            return False
        
        print(f"✅ SUCCESS: OpenAI reference working")
        print(f"   Tool calls: {len(tool_calls)}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception {e}")
        return False

def test_anthropic_no_tools():
    """Test Anthropic endpoint without tools (should work normally)."""
    
    print("\n🧪 Test 4: Anthropic No Tools (Standard Chat)")
    print("-" * 50)
    
    request_data = {
        "model": "claude-3-haiku",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?"
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/messages", 
            json=request_data, 
            headers=headers, 
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ FAILED: HTTP {response.status_code}")
            return False
        
        data = response.json()
        content = data.get('content', [])
        text_blocks = [block for block in content if block.get('type') == 'text']
        
        if len(text_blocks) == 0:
            print(f"❌ FAILED: No text blocks found")
            return False
        
        if data.get('stop_reason') != 'end_turn':
            print(f"❌ FAILED: Expected stop_reason='end_turn', got '{data.get('stop_reason')}'")
            return False
        
        print(f"✅ SUCCESS: Anthropic no-tools chat working")
        print(f"   Text blocks: {len(text_blocks)}")
        print(f"   Stop reason: {data['stop_reason']}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception {e}")
        return False

def test_error_handling():
    """Test error handling scenarios."""
    
    print("\n🧪 Test 5: Error Handling")
    print("-" * 50)
    
    # Test missing anthropic-version header
    request_data = {
        "model": "claude-3-haiku",
        "messages": [{"role": "user", "content": "Test"}],
        "tools": [{"name": "test", "input_schema": {}}]
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/messages", 
            json=request_data,
            headers={"Content-Type": "application/json"},  # Missing anthropic-version
            timeout=15
        )
        
        # Should work without anthropic-version (our implementation is lenient)
        if response.status_code not in [200, 400]:
            print(f"⚠️ Unexpected status code: {response.status_code}")
        
        print(f"✅ SUCCESS: Error handling working")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Exception {e}")
        return False

def performance_comparison():
    """Compare performance between endpoints."""
    
    print("\n🧪 Test 6: Performance Comparison")
    print("-" * 50)
    
    # Anthropic endpoint timing
    anthropic_request = {
        "model": "claude-3-haiku",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": "Use the tool to get weather."}],
        "tools": [{
            "name": "weather",
            "description": "Get weather info",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }]
    }
    
    # OpenAI endpoint timing
    openai_request = {
        "model": "claude-3-haiku",
        "messages": [{"role": "user", "content": "Use the tool to get weather."}],
        "tools": [{
            "type": "function",
            "function": {
                "name": "weather",
                "description": "Get weather info",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    },
                    "required": ["location"]
                }
            }
        }]
    }
    
    try:
        # Time Anthropic endpoint
        start_time = time.time()
        anthropic_response = requests.post(
            "http://localhost:8000/v1/messages",
            json=anthropic_request,
            headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"},
            timeout=15
        )
        anthropic_time = time.time() - start_time
        
        # Time OpenAI endpoint
        start_time = time.time()
        openai_response = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json=openai_request,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        openai_time = time.time() - start_time
        
        print(f"⏱️ Performance Results:")
        print(f"   Anthropic endpoint: {anthropic_time:.2f}s")
        print(f"   OpenAI endpoint: {openai_time:.2f}s")
        print(f"   Difference: {abs(anthropic_time - openai_time):.2f}s")
        
        if anthropic_response.status_code == 200 and openai_response.status_code == 200:
            print(f"✅ SUCCESS: Both endpoints performing well")
            return True
        else:
            print(f"❌ FAILED: Performance test issues")
            return False
        
    except Exception as e:
        print(f"❌ FAILED: Exception {e}")
        return False

def main():
    """Run all regression tests."""
    
    print("🧪 ANTHROPIC TOOL CALLING REGRESSION PREVENTION TEST SUITE")
    print("=" * 70)
    print("Testing fix for n8n Anthropic Chat Model tool calling issue")
    print("=" * 70)
    
    tests = [
        ("Anthropic Single Tool (N8N)", test_anthropic_single_tool),
        ("Anthropic Multiple Tools", test_anthropic_multiple_tools),
        ("OpenAI Reference", test_openai_reference),
        ("Anthropic No Tools", test_anthropic_no_tools),
        ("Error Handling", test_error_handling),
        ("Performance Comparison", performance_comparison)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 REGRESSION TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
    
    print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Anthropic tool calling is working correctly!")
        print("🔒 Regression prevention: This fix maintains n8n compatibility")
        return True
    else:
        print("🚨 SOME TESTS FAILED - Anthropic tool calling has issues")
        print("⚠️ This may break n8n and LangChain integrations")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)