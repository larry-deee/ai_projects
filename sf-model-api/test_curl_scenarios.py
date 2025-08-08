#!/usr/bin/env python3
"""
cURL Test Scenarios for Tool Behaviour Compatibility Layer
==========================================================

This script generates and executes the specific cURL commands mentioned
in the test requirements to validate tool preservation behavior.

Test Scenarios:
A) Tool Call with n8n Client (Tool Preservation)
B) Tool Result Round-Trip (Follow-up)
C) Environment Variable Testing
"""

import subprocess
import json
import sys
import os
import time

def run_curl_command(curl_cmd, description=""):
    """Execute a cURL command and return parsed JSON response."""
    print(f"\n🧪 {description}")
    print("=" * 60)
    print(f"Command: {' '.join(curl_cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                print("✅ Response received:")
                print(json.dumps(response_data, indent=2))
                return response_data
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Raw response: {result.stdout}")
                return None
        else:
            print(f"❌ cURL command failed with return code: {result.returncode}")
            print(f"Error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ Request timed out after 30 seconds")
        return None
    except Exception as e:
        print(f"❌ Error executing command: {e}")
        return None

def test_a_tool_call_n8n_client():
    """Test A: Tool Call with n8n Client (Tool Preservation)."""
    curl_cmd = [
        'curl', '-s', 'http://localhost:8000/v1/chat/completions',
        '-H', 'Content-Type: application/json',
        '-H', 'User-Agent: openai/js 5.12.1',
        '-d', json.dumps({
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Call research_agent with q=\"hello\""}],
            "tool_choice": "auto",
            "tools": [{
                "type": "function",
                "function": {
                    "name": "research_agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "q": {"type": "string"}
                        },
                        "required": ["q"]
                    }
                }
            }]
        })
    ]
    
    response = run_curl_command(curl_cmd, "Test A: Tool Call with n8n Client")
    
    if response:
        # Validation
        has_tool_calls = 'choices' in response and response['choices'] and 'tool_calls' in response['choices'][0].get('message', {})
        
        print("\n📊 Validation Results:")
        print(f"   Has tool_calls: {has_tool_calls}")
        
        if has_tool_calls:
            message = response['choices'][0]['message']
            tool_calls = message['tool_calls']
            content = message.get('content', '')
            finish_reason = response['choices'][0].get('finish_reason')
            
            print(f"   Tool calls count: {len(tool_calls)}")
            print(f"   Content empty: {content == ''}")
            print(f"   Finish reason: {finish_reason}")
            
            if len(tool_calls) > 0 and content == '' and finish_reason == 'tool_calls':
                print("✅ PASS: Tools preserved, content empty, proper finish reason")
                return True
            else:
                print("❌ FAIL: Tool preservation behavior incorrect")
                return False
        else:
            print("❌ FAIL: No tool calls found - tools were not preserved")
            return False
    else:
        print("❌ FAIL: No response received")
        return False

def test_b_tool_result_round_trip():
    """Test B: Tool Result Round-Trip (Follow-up)."""
    curl_cmd = [
        'curl', '-s', 'http://localhost:8000/v1/chat/completions',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [
                {"role": "user", "content": "Call research_agent with q=\"hello\""},
                {
                    "role": "assistant", 
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "research_agent",
                            "arguments": json.dumps({"q": "hello"})
                        }
                    }]
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": json.dumps({"summary": "done"})
                }
            ]
        })
    ]
    
    response = run_curl_command(curl_cmd, "Test B: Tool Result Round-Trip")
    
    if response:
        # Validation
        print("\n📊 Validation Results:")
        
        if 'choices' in response and response['choices']:
            message = response['choices'][0].get('message', {})
            finish_reason = response['choices'][0].get('finish_reason')
            content = message.get('content', '')
            
            print(f"   Content: {content}")
            print(f"   Finish reason: {finish_reason}")
            
            if finish_reason == "stop" and content:
                print("✅ PASS: Normal assistant response with stop finish reason")
                return True
            else:
                print("❌ FAIL: Invalid follow-up response")
                return False
        else:
            print("❌ FAIL: Invalid response structure")
            return False
    else:
        print("❌ FAIL: No response received")
        return False

