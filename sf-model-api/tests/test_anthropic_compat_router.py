#!/usr/bin/env python3
"""
Router Integration Tests for Anthropic Compatibility Layer
=========================================================

Tests for the Anthropic-compatible router component ensuring:
- Proper endpoint registration and availability
- Correct request validation and header checking
- Proper error handling and status codes
- Endpoint-specific functionality:
  - /v1/models
  - /v1/messages
  - /v1/messages/count_tokens
- Proper Quart blueprint integration
"""

import os
import json
import pytest
import asyncio
from typing import Dict, Any, List
from quart import Quart
import pytest_asyncio

# The imports are handled in conftest.py

@pytest.mark.asyncio
async def test_create_anthropic_compat_router():
    """Test creation of Anthropic compatibility router blueprint."""
    from src.routers.anthropic_compat_async import create_anthropic_compat_router
    
    # Test with default URL prefix
    router_bp = create_anthropic_compat_router()
    assert router_bp.name == 'anthropic_compat_async'
    assert router_bp.url_prefix == '/v1'
    
    # Test with custom URL prefix
    custom_router_bp = create_anthropic_compat_router('/custom')
    assert custom_router_bp.name == 'anthropic_compat_async'
    assert custom_router_bp.url_prefix == '/custom'

@pytest.mark.asyncio
async def test_models_endpoint(test_client):
    """Test the /v1/models endpoint for listing available models."""
    # Test with valid headers
    response = await test_client.get(
        '/anthropic/v1/models',
        headers={'anthropic-version': '2023-06-01'}
    )
    
    assert response.status_code == 200
    data = await response.get_json()
    
    # Verify response format
    assert 'data' in data
    assert isinstance(data['data'], list)
    assert len(data['data']) > 0
    assert 'has_more' in data
    assert 'first_id' in data
    assert 'last_id' in data
    
    # Verify model data structure
    first_model = data['data'][0]
    assert 'id' in first_model
    assert 'display_name' in first_model
    assert 'type' in first_model
    assert 'capabilities' in first_model
    assert 'created_at' in first_model
    
    # Verify x-proxy-latency-ms header
    assert 'x-proxy-latency-ms' in response.headers

@pytest.mark.asyncio
async def test_models_endpoint_missing_header(test_client):
    """Test the /v1/models endpoint with missing Anthropic header."""
    response = await test_client.get(
        '/anthropic/v1/models'
    )
    
    assert response.status_code == 400
    data = await response.get_json()
    
    # Verify error response format
    assert 'type' in data
    assert data['type'] == 'error'
    assert 'error' in data
    assert 'type' in data['error']
    assert data['error']['type'] == 'invalid_request_error'
    assert 'message' in data['error']
    assert 'anthropic-version' in data['error']['message'].lower()

@pytest.mark.asyncio
async def test_count_tokens_endpoint(test_client, mock_anthropic_messages):
    """Test the /v1/messages/count_tokens endpoint."""
    # Prepare request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'system': 'You are a helpful assistant'
    }
    
    # Test with valid request
    response = await test_client.post(
        '/anthropic/v1/messages/count_tokens',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json=request_data
    )
    
    assert response.status_code == 200
    data = await response.get_json()
    
    # Verify response format
    assert 'input_tokens' in data
    assert isinstance(data['input_tokens'], int)
    assert data['input_tokens'] > 0
    
    # Verify x-proxy-latency-ms header
    assert 'x-proxy-latency-ms' in response.headers

@pytest.mark.asyncio
async def test_count_tokens_endpoint_invalid_model(test_client, mock_anthropic_messages):
    """Test the /v1/messages/count_tokens endpoint with invalid model."""
    # Prepare request data with invalid model
    request_data = {
        'model': 'invalid-model',
        'messages': mock_anthropic_messages
    }
    
    # Mock verify_model_async to return False for this test
    async def mock_verify_model_async(model):
        return False
    
    # Monkeypatch the verify_model_async function in the router module
    original_verify = __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async
    __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = mock_verify_model_async
    
    try:
        # Test with invalid model
        response = await test_client.post(
            '/anthropic/v1/messages/count_tokens',
            headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
            json=request_data
        )
        
        assert response.status_code == 400
        data = await response.get_json()
        
        # Verify error response
        assert data['type'] == 'error'
        assert data['error']['type'] == 'invalid_request_error'
        assert 'model' in data['error']['message'].lower()
    finally:
        # Restore original function
        __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = original_verify

@pytest.mark.asyncio
async def test_messages_endpoint_non_streaming(test_client, mock_anthropic_messages):
    """Test the /v1/messages endpoint with non-streaming request."""
    # Prepare request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'max_tokens': 100,
        'temperature': 0.7,
        'system': 'You are a helpful assistant',
        'stream': False
    }
    
    # Test with valid request
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json=request_data
    )
    
    assert response.status_code == 200
    data = await response.get_json()
    
    # Verify response format
    assert 'id' in data
    assert 'model' in data
    assert 'type' in data
    assert data['type'] == 'message'
    assert 'role' in data
    assert data['role'] == 'assistant'
    assert 'content' in data
    assert isinstance(data['content'], list)
    assert len(data['content']) > 0
    assert data['content'][0]['type'] == 'text'
    assert 'text' in data['content'][0]
    assert 'usage' in data
    assert 'input_tokens' in data['usage']
    assert 'output_tokens' in data['usage']
    
    # Verify x-proxy-latency-ms header
    assert 'x-proxy-latency-ms' in response.headers

