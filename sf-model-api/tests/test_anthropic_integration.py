#!/usr/bin/env python3
"""
Integration Tests for Anthropic Compatibility Layer
==================================================

End-to-end tests for the Anthropic compatibility implementation verifying:
- Complete request/response flow from client to Salesforce backend
- Authentication integration with token pre-warming
- Error handling across the entire pipeline
- Concurrent request handling
- Memory efficiency and resource management
"""

import os
import json
import time
import pytest
import asyncio
from typing import Dict, Any, List, Optional
from quart import Quart
import pytest_asyncio

@pytest.mark.asyncio
async def test_end_to_end_request_flow(test_client, mock_anthropic_messages):
    """Test the complete request flow from client to backend and response."""
    # Prepare request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'max_tokens': 100,
        'temperature': 0.7,
        'system': 'You are a helpful assistant',
        'stream': False
    }
    
    # Send request
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json=request_data
    )
    
    # Verify response
    assert response.status_code == 200
    data = await response.get_json()
    
    # Verify essential response fields
    assert 'id' in data
    assert 'model' in data
    assert 'content' in data
    assert 'usage' in data

@pytest.mark.asyncio
async def test_end_to_end_streaming(test_client, mock_anthropic_messages):
    """Test end-to-end streaming from client to backend and response."""
    # Prepare request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'max_tokens': 100,
        'temperature': 0.7,
        'system': 'You are a helpful assistant',
        'stream': True
    }
    
    # Send streaming request
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json=request_data
    )
    
    # Verify response code
    assert response.status_code == 200
    
    # Read and validate streaming events
    events = []
    async for chunk in response.response:
        events.append(chunk.decode('utf-8'))
    
    # Verify we received multiple events
    assert len(events) > 1
    
    # Verify essential event types are present
    content = ''.join(events)
    assert 'event: message_start' in content
    assert 'event: content_block_start' in content
    assert 'event: content_block_delta' in content
    assert 'event: content_block_stop' in content
    assert 'event: message_stop' in content

@pytest.mark.asyncio
async def test_integration_error_handling(test_client):
    """Test error handling across the entire pipeline."""
    # Test with invalid request that should cause an error at the backend
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': [{'role': 'invalid_role', 'content': 'This should cause an error'}]
    }
    
    # Mock the async client to raise an exception
    async def mock_async_chat_completion(**kwargs):
        raise ValueError("Backend error: Invalid message role")
    
    # Patch the client method
    original_method = __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client
    
    async def mock_get_client():
        client = await original_method()
        client._async_chat_completion = mock_async_chat_completion
        return client
    
    # Apply patch
    __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client = mock_get_client
    
    try:
        # Send request
        response = await test_client.post(
            '/anthropic/v1/messages',
            headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
            json=request_data
        )
        
        # Verify error response
        assert response.status_code in (400, 500)  # Either client or server error
        data = await response.get_json()
        
        # Verify error format
        assert data['type'] == 'error'
        assert 'error' in data
        assert 'type' in data['error']
        assert 'message' in data['error']
    finally:
        # Restore original method
        __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client = original_method

@pytest.mark.asyncio
async def test_concurrent_requests(test_client, mock_anthropic_messages):
    """Test handling multiple concurrent requests."""
    # Prepare multiple requests
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'max_tokens': 50,
        'temperature': 0.7,
        'stream': False
    }
    
    # Create multiple request coroutines
    request_count = 5
    requests = []
    
    for i in range(request_count):
        # Clone request data to avoid issues
        req_data = dict(request_data)
        req_data['messages'] = list(mock_anthropic_messages)  # Make a copy
        
        # Add request
        requests.append(
            test_client.post(
                '/anthropic/v1/messages',
                headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
                json=req_data
            )
        )
    
    # Send concurrent requests
    start_time = time.time()
    responses = await asyncio.gather(*requests)
    end_time = time.time()
    
    # Verify all responses are successful
    for response in responses:
        assert response.status_code == 200
        data = await response.get_json()
        assert 'id' in data
    
    # Verify concurrency benefit (total time should be less than sequential time)
    total_time = end_time - start_time
    
    # Log the time for debugging
    print(f"Concurrent requests ({request_count}) completed in {total_time:.2f} seconds")
    
    # No hard assertion on time since it depends on the test environment