def test_c_environment_variable_testing():
    """Test C: Environment Variable Testing."""
    print("\n🧪 Test C: Environment Variable Testing")
    print("=" * 60)
    
    # Display current environment variables
    env_vars = {
        'N8N_COMPAT_MODE': os.environ.get('N8N_COMPAT_MODE', 'not_set'),
        'N8N_COMPAT_PRESERVE_TOOLS': os.environ.get('N8N_COMPAT_PRESERVE_TOOLS', 'not_set'),
        'OPENAI_NATIVE_TOOL_PASSTHROUGH': os.environ.get('OPENAI_NATIVE_TOOL_PASSTHROUGH', 'not_set')
    }
    
    print("Current Environment Variables:")
    for var, value in env_vars.items():
        print(f"   {var}: {value}")
    
    print("\n📋 Note: Environment variable changes require server restart")
    print("To test different configurations:")
    print("1. Stop the server (Ctrl+C)")
    print("2. Set environment variables:")
    print("   export N8N_COMPAT_PRESERVE_TOOLS=0")
    print("   export OPENAI_NATIVE_TOOL_PASSTHROUGH=0")
    print("3. Restart server: ./start_async_service.sh")
    print("4. Run these tests again")
    
    # Test current behavior matches environment settings
    preserve_tools = env_vars.get('N8N_COMPAT_PRESERVE_TOOLS', '1') == '1'
    
    if preserve_tools:
        print("\n🔄 Testing current behavior (tools should be preserved)...")
        return test_a_tool_call_n8n_client()
    else:
        print("\n🔄 Testing current behavior (tools should be ignored)...")
        # Test that tools are ignored when preservation is disabled
        response = run_curl_command([
            'curl', '-s', 'http://localhost:8000/v1/chat/completions',
            '-H', 'Content-Type: application/json',
            '-H', 'User-Agent: openai/js 5.12.1',
            '-d', json.dumps({
                "model": "claude-3-haiku",
                "messages": [{"role": "user", "content": "Call research_agent with q=\"hello\""}],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "research_agent",
                        "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}
                    }
                }]
            })
        ], "Testing tool ignoring behavior")
        
        if response:
            has_tool_calls = 'choices' in response and 'tool_calls' in response['choices'][0].get('message', {})
            if not has_tool_calls:
                print("✅ PASS: Tools correctly ignored when N8N_COMPAT_PRESERVE_TOOLS=0")
                return True
            else:
                print("❌ FAIL: Tools were not ignored despite N8N_COMPAT_PRESERVE_TOOLS=0")
                return False
        
        return False

def validate_server_logs():
    """Check server logs for expected messages."""
    print("\n🔍 Validating Server Logs")
    print("=" * 60)
    
    expected_log_messages = [
        "🔧 N8N compat: tools PRESERVED",
        "🔧 Tool routing:",
        "OpenAI-native model passthrough"
    ]
    
    print("Expected log messages to look for in server output:")
    for msg in expected_log_messages:
        print(f"   • {msg}")
    
    print("\n📝 To check server logs:")
    print("   1. Look at the terminal where you started the server")
    print("   2. Look for the expected messages above")
    print("   3. Ensure NO 'ignoring tools' messages appear")

def main():
    """Execute all cURL test scenarios."""
    print("🚀 cURL Test Scenarios for Tool Behaviour Compatibility Layer")
    print("=============================================================")
    
    # Check if server is running
    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code != 200:
            print("❌ Server health check failed")
            sys.exit(1)
        print("✅ Server is healthy and ready for testing\n")
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        print("Please ensure the server is running with: ./start_async_service.sh")
        sys.exit(1)
    
    # Run test scenarios
    results = []
    
    print("\n" + "=" * 80)
    results.append(("Test A: n8n Tool Preservation", test_a_tool_call_n8n_client()))
    
    print("\n" + "=" * 80)
    results.append(("Test B: Tool Round-Trip", test_b_tool_result_round_trip()))
    
    print("\n" + "=" * 80)
    results.append(("Test C: Environment Variables", test_c_environment_variable_testing()))
    
    # Validate logs
    print("\n" + "=" * 80)
    validate_server_logs()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All cURL tests passed successfully!")
        print("✅ Tool Behaviour Compatibility Layer is working correctly!")
        sys.exit(0)
    else:
        print(f"\n❌ {len(results) - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()