@pytest.mark.asyncio
async def test_messages_endpoint_streaming(test_client, mock_anthropic_messages):
    """Test the /v1/messages endpoint with streaming request."""
    # Prepare request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'max_tokens': 100,
        'temperature': 0.7,
        'system': 'You are a helpful assistant',
        'stream': True
    }
    
    # Test with valid streaming request
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json=request_data
    )
    
    assert response.status_code == 200
    
    # Check headers for SSE streaming
    assert response.headers['Content-Type'] == 'text/plain; charset=utf-8'
    assert response.headers['Cache-Control'] == 'no-cache'
    assert response.headers['Connection'] == 'keep-alive'
    assert 'Access-Control-Allow-Origin' in response.headers
    assert 'X-Accel-Buffering' in response.headers
    
    # Read streaming response
    event_data = []
    event_types = set()
    
    # Read the response stream
    async for data in response.response:
        decoded = data.decode('utf-8')
        for line in decoded.strip().split('\n\n'):
            if not line:
                continue
                
            parts = line.split('\n')
            if len(parts) >= 2 and parts[0].startswith('event:'):
                event_type = parts[0].replace('event:', '').strip()
                event_types.add(event_type)
                
                if len(parts) >= 2 and parts[1].startswith('data:'):
                    event_json = parts[1].replace('data:', '').strip()
                    try:
                        event_data.append(json.loads(event_json))
                    except json.JSONDecodeError:
                        event_data.append(event_json)
    
    # Verify that we received the expected SSE event types
    expected_event_types = {
        'message_start', 
        'content_block_start', 
        'content_block_delta', 
        'content_block_stop', 
        'message_delta', 
        'message_stop'
    }
    
    for event_type in expected_event_types:
        assert event_type in event_types, f"Missing expected SSE event type: {event_type}"
    
    # Verify content in message_start event
    message_start_event = next((e for e in event_data if e.get('type') == 'message_start'), None)
    assert message_start_event is not None
    assert 'message' in message_start_event
    assert 'id' in message_start_event['message']

@pytest.mark.asyncio
async def test_messages_endpoint_invalid_content_type(test_client):
    """Test the /v1/messages endpoint with invalid content type."""
    # Send request with missing Content-Type
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01'},
        data="This is not JSON"
    )
    
    assert response.status_code == 400
    data = await response.get_json()
    
    # Verify error response
    assert data['type'] == 'error'
    assert data['error']['type'] == 'invalid_request_error'
    assert 'content-type' in data['error']['message'].lower()

@pytest.mark.asyncio
async def test_messages_endpoint_missing_required_params(test_client):
    """Test the /v1/messages endpoint with missing required parameters."""
    # Test with missing model parameter
    response1 = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json={'messages': [{'role': 'user', 'content': 'Hello'}]}
    )
    
    assert response1.status_code == 400
    data1 = await response1.get_json()
    assert 'model' in data1['error']['message'].lower()
    
    # Test with missing messages parameter
    response2 = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json={'model': 'claude-3-5-sonnet-latest'}
    )
    
    assert response2.status_code == 400
    data2 = await response2.get_json()
    assert 'messages' in data2['error']['message'].lower()

@pytest.mark.asyncio
async def test_messages_with_tools(test_client, mock_anthropic_messages, mock_anthropic_tools):
    """Test the /v1/messages endpoint with tools."""
    # Prepare request data with tools
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'tools': mock_anthropic_tools,
        'max_tokens': 100,
        'temperature': 0.7,
        'stream': False
    }
    
    # Test with valid request including tools
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json=request_data
    )
    
    assert response.status_code == 200
    data = await response.get_json()
    
    # We don't verify tool calls in the response here as that's tested in the mapper tests
    assert 'id' in data
    assert 'model' in data
    assert 'type' in data

@pytest.mark.asyncio
async def test_server_integration():
    """Test creating and starting an async server with the Anthropic router."""
    # Import async server
    from src.async_endpoint_server import create_app
    
    # Create a test app with minimal configuration
    app = create_app(testing=True)
    
    # Configure app for Anthropic compatibility (similar to how it's done in async_endpoint_server.py)
    anthropic_enabled = os.environ.get('NATIVE_ANTHROPIC_ENABLED', 'true').lower() in ('true', '1', 'yes')
    
    if anthropic_enabled:
        from src.routers.anthropic_compat_async import create_anthropic_compat_router
        anthropic_bp = create_anthropic_compat_router()
        app.register_blueprint(anthropic_bp, url_prefix='/anthropic/v1')
    
    # Test that the app was created successfully with the Anthropic router
    assert app is not None
    
    # Check that the Anthropic endpoints are registered
    for rule in app.url_map.iter_rules():
        if 'anthropic' in rule.rule:
            # Found at least one Anthropic endpoint
            break
    else:
        # No Anthropic endpoints found
        if anthropic_enabled:
            pytest.fail("Anthropic endpoints not registered in async server")

@pytest.mark.asyncio
async def test_error_handling(test_client):
    """Test the error handling in the Anthropic router."""
    # Test with a request that will cause an internal server error
    response = await test_client.post(
        '/anthropic/v1/messages',
        headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
        json={'model': 'claude-3-5-sonnet-latest', 'messages': 'not_a_list'}  # This will cause a type error
    )
    
    # Should return 500 with proper error format
    assert response.status_code == 500
    data = await response.get_json()
    
    # Verify error response format
    assert data['type'] == 'error'
    assert 'error' in data
    assert 'type' in data['error']
    assert 'message' in data['error']
    assert data['error']['type'] == 'api_error'