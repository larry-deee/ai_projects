#\!/usr/bin/env python3
"""
Anthropic Endpoint Fixes Validation Script
==========================================

Validates that all critical Anthropic endpoint issues have been resolved:
1. 404 errors on /anthropic/v1/messages
2. 500 errors on /v1/messages with metadata fetch failures  
3. Model mapping issues with claude-3-haiku-20240307
4. N8N credential validation failures

This script tests both base URLs and endpoints that n8n uses.
"""

import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
ANTHROPIC_HEADERS = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01"
}

def test_endpoint(name, method, url, headers=None, data=None, expected_status=200):
    """Test an endpoint and return success status and response"""
    print(f"🧪 Testing {name}...")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=15)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        success = response.status_code == expected_status
        status_icon = "✅" if success else "❌"
        print(f"   {status_icon} Status: {response.status_code} (expected {expected_status})")
        
        if success and response.text:
            try:
                json_response = response.json()
                print(f"   📄 Response type: {type(json_response).__name__}")
                if isinstance(json_response, dict):
                    if 'id' in json_response:
                        print(f"   🆔 Response ID: {json_response['id']}")
                    if 'model' in json_response:
                        print(f"   🤖 Model: {json_response['model']}")
                    if 'data' in json_response and isinstance(json_response['data'], list):
                        print(f"   📊 Data items: {len(json_response['data'])}")
            except:
                print(f"   📄 Response length: {len(response.text)} chars")
        
        return success, response
        
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout after 15 seconds")
        return False, None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, None

def main():
    """Run comprehensive validation tests"""
    print("🚀 Anthropic Endpoint Fixes Validation")
    print("=" * 60)
    print("Testing critical endpoints that were failing...")
    print()
    
    tests = []
    
    # Test 1: Base URL validation (n8n credential test)
    success, _ = test_endpoint(
        "Base URL Health Check", 
        "GET", 
        f"{BASE_URL}/health"
    )
    tests.append(("Base URL connectivity", success))
    print()
    
    # Test 2: /anthropic/v1/messages endpoint (was returning 404)
    success, response = test_endpoint(
        "/anthropic/v1/messages endpoint (was 404)",
        "POST",
        f"{BASE_URL}/anthropic/v1/messages", 
        headers=ANTHROPIC_HEADERS,
        data={
            "model": "claude-3-haiku-20240307",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    tests.append(("Anthropic v1 messages endpoint", success))
    print()
    
    # Test 3: /v1/messages endpoint with model mapping (was returning 500)
    success, response = test_endpoint(
        "/v1/messages with claude-3-haiku-20240307 (was 500)",
        "POST", 
        f"{BASE_URL}/v1/messages",
        headers=ANTHROPIC_HEADERS,
        data={
            "model": "claude-3-haiku-20240307", 
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Test"}]
        }
    )
    tests.append(("Direct v1 messages with model mapping", success))
    print()
    
    # Test 4: /anthropic/v1/models endpoint (n8n model validation)
    success, response = test_endpoint(
        "/anthropic/v1/models endpoint (n8n validation)",
        "GET",
        f"{BASE_URL}/anthropic/v1/models",
        headers={"anthropic-version": "2023-06-01"}
    )
    tests.append(("Anthropic models endpoint", success))
    
    if success and response:
        try:
            models_data = response.json()
            if 'data' in models_data:
                model_ids = [model.get('id', 'unknown') for model in models_data['data']]
                print(f"   📋 Available models: {', '.join(model_ids)}")
                claude_haiku_available = 'claude-3-haiku-20240307' in model_ids
                print(f"   🎯 claude-3-haiku-20240307 available: {'✅' if claude_haiku_available else '❌'}")
        except:
            pass
    print()
    
    # Test 5: Different model name formats
    other_models = [
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229", 
        "claude-3-5-sonnet-latest"
    ]
    
    for model in other_models:
        success, _ = test_endpoint(
            f"Model mapping: {model}",
            "POST",
            f"{BASE_URL}/v1/messages",
            headers=ANTHROPIC_HEADERS, 
            data={
                "model": model,
                "max_tokens": 20,
                "messages": [{"role": "user", "content": "Hi"}]
            }
        )
        tests.append((f"Model mapping {model}", success))
        print()
    
    # Summary
    print("=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print()
    print(f"📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED\!")
        print("✅ N8N credential validation should now work")
        print("✅ Anthropic endpoints are fully functional") 
        print("✅ Model mapping issues resolved")
        print("✅ 404 and 500 errors fixed")
        return True
    else:
        print("⚠️  Some tests failed - issues remain")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)