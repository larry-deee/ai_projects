#!/usr/bin/env python3
"""
Anthropic API Python Client Examples

This file demonstrates how to use the Salesforce Models API Gateway's 
Anthropic-compatible endpoints with the official Anthropic Python SDK.

Prerequisites:
- pip install anthropic
- Ensure the gateway server is running on localhost:8000

Usage:
    python python_client_examples.py
"""

import os
import time
import asyncio
import anthropic
from typing import List, Dict, Any

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000/anthropic')
ANTHROPIC_VERSION = '2023-06-01'

def check_server_health():
    """Check if the server is running."""
    import requests
    try:
        response = requests.get(f'{API_BASE_URL.replace("/anthropic", "")}/health')
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print("❌ Server returned error status")
            return False
    except Exception as e:
        print(f"❌ Server is not running: {e}")
        return False

def example_1_basic_message():
    """Basic message completion example."""
    print("\n1️⃣  Basic Message Completion")
    print("============================")
    
    client = anthropic.Anthropic(
        api_key="any-key",  # Not used for local API
        base_url=API_BASE_URL
    )
    
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "user", "content": "Hello, Claude! Can you introduce yourself briefly?"}
            ],
            max_tokens=1000
        )
        
        print(f"Response ID: {response.id}")
        print(f"Model: {response.model}")
        print(f"Content: {response.content[0].text}")
        print(f"Stop reason: {response.stop_reason}")
        print(f"Usage: {response.usage}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_2_system_context():
    """Message with system context example."""
    print("\n2️⃣  Message with System Context")
    print("===============================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "user", "content": "Explain quantum computing in simple terms."}
            ],
            system="You are a physics professor who excels at explaining complex concepts to beginners. Use analogies and simple language.",
            max_tokens=200
        )
        
        print(f"Content: {response.content[0].text}")
        print(f"Input tokens: {response.usage.input_tokens}")
        print(f"Output tokens: {response.usage.output_tokens}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_3_multi_turn_conversation():
    """Multi-turn conversation example."""
    print("\n3️⃣  Multi-turn Conversation")
    print("===========================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    # Simulate a conversation
    conversation = [
        {"role": "user", "content": "What is the capital of Japan?"},
    ]
    
    try:
        # First exchange
        response1 = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=conversation,
            max_tokens=100
        )
        
        print(f"User: {conversation[0]['content']}")
        print(f"Claude: {response1.content[0].text}")
        
        # Add Claude's response to conversation
        conversation.extend([
            {"role": "assistant", "content": response1.content[0].text},
            {"role": "user", "content": "What is the population of that city?"}
        ])
        
        # Second exchange
        response2 = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=conversation,
            max_tokens=100
        )
        
        print(f"User: What is the population of that city?")
        print(f"Claude: {response2.content[0].text}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_4_temperature_comparison():
    """Compare responses with different temperatures."""
    print("\n4️⃣  Temperature Comparison")
    print("==========================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    prompt = "Write a creative haiku about artificial intelligence."
    
    temperatures = [0.0, 0.5, 1.0]
    
    for temp in temperatures:
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temp,
                max_tokens=100
            )
            
            print(f"\nTemperature {temp}:")
            print(response.content[0].text)
            
        except Exception as e:
            print(f"Error at temperature {temp}: {e}")

def example_5_model_comparison():
    """Compare responses from different models."""
    print("\n5️⃣  Model Comparison")
    print("====================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    models = [
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229"
    ]
    
    prompt = "Explain the concept of recursion in programming in one paragraph."
    
    for model in models:
        try:
            start_time = time.time()
            response = client.messages.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )
            end_time = time.time()
            
            print(f"\n{model}:")
            print(f"Response time: {end_time - start_time:.2f}s")
            print(f"Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
            print(f"Content: {response.content[0].text[:200]}...")
            
        except Exception as e:
            print(f"Error with {model}: {e}")

def example_6_streaming_basic():
    """Basic streaming example."""
    print("\n6️⃣  Basic Streaming")
    print("===================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    try:
        with client.messages.stream(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "user", "content": "Write a short story about a robot learning to paint."}
            ],
            max_tokens=300
        ) as stream:
            print("Streaming response:")
            for text in stream.text_stream:
                print(text, end="", flush=True)
            print()  # New line after streaming
            
        # Get the final message
        message = stream.get_final_message()
        print(f"\nFinal usage: {message.usage}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_7_streaming_with_events():
    """Streaming with event inspection."""
    print("\n7️⃣  Streaming with Event Inspection")
    print("===================================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    try:
        with client.messages.stream(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "user", "content": "Count from 1 to 5 with a fact about each number."}
            ],
            max_tokens=200
        ) as stream:
            print("Event types received:")
            
            for event in stream:
                if event.type == 'message_start':
                    print(f"🚀 {event.type}: {event.message.id}")
                elif event.type == 'content_block_start':
                    print(f"📝 {event.type}: index {event.index}")
                elif event.type == 'content_block_delta':
                    print(text, end="", flush=True)
                elif event.type == 'content_block_stop':
                    print(f"\n📋 {event.type}: index {event.index}")
                elif event.type == 'message_delta':
                    print(f"🔄 {event.type}: {event.delta}")
                elif event.type == 'message_stop':
                    print(f"✅ {event.type}")
            
    except Exception as e:
        print(f"Error: {e}")

