#!/usr/bin/env python3
"""
Anthropic Native Pass-Through Demo
==================================

Demonstration script for the Anthropic native pass-through adapter.
Shows the key differences between the OpenAI front-door and native pass-through.

Usage:
    # Set your Anthropic API key
    export ANTHROPIC_API_KEY=your_key_here
    
    # Start the server in another terminal
    python src/llm_endpoint_server.py
    
    # Run the demo
    python anthropic_native_demo.py

This script demonstrates:
1. Native Anthropic format requests and responses
2. SSE streaming in native Anthropic format  
3. Tool calling with native Anthropic schema
4. Error handling with original status codes
5. Header preservation and correlation IDs
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("❌ httpx is required for this demo")
    print("   Install with: pip install httpx")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
ANTHROPIC_ENDPOINT = f"{BASE_URL}/anthropic/v1/messages"
OPENAI_ENDPOINT = f"{BASE_URL}/v1/chat/completions"

async def demo_native_format():
    """Demonstrate native Anthropic format vs OpenAI format."""
    print("🔄 Demo 1: Native Anthropic Format vs OpenAI Format")
    print("=" * 50)
    
    # Native Anthropic request
    anthropic_request = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "What is the capital of France?"
            }
        ]
    }
    
    # Equivalent OpenAI request  
    openai_request = {
        "model": "claude-3-haiku",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user", 
                "content": "What is the capital of France?"
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Test Anthropic native endpoint
            print("📤 Sending request to Anthropic native endpoint...")
            anthropic_response = await client.post(
                ANTHROPIC_ENDPOINT,
                json=anthropic_request,
                timeout=30.0
            )
            
            if anthropic_response.status_code == 200:
                anthropic_data = anthropic_response.json()
                print("✅ Anthropic native response:")
                print(f"   Type: {anthropic_data.get('type')}")
                print(f"   Role: {anthropic_data.get('role')}")
                print(f"   Content structure: {type(anthropic_data.get('content'))}")
                if anthropic_data.get('content'):
                    print(f"   Content[0] type: {anthropic_data['content'][0].get('type')}")
            else:
                print(f"❌ Anthropic native failed: {anthropic_response.status_code}")
            
            # Test OpenAI compatibility endpoint
            print("\n📤 Sending request to OpenAI compatibility endpoint...")
            openai_response = await client.post(
                OPENAI_ENDPOINT,
                json=openai_request,
                timeout=30.0
            )
            
            if openai_response.status_code == 200:
                openai_data = openai_response.json()
                print("✅ OpenAI compatibility response:")
                print(f"   Object: {openai_data.get('object')}")
                print(f"   Message role: {openai_data.get('choices', [{}])[0].get('message', {}).get('role')}")
                print(f"   Content structure: {type(openai_data.get('choices', [{}])[0].get('message', {}).get('content'))}")
            else:
                print(f"❌ OpenAI compatibility failed: {openai_response.status_code}")
                
        except Exception as e:
            print(f"❌ Demo 1 failed: {e}")

async def demo_streaming():
    """Demonstrate SSE streaming with native Anthropic format."""
    print("\n🌊 Demo 2: SSE Streaming - Native Anthropic Format")
    print("=" * 50)
    
    streaming_request = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 150,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "Write a short poem about artificial intelligence."
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("📤 Starting SSE stream...")
            
            async with client.stream(
                'POST',
                ANTHROPIC_ENDPOINT,
                json=streaming_request,
                timeout=30.0
            ) as response:
                
                if response.status_code != 200:
                    print(f"❌ Streaming failed: {response.status_code}")
                    return
                
                print("✅ Stream headers:")
                print(f"   Content-Type: {response.headers.get('content-type')}")
                print(f"   Cache-Control: {response.headers.get('cache-control')}")
                print(f"   Connection: {response.headers.get('connection')}")
                
                print("\n📊 SSE Events:")
                event_count = 0
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        event_count += 1
                        lines = chunk.strip().split('\n')
                        for line in lines:
                            if line.startswith('event:'):
                                print(f"   {line}")
                            elif line.startswith('data:'):
                                try:
                                    data = json.loads(line[5:])  # Remove 'data:' prefix
                                    event_type = data.get('type', 'unknown')
                                    print(f"   └─ Type: {event_type}")
                                    if event_type == 'content_block_delta':
                                        delta = data.get('delta', {})
                                        text = delta.get('text', '')
                                        if text:
                                            print(f"      Text: {repr(text)}")
                                except json.JSONDecodeError:
                                    pass
                        
                        if event_count >= 10:  # Limit output for demo
                            break
                
                print(f"\n✅ Received {event_count} SSE events")
                
        except Exception as e:
            print(f"❌ Demo 2 failed: {e}")

async def demo_tool_calling():
    """Demonstrate tool calling in native Anthropic format."""
    print("\n🔧 Demo 3: Tool Calling - Native Anthropic Format")
    print("=" * 50)
    
    tool_request = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": "What's the current weather in New York?"
            }
        ],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get current weather information for a city",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city to get weather for"
                        },
                        "units": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature units"
                        }
                    },
                    "required": ["city"]
                }
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("📤 Sending tool calling request...")
            
            response = await client.post(
                ANTHROPIC_ENDPOINT,
                json=tool_request,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Tool calling response:")
                
                content = data.get('content', [])
                for i, block in enumerate(content):
                    block_type = block.get('type')
                    print(f"   Content[{i}] type: {block_type}")
                    
                    if block_type == 'text':
                        text = block.get('text', '')[:100]
                        print(f"   └─ Text: {text}...")
                    elif block_type == 'tool_use':
                        print(f"   └─ Tool: {block.get('name')}")
                        print(f"   └─ ID: {block.get('id')}")
                        print(f"   └─ Input: {block.get('input')}")
                        
            else:
                print(f"❌ Tool calling failed: {response.status_code}")
                error_text = response.text
                print(f"   Error: {error_text[:200]}...")
                
        except Exception as e:
            print(f"❌ Demo 3 failed: {e}")

async def demo_error_handling():
    """Demonstrate error pass-through with original status codes."""
    print("\n⚠️  Demo 4: Error Handling - Status Code Pass-Through")
    print("=" * 50)
    
    # Invalid request (missing required fields)
    invalid_request = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 100
        # Missing required 'messages' field
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("📤 Sending invalid request...")
            
            response = await client.post(
                ANTHROPIC_ENDPOINT,
                json=invalid_request,
                timeout=30.0
            )
            
            print(f"✅ Status code: {response.status_code}")
            
            if response.status_code >= 400:
                data = response.json()
                print("✅ Error response format:")
                print(f"   Type: {data.get('type')}")
                
                error = data.get('error', {})
                print(f"   Error type: {error.get('type')}")
                print(f"   Error message: {error.get('message', '')[:100]}...")
                
        except Exception as e:
            print(f"❌ Demo 4 failed: {e}")

async def demo_header_handling():
    """Demonstrate header preservation and correlation IDs."""
    print("\n📋 Demo 5: Header Handling - Correlation & Beta Features")
    print("=" * 50)
    
    request_data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 50,
        "messages": [
            {
                "role": "user",
                "content": "Hello!"
            }
        ]
    }
    
    # Test with beta header
    headers = {
        "Content-Type": "application/json",
        "anthropic-beta": "tools-2024-04-04"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("📤 Sending request with beta header...")
            
            response = await client.post(
                ANTHROPIC_ENDPOINT,
                json=request_data,
                headers=headers,
                timeout=30.0
            )
            
            print(f"✅ Status code: {response.status_code}")
            
            # Check for correlation ID
            request_id = response.headers.get('anthropic-request-id')
            if request_id:
                print(f"✅ Request ID preserved: {request_id}")
            else:
                print("ℹ️  No request ID in response (may be expected)")
            
            # Check response structure
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response format: {data.get('type')} message")
                
        except Exception as e:
            print(f"❌ Demo 5 failed: {e}")

async def main():
    """Run all demos."""
    print("🚀 Anthropic Native Pass-Through Adapter Demo")
    print("=" * 60)
    print()
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            health_response = await client.get(f"{BASE_URL}/anthropic/health", timeout=5.0)
            if health_response.status_code != 200:
                print("❌ Server not responding. Please start the server first:")
                print("   python src/llm_endpoint_server.py")
                return
    except Exception:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   python src/llm_endpoint_server.py")
        return
    
    # Check API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("⚠️  ANTHROPIC_API_KEY not set. Some demos will be limited.")
        print("   Set your API key: export ANTHROPIC_API_KEY=your_key_here")
        print()
    
    # Run demos
    await demo_native_format()
    await demo_streaming()
    await demo_tool_calling()
    await demo_error_handling()
    await demo_header_handling()
    
    print("\n" + "=" * 60)
    print("✅ Demo completed! Key benefits of Anthropic Native Pass-Through:")
    print("   • Zero schema transformation - pure Anthropic API compatibility")
    print("   • SSE streaming with proper headers and no buffering")
    print("   • Tool calls preserved in native Anthropic format")
    print("   • Error status codes passed through unchanged")
    print("   • Request correlation IDs preserved")
    print("   • Beta feature headers forwarded")
    print()
    print("🔗 Integration URLs:")
    print(f"   Native Anthropic: {ANTHROPIC_ENDPOINT}")
    print(f"   OpenAI Compatible: {OPENAI_ENDPOINT}")

if __name__ == "__main__":
    asyncio.run(main())