#!/usr/bin/env python3
"""
Test script to validate chat-generations endpoint migration.
Tests OpenAI and Anthropic API compatibility after migration.
"""

import requests
import time
import sys

# Configuration
BASE_URL = "http://localhost:8080"
TEST_API_KEY = "test-api-key"  # Replace with actual API key if needed

def test_openai_compatibility():
    """Test OpenAI /v1/chat/completions endpoint compatibility."""
    print("🔍 Testing OpenAI compatibility...")
    
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_API_KEY}"
    }
    
    payload = {
        "model": "claude-3-haiku",
        "messages": [
            {"role": "user", "content": "Say 'Hello from chat-generations!' in exactly those words."}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"✅ OpenAI endpoint working - Response time: {end_time - start_time:.2f}s")
            print(f"   Response: {content[:100]}...")
            return True
        else:
            print(f"❌ OpenAI endpoint failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ OpenAI endpoint error: {e}")
        return False

def test_anthropic_compatibility():
    """Test Anthropic /v1/messages endpoint compatibility."""
    print("🔍 Testing Anthropic compatibility...")
    
    url = f"{BASE_URL}/v1/messages"  
    headers = {
        "Content-Type": "application/json",
        "x-api-key": TEST_API_KEY
    }
    
    payload = {
        "model": "claude-3-haiku",
        "messages": [
            {"role": "user", "content": "Say 'Hello from chat-generations!' in exactly those words."}
        ],
        "max_tokens": 50
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('content', [{}])[0].get('text', '')
            print(f"✅ Anthropic endpoint working - Response time: {end_time - start_time:.2f}s")
            print(f"   Response: {content[:100]}...")
            return True
        else:
            print(f"❌ Anthropic endpoint failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Anthropic endpoint error: {e}")
        return False

def test_multi_turn_conversation():
    """Test multi-turn conversation handling."""
    print("🔍 Testing multi-turn conversation...")
    
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_API_KEY}"
    }
    
    payload = {
        "model": "claude-3-haiku",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Be concise."},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4."},
            {"role": "user", "content": "What about 3+3?"}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"✅ Multi-turn conversation working - Response time: {end_time - start_time:.2f}s")
            print(f"   Response: {content[:100]}...")
            return True
        else:
            print(f"❌ Multi-turn conversation failed - Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Multi-turn conversation error: {e}")
        return False

def test_service_availability():
    """Test if the service is running."""
    print("🔍 Testing service availability...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Service is running")
            return True
        else:
            print(f"❌ Service health check failed - Status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Service not available: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting chat-generations endpoint migration tests...\n")
    
    tests = [
        ("Service Availability", test_service_availability),
        ("OpenAI Compatibility", test_openai_compatibility), 
        ("Anthropic Compatibility", test_anthropic_compatibility),
        ("Multi-turn Conversation", test_multi_turn_conversation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
        print("-" * 50)
    
    # Summary
    print("\n🏁 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Chat-generations migration successful.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Review the migration implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()