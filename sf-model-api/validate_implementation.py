#!/usr/bin/env python3
"""
Quick Implementation Validation
===============================

This script performs a quick validation of the Tool Behaviour Compatibility Layer
implementation without starting/stopping the server.

Usage:
    python validate_implementation.py
"""

import os
import sys
import requests
import json
import time

def check_server_health():
    """Check if server is running and healthy."""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Server is running and healthy")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        print("Please start the server with: ./start_async_service.sh")
        return False

def test_n8n_tool_preservation():
    """Test that n8n clients preserve tools."""
    print("\n🧪 Testing n8n tool preservation...")
    
    try:
        response = requests.post(
            'http://localhost:8000/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'openai/js 5.12.1'
            },
            json={
                "model": "sfdc_ai__DefaultGPT4Omni",
                "messages": [{"role": "user", "content": "Call research_agent with q=\"hello\""}],
                "tool_choice": "auto",
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "research_agent",
                        "parameters": {
                            "type": "object",
                            "properties": {"q": {"type": "string"}},
                            "required": ["q"]
                        }
                    }
                }]
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            message = data['choices'][0].get('message', {})
            has_tool_calls = 'tool_calls' in message
            content_empty = message.get('content', '') == ''
            finish_reason = data['choices'][0].get('finish_reason')
            
            if has_tool_calls and content_empty and finish_reason == 'tool_calls':
                print("✅ n8n tool preservation working correctly")
                print(f"   - Tool calls found: {len(message['tool_calls'])}")
                print(f"   - Content empty: {content_empty}")
                print(f"   - Finish reason: {finish_reason}")
                return True
            else:
                print("❌ n8n tool preservation not working")
                print(f"   - Has tool calls: {has_tool_calls}")
                print(f"   - Content empty: {content_empty}")
                print(f"   - Finish reason: {finish_reason}")
                return False
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_openai_format_consistency():
    """Test that responses are in consistent OpenAI format."""
    print("\n🧪 Testing OpenAI format consistency...")
    
    try:
        response = requests.post(
            'http://localhost:8000/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'TestClient/1.0'
            },
            json={
                "model": "claude-3-haiku",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check required OpenAI fields
            required_fields = ['id', 'object', 'created', 'model', 'choices', 'usage']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print("✅ OpenAI format consistency correct")
                print(f"   - Response ID: {data['id']}")
                print(f"   - Object type: {data['object']}")
                print(f"   - Model: {data['model']}")
                return True
            else:
                print(f"❌ Missing OpenAI fields: {missing_fields}")
                return False
        else:
            print(f"❌ Request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def check_environment_variables():
    """Check current environment variable configuration."""
    print("\n📋 Checking environment variables...")
    
    env_vars = {
        'N8N_COMPAT_MODE': os.environ.get('N8N_COMPAT_MODE', 'not_set'),
        'N8N_COMPAT_PRESERVE_TOOLS': os.environ.get('N8N_COMPAT_PRESERVE_TOOLS', 'not_set'),
        'OPENAI_NATIVE_TOOL_PASSTHROUGH': os.environ.get('OPENAI_NATIVE_TOOL_PASSTHROUGH', 'not_set'),
        'VERBOSE_TOOL_LOGS': os.environ.get('VERBOSE_TOOL_LOGS', 'not_set')
    }
    
    print("Current settings:")
    for var, value in env_vars.items():
        print(f"   {var}: {value}")
    
    # Check if key settings are enabled
    preserve_tools = env_vars.get('N8N_COMPAT_PRESERVE_TOOLS', '1') == '1'
    openai_passthrough = env_vars.get('OPENAI_NATIVE_TOOL_PASSTHROUGH', '1') == '1'
    
    if preserve_tools and openai_passthrough:
        print("✅ Key features enabled for Tool Behaviour Compatibility")
        return True
    else:
        print("⚠️ Some key features may be disabled")
        return False

def test_response_normalization():
    """Test response normalization with different clients."""
    print("\n🧪 Testing response normalization...")
    
    clients = [
        ("Standard", "MyApp/1.0"),
        ("n8n", "openai/js 5.12.1"),
        ("OpenAI", "openai-python/1.3.8")
    ]
    
    all_consistent = True
    
    for client_name, user_agent in clients:
        try:
            response = requests.post(
                'http://localhost:8000/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': user_agent
                },
                json={
                    "model": "claude-3-haiku",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 30
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'object', 'choices']
                has_all_fields = all(field in data for field in required_fields)
                
                if has_all_fields:
                    print(f"   ✅ {client_name} client: consistent format")
                else:
                    print(f"   ❌ {client_name} client: inconsistent format")
                    all_consistent = False
            else:
                print(f"   ❌ {client_name} client: request failed ({response.status_code})")
                all_consistent = False
                
        except Exception as e:
            print(f"   ❌ {client_name} client: error ({e})")
            all_consistent = False
    
    if all_consistent:
        print("✅ Response normalization working correctly")
    else:
        print("❌ Response normalization issues found")
    
    return all_consistent

def main():
    """Run quick validation tests."""
    print("🔍 Tool Behaviour Compatibility Layer - Quick Validation")
    print("=" * 60)
    
    # Track results
    tests = [
        ("Server Health", check_server_health),
        ("Environment Variables", check_environment_variables),
        ("n8n Tool Preservation", test_n8n_tool_preservation),
        ("OpenAI Format Consistency", test_openai_format_consistency),
        ("Response Normalization", test_response_normalization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n⚠️ Validation interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Validation Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} validations passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All validations passed!")
        print("✅ Tool Behaviour Compatibility Layer appears to be working correctly!")
        print("\n📋 Key behaviors confirmed:")
        print("   • Server is healthy and responding")
        print("   • Environment variables are configured")
        print("   • n8n clients preserve tools correctly") 
        print("   • OpenAI format consistency maintained")
        print("   • Response normalization working across clients")
        print("\n🚀 Ready for comprehensive testing with: python run_all_compatibility_tests.py")
        sys.exit(0)
    else:
        print(f"\n❌ {total - passed} validation(s) failed")
        print("Please check the issues above before running comprehensive tests")
        sys.exit(1)

if __name__ == "__main__":
    main()