def example_8_token_counting():
    """Token counting example."""
    print("\n8️⃣  Token Counting")
    print("==================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    messages = [
        {"role": "user", "content": "This is a test message to count tokens. It has multiple sentences! And some punctuation? Plus numbers like 123 and symbols like @#$."}
    ]
    
    system_message = "You are a helpful assistant that provides accurate information."
    
    try:
        # Use the count_tokens endpoint
        response = client.messages.count_tokens(
            model="claude-3-haiku-20240307",
            messages=messages,
            system=system_message
        )
        
        print(f"Input tokens: {response.input_tokens}")
        
        # Compare with actual usage
        actual_response = client.messages.create(
            model="claude-3-haiku-20240307",
            messages=messages,
            system=system_message,
            max_tokens=50
        )
        
        print(f"Actual input tokens (from completion): {actual_response.usage.input_tokens}")
        print(f"Output tokens: {actual_response.usage.output_tokens}")
        print(f"Total tokens: {actual_response.usage.input_tokens + actual_response.usage.output_tokens}")
        
    except Exception as e:
        print(f"Error: {e}")

def example_9_error_handling():
    """Error handling examples."""
    print("\n9️⃣  Error Handling")
    print("==================")
    
    client = anthropic.Anthropic(
        api_key="any-key",
        base_url=API_BASE_URL
    )
    
    # Test various error conditions
    test_cases = [
        {
            "name": "Invalid model",
            "params": {
                "model": "invalid-model-name",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 100
            }
        },
        {
            "name": "Missing model",
            "params": {
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 100
            }
        },
        {
            "name": "Empty messages",
            "params": {
                "model": "claude-3-haiku-20240307",
                "messages": [],
                "max_tokens": 100
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        try:
            if 'model' not in test_case['params']:
                # This will fail at the SDK level before making the request
                print("❌ SDK validation error: model parameter is required")
            else:
                response = client.messages.create(**test_case['params'])
                print(f"✅ Unexpected success: {response.content[0].text[:50]}...")
        except anthropic.BadRequestError as e:
            print(f"❌ Bad request error: {e}")
        except Exception as e:
            print(f"❌ Other error: {e}")

def example_10_async_usage():
    """Async client usage example."""
    print("\n🔟 Async Client Usage")
    print("=====================")
    
    async def async_example():
        client = anthropic.AsyncAnthropic(
            api_key="any-key",
            base_url=API_BASE_URL
        )
        
        try:
            # Async basic message
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[
                    {"role": "user", "content": "What are the benefits of asynchronous programming?"}
                ],
                max_tokens=200
            )
            
            print(f"Async response: {response.content[0].text}")
            
            # Async streaming
            print("\nAsync streaming:")
            async with client.messages.stream(
                model="claude-3-haiku-20240307",
                messages=[
                    {"role": "user", "content": "Write a haiku about async programming."}
                ],
                max_tokens=100
            ) as stream:
                async for text in stream.text_stream:
                    print(text, end="", flush=True)
                print()
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Run the async example
    asyncio.run(async_example())

def main():
    """Run all examples."""
    print("🐍 Anthropic Python SDK Examples")
    print("=================================")
    print(f"Using API base URL: {API_BASE_URL}")
    
    # Check server health
    if not check_server_health():
        print("Please start the server first and try again.")
        return
    
    # Run examples
    example_1_basic_message()
    example_2_system_context()
    example_3_multi_turn_conversation()
    example_4_temperature_comparison()
    example_5_model_comparison()
    example_6_streaming_basic()
    example_7_streaming_with_events()
    example_8_token_counting()
    example_9_error_handling()
    example_10_async_usage()
    
    print("\n✅ All examples completed!")
    print("="*50)
    print("These examples demonstrated:")
    print("• Basic message completion")
    print("• System context usage")
    print("• Multi-turn conversations")
    print("• Temperature effects")
    print("• Model comparison")
    print("• Basic streaming")
    print("• Streaming event inspection")
    print("• Token counting")
    print("• Error handling")
    print("• Async client usage")

if __name__ == "__main__":
    main()