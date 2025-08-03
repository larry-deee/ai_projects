#!/usr/bin/env python3
"""
Test script for Salesforce Models API Gateway endpoints
Tests both OpenAI and Anthropic compatibility
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, endpoint, data=None, expect_status=200):
    """Test an endpoint and return the result."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expect_status:
            print(f"✅ {method} {endpoint} - Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                try:
                    resp_json = response.json()
                    print(f"   Response: {json.dumps(resp_json, indent=2)[:200]}...")
                except:
                    print(f"   Response: {response.text[:200]}...")
            return True
        else:
            print(f"❌ {method} {endpoint} - Expected: {expect_status}, Got: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return False

def main():
    """Run endpoint tests."""
    print("🚀 Testing Salesforce Models API Gateway Endpoints")
    print("=" * 60)
    
    tests = [
        # Basic endpoints
        ("GET", "/", None, 200),
        ("GET", "/health", None, 200),
        ("GET", "/v1/models", None, 200),
        
        # OpenAI endpoint documentation
        ("GET", "/v1/chat/completions", None, 200),
        
        # Test Anthropic messages endpoint (should exist now)
        ("GET", "/v1/messages", None, 405),  # GET not allowed, but should not be 404
        
        # Test problematic endpoints that caused original issues
        ("POST", "/v1/v1/messages", {"messages": []}, 404),  # Should still be 404 (double path)
        ("GET", "/v1/messages", None, 405),  # Should be 405 (method not allowed) not 404
    ]
    
    passed = 0
    failed = 0
    
    for method, endpoint, data, expected_status in tests:
        if test_endpoint(method, endpoint, data, expected_status):
            passed += 1
        else:
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed! The gateway is properly configured.")
        print("\n🔗 Claude Code Configuration:")
        print(f"   Base URL: {BASE_URL}")
        print(f"   Messages endpoint: {BASE_URL}/v1/messages")
        print(f"   Chat completions endpoint: {BASE_URL}/v1/chat/completions")
    else:
        print("❌ Some tests failed. Check server configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()