@pytest.mark.asyncio
async def test_integration_with_token_prewarming():
    """Test integration with token pre-warming system."""
    # This is a complex test that requires mocking the token pre-warming system
    # We'll create a simplified version for demonstration
    
    # Import the necessary modules
    from src.routers.anthropic_compat_async import AnthropicCompatAsyncRouter
    from quart import Quart
    
    # Create a new app for this test
    app = Quart(__name__)
    
    # Create a mock token manager
    class MockTokenManager:
        async def get_token(self):
            return "mock_token_123"
    
    # Create a mock client factory that uses the token manager
    async def mock_get_client():
        from salesforce_models_client import AsyncSalesforceModelsClient
        
        # Create a minimal client instance
        client = AsyncSalesforceModelsClient(
            api_url="https://example.com",
            token_manager=MockTokenManager()
        )
        
        # Mock the _async_chat_completion method
        client._async_chat_completion = async_chat_completion_mock
        return client
    
    # Mock chat completion function
    async def async_chat_completion_mock(**kwargs):
        # Simulate successful response
        return {
            "generations": [{"text": "Response with pre-warmed token"}],
            "usage": {"inputTokenCount": 10, "outputTokenCount": 5}
        }
    
    # Register the mock client getter
    app.async_client_getter = mock_get_client
    
    # Create and register the Anthropic router
    router = AnthropicCompatAsyncRouter()
    app.register_blueprint(router.create_blueprint(), url_prefix='/v1')
    
    # Create a test client
    test_client = app.test_client()
    
    # Prepare request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': [{'role': 'user', 'content': 'Hello'}],
        'max_tokens': 50,
        'stream': False
    }
    
    # Mock verify_model_async to return True
    async def mock_verify_model_async(model):
        return True
    
    # Apply patch
    original_verify = __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async
    __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = mock_verify_model_async
    
    # Apply get_async_client patch
    original_get_client = __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client
    __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client = mock_get_client
    
    try:
        # Send request
        response = await test_client.post(
            '/v1/messages',
            headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
            json=request_data
        )
        
        # Verify response
        assert response.status_code == 200
        data = await response.get_json()
        
        # Basic verification
        assert 'id' in data
        assert 'content' in data
    finally:
        # Restore original functions
        __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = original_verify
        __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client = original_get_client

@pytest.mark.asyncio
async def test_memory_usage_with_large_response():
    """Test memory efficiency with large responses."""
    from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
    import psutil
    import gc
    
    # Force garbage collection to get a clean baseline
    gc.collect()
    
    # Get initial memory usage
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Create a large mock response
    large_text = "This is a test. " * 10000  # ~200KB of text
    large_response = {
        "generations": [{"text": large_text}],
        "usage": {"inputTokenCount": 10, "outputTokenCount": 50000}
    }
    
    # Process with SSE generator
    event_count = 0
    total_bytes = 0
    
    async for event in sse_iter_from_sf_generation(large_response, "claude-3-5-sonnet-latest"):
        event_count += 1
        total_bytes += len(event)
    
    # Force garbage collection again
    gc.collect()
    
    # Check final memory usage
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_diff = final_memory - initial_memory
    
    # Log memory usage (no hard assertion since it depends on environment)
    print(f"Memory before: {initial_memory:.2f} MB")
    print(f"Memory after: {final_memory:.2f} MB")
    print(f"Difference: {memory_diff:.2f} MB")
    print(f"Processed {event_count} events, {total_bytes} bytes")
    
    # Verify the function processed the large response
    assert event_count > 0
    assert total_bytes > len(large_text)

@pytest.mark.asyncio
async def test_router_integration_with_async_server():
    """Test integration of router with the async endpoint server."""
    # Import server module
    from src.async_endpoint_server import create_app
    
    # Create app with minimal configuration for testing
    app = create_app(testing=True)
    
    # Ensure the Anthropic router can be registered
    from src.routers.anthropic_compat_async import create_anthropic_compat_router
    
    # Register router with custom prefix for testing
    router = create_anthropic_compat_router('/v1-test')
    app.register_blueprint(router, url_prefix='/anthropic-test')
    
    # Verify the router was registered by checking routes
    registered_routes = [str(rule) for rule in app.url_map.iter_rules()]
    
    # Check for expected routes
    assert '/anthropic-test/v1-test/models' in registered_routes
    assert '/anthropic-test/v1-test/messages' in registered_routes
    assert '/anthropic-test/v1-test/messages/count_tokens' in registered_routes
    
    # Create test client
    client = app.test_client()
    
    # Verify the endpoint responds (with minimal mocking)
    # This will likely return an error due to missing backend, but should handle the request
    response = await client.get(
        '/anthropic-test/v1-test/models',
        headers={'anthropic-version': '2023-06-01'}
    )
    
    # Verify the request was routed properly (any response means routing worked)
    assert response.status_code != 404