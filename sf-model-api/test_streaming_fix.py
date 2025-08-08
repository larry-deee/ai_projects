#!/usr/bin/env python3
"""
Test script to verify streaming endpoints work after content extraction fix
"""
import asyncio
import json
import requests
import time
import threading
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import server components for local testing
from async_endpoint_server import app

def test_server_running():
    """Test if the server is reachable"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def test_openai_non_streaming():
    """Test OpenAI non-streaming endpoint"""
    print("Testing OpenAI non-streaming...")
    
    data = {
        "model": "claude-3-haiku",
        "messages": [
            {"role": "user", "content": "Say 'Hello World'"}
        ],
        "max_tokens": 50,
        "temperature": 0.1,
        "stream": False
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/v1/chat/completions',
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and result['choices']:
                content = result['choices'][0]['message']['content']
                print(f"✅ SUCCESS: Non-streaming response: '{content[:100]}...'")
                return True
            else:
                print(f"❌ FAILED: Invalid response structure: {result}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}: {response.text}")
        
    except Exception as e:
        print(f"❌ FAILED: Exception during non-streaming test: {e}")
    
    return False

def test_openai_streaming():
    """Test OpenAI streaming endpoint"""
    print("Testing OpenAI streaming...")
    
    data = {
        "model": "claude-3-haiku", 
        "messages": [
            {"role": "user", "content": "Count from 1 to 5"}
        ],
        "max_tokens": 100,
        "temperature": 0.1,
        "stream": True
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/v1/chat/completions',
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            chunks_received = 0
            content_pieces = []
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_content = line_str[6:]  # Remove 'data: '
                        if data_content == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data_content)
                            if 'choices' in chunk and chunk['choices']:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content_pieces.append(delta['content'])
                                    chunks_received += 1
                        except json.JSONDecodeError:
                            continue
            
            if chunks_received > 0:
                full_content = ''.join(content_pieces)
                print(f"✅ SUCCESS: Streaming received {chunks_received} chunks: '{full_content[:100]}...'")
                return True
            else:
                print(f"❌ FAILED: No content chunks received")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}: {response.text}")
        
    except Exception as e:
        print(f"❌ FAILED: Exception during streaming test: {e}")
    
    return False

def test_anthropic_streaming():
    """Test Anthropic streaming endpoint"""
    print("Testing Anthropic streaming...")
    
    data = {
        "model": "claude-3-haiku",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
        "max_tokens": 50,
        "temperature": 0.1,
        "stream": True
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/v1/messages',
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30,
            stream=True
        )
        
        if response.status_code == 200:
            events_received = 0
            content_pieces = []
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('event: ') or line_str.startswith('data: '):
                        events_received += 1
                        if line_str.startswith('data: '):
                            try:
                                data_content = line_str[6:]
                                event_data = json.loads(data_content)
                                if event_data.get('type') == 'content_block_delta':
                                    delta = event_data.get('delta', {})
                                    if 'text' in delta:
                                        content_pieces.append(delta['text'])
                            except json.JSONDecodeError:
                                continue
            
            if events_received > 0:
                full_content = ''.join(content_pieces)
                print(f"✅ SUCCESS: Anthropic streaming received {events_received} events: '{full_content[:100]}...'")
                return True
            else:
                print(f"❌ FAILED: No events received")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}: {response.text}")
        
    except Exception as e:
        print(f"❌ FAILED: Exception during Anthropic streaming test: {e}")
    
    return False

def run_all_tests():
    """Run all tests"""
    print("=== Streaming Fix Verification Tests ===")
    print()
    
    if not test_server_running():
        print("❌ Server is not running on localhost:8000")
        print("Please start the server first: python src/async_endpoint_server.py")
        return False
    
    print("✅ Server is running and reachable")
    print()
    
    results = []
    results.append(test_openai_non_streaming())
    results.append(test_openai_streaming()) 
    results.append(test_anthropic_streaming())
    
    print()
    print("=== Results Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Content extraction fix is working!")
        return True
    else:
        print("⚠️  Some tests failed - investigation needed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)