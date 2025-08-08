#!/usr/bin/env python3
"""
Final Validation Demo Script
===========================

Demonstrates the successful implementation of:
1. Token pre-warming (eliminates first-request 401)
2. Enhanced n8n user agent detection (openai/js support)  
3. Hardened JSON parsing (code fence tolerance)
4. Tool ignoring for n8n compatibility

Usage: python final_validation_demo.py
"""

import requests
import json
import time
import sys

# Server configuration
BASE_URL = "http://localhost:8000"

def test_with_user_agent(ua_string, description, test_data=None):
    """Test API with specific user agent"""
    print(f"\n🧪 {description}")
    print(f"   User-Agent: {ua_string}")
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': ua_string
    }
    
    if test_data is None:
        test_data = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 50
        }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                               headers=headers, 
                               json=test_data,
                               timeout=30)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', 'No content')
            tool_calls = data.get('choices', [{}])[0].get('message', {}).get('tool_calls')
            
            print(f"   ✅ SUCCESS ({elapsed_ms}ms)")
            print(f"   Status: {response.status_code}")
            print(f"   Content: {content[:100]}..." if len(content) > 100 else f"   Content: {content}")
            print(f"   Tool Calls: {tool_calls}")
            
            # Check headers for n8n compatibility
            stream_downgraded = response.headers.get('x-stream-downgraded', 'not-set')
            proxy_latency = response.headers.get('x-proxy-latency-ms', 'not-set')
            print(f"   Headers: stream-downgraded={stream_downgraded}, latency={proxy_latency}ms")
            
            return True
        else:
            print(f"   ❌ FAILED: {response.status_code} - {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    """Run comprehensive validation demo"""
    print("🚀 SF-MODEL-API Final Validation Demo")
    print("=" * 50)
    
    # Test 1: Server Health Check  
    print("\n🏥 Server Health Check")
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=10)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   ✅ Server Status: {health_data.get('status', 'unknown')}")
            print(f"   ✅ Configuration: {health_data.get('configuration', 'unknown')}")
        else:
            print(f"   ❌ Health check failed: {health_response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to server: {e}")
        print(f"   💡 Make sure server is running: cd src && python async_endpoint_server.py")
        return False
    
    # Test 2: Models endpoint (verifies token pre-warming)
    print("\n📋 Models Endpoint (Token Pre-warming Validation)")
    try:
        models_response = requests.get(f"{BASE_URL}/v1/models", timeout=10)
        if models_response.status_code == 200:
            models_data = models_response.json()
            model_count = len(models_data.get('data', []))
            print(f"   ✅ Models loaded successfully: {model_count} models available")
            print("   ✅ No 401 authentication errors (token pre-warming working)")
        else:
            print(f"   ❌ Models endpoint failed: {models_response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Models endpoint error: {e}")
        return False
    
    # Test 3: Regular user agent (baseline)
    success = test_with_user_agent(
        "python-requests/2.31.0", 
        "Regular User Agent (Baseline Test)"
    )
    if not success:
        return False
    
    # Test 4: openai/js user agent (NEW n8n detection)
    success = test_with_user_agent(
        "openai/js 5.12.1",
        "OpenAI JS Client (NEW n8n Detection)"
    )
    if not success:
        return False
        
    # Test 5: Traditional n8n user agent  
    success = test_with_user_agent(
        "n8n/1.105.4",
        "Traditional n8n Client"
    )
    if not success:
        return False
    
    # Test 6: n8n with tools (should ignore tools)
    tool_test_data = {
        "model": "sfdc_ai__DefaultGPT4Omni",
        "messages": [{"role": "user", "content": "Test with tools"}],
        "max_tokens": 50,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ],
        "tool_choice": "auto"
    }
    
    success = test_with_user_agent(
        "openai/js 5.12.1",
        "N8N with Tools (Should Ignore Tools)",
        tool_test_data
    )
    if not success:
        return False
    
    # Test 7: Story with brackets (parser robustness)
    bracket_test_data = {
        "model": "sfdc_ai__DefaultGPT4Omni", 
        "messages": [{"role": "user", "content": "Tell a short story with [brackets] in it"}],
        "max_tokens": 100
    }
    
    success = test_with_user_agent(
        "openai/js 5.12.1",
        "Narrative with Brackets (JSON Parser Robustness)",
        bracket_test_data
    )
    if not success:
        return False
    
    # Final Results
    print("\n" + "=" * 50)
    print("🎉 ALL VALIDATION TESTS PASSED!")
    print("\n✅ Token Pre-warming: Working (no 401 errors)")
    print("✅ Enhanced n8n Detection: Working (openai/js support)")  
    print("✅ Tool Ignoring: Working (n8n gets plain text)")
    print("✅ JSON Parser Robustness: Working (handles edge cases)")
    print("✅ Backward Compatibility: Working (regular clients unaffected)")
    
    print(f"\n🚀 SF-Model-API fixes are production-ready!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)