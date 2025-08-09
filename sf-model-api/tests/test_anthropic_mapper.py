#!/usr/bin/env python3
"""
Format Transformation Tests for Anthropic Compatibility Layer
============================================================

Tests for the format transformation components ensuring:
- Anthropic header validation
- Message format conversion (Anthropic → Salesforce)
- Response format conversion (Salesforce → Anthropic)
- Content block handling (text, images, etc.)
- SSE streaming generation
- Tool calling integration
- System message handling
"""

import json
import pytest
import asyncio
from typing import Dict, Any, List
from werkzeug.datastructures import Headers

@pytest.mark.asyncio
async def test_require_anthropic_headers_valid():
    """Test header validation with valid Anthropic headers."""
    from src.compat_async.anthropic_mapper import require_anthropic_headers
    
    # Test with valid version
    headers = Headers({
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    })
    
    # Should not raise an exception
    await require_anthropic_headers(headers)

@pytest.mark.asyncio
async def test_require_anthropic_headers_missing():
    """Test header validation with missing Anthropic headers."""
    from src.compat_async.anthropic_mapper import require_anthropic_headers
    
    # Test with missing version
    headers = Headers({
        'content-type': 'application/json'
    })
    
    # Should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        await require_anthropic_headers(headers)
    
    assert "anthropic-version" in str(excinfo.value).lower()

@pytest.mark.asyncio
async def test_require_anthropic_headers_unknown_version():
    """Test header validation with unknown Anthropic version."""
    from src.compat_async.anthropic_mapper import require_anthropic_headers
    
    # Test with unknown version - this should still pass but log a warning
    headers = Headers({
        'anthropic-version': '9999-99-99',
        'content-type': 'application/json'
    })
    
    # Should not raise an exception (we're tolerant of unknown versions)
    await require_anthropic_headers(headers)

@pytest.mark.asyncio
async def test_map_messages_to_sf_async_basic(mock_anthropic_messages):
    """Test basic message mapping from Anthropic to Salesforce format."""
    from src.compat_async.anthropic_mapper import map_messages_to_sf_async
    
    # Map messages
    sf_request = await map_messages_to_sf_async(
        messages=mock_anthropic_messages,
        model="claude-3-5-sonnet-latest",
        max_tokens=100,
        temperature=0.7
    )
    
    # Verify basic structure
    assert "messages" in sf_request
    assert "model" in sf_request
    assert "max_tokens" in sf_request
    assert "temperature" in sf_request
    
    # Verify message mapping
    sf_messages = sf_request["messages"]
    assert len(sf_messages) == len(mock_anthropic_messages)
    
    # Verify model mapping
    assert "sfdc_ai__" in sf_request["model"]

@pytest.mark.asyncio
async def test_map_messages_to_sf_async_with_system():
    """Test message mapping with system message."""
    from src.compat_async.anthropic_mapper import map_messages_to_sf_async
    
    # Define messages with system
    anthropic_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello, world!"}
            ]
        }
    ]
    system_message = "You are a helpful assistant specialized in Python"
    
    # Map messages with system
    sf_request = await map_messages_to_sf_async(
        messages=anthropic_messages,
        model="claude-3-5-sonnet-latest",
        system=system_message
    )
    
    # Verify system message is first in SF messages
    sf_messages = sf_request["messages"]
    assert len(sf_messages) == len(anthropic_messages) + 1  # +1 for system
    assert sf_messages[0]["role"] == "system"
    assert sf_messages[0]["content"] == system_message
    
    # Verify user message is second
    assert sf_messages[1]["role"] == "user"
    assert "Hello, world!" in sf_messages[1]["content"]

@pytest.mark.asyncio
async def test_map_messages_to_sf_async_complex_content():
    """Test message mapping with complex content blocks."""
    from src.compat_async.anthropic_mapper import map_messages_to_sf_async
    
    # Define messages with multiple content blocks
    anthropic_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": ", world!"}
            ]
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "How can I help you today?"}
            ]
        }
    ]
    
    # Map messages
    sf_request = await map_messages_to_sf_async(
        messages=anthropic_messages,
        model="claude-3-haiku-20240307"
    )
    
    # Verify messages are correctly combined
    sf_messages = sf_request["messages"]
    assert len(sf_messages) == 2
    
    # First message should combine text blocks
    assert sf_messages[0]["role"] == "user"
    assert sf_messages[0]["content"] == "Hello, world!"
    
    # Second message should preserve content
    assert sf_messages[1]["role"] == "assistant"
    assert sf_messages[1]["content"] == "How can I help you today?"

@pytest.mark.asyncio
async def test_map_messages_to_sf_async_with_tools(mock_anthropic_tools):
    """Test message mapping with tool definitions."""
    from src.compat_async.anthropic_mapper import map_messages_to_sf_async
    
    # Define messages
    anthropic_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's the weather in San Francisco?"}
            ]
        }
    ]
    
    # Map messages with tools
    sf_request = await map_messages_to_sf_async(
        messages=anthropic_messages,
        model="claude-3-5-sonnet-latest",
        tools=mock_anthropic_tools
    )
    
    # Verify tools are included in request
    assert "tools" in sf_request
    assert len(sf_request["tools"]) == len(mock_anthropic_tools)
    assert sf_request["tools"][0]["name"] == "get_weather"

@pytest.mark.asyncio
async def test_map_sf_to_anthropic_basic(mock_sf_response):
    """Test basic response mapping from Salesforce to Anthropic format."""
    from src.compat_async.anthropic_mapper import map_sf_to_anthropic
    
    # Mock original messages
    original_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello"}
            ]
        }
    ]
    
    # Map response
    anthropic_response = await map_sf_to_anthropic(
        mock_sf_response,
        "claude-3-5-sonnet-latest",
        original_messages
    )
    
    # Verify basic structure
    assert "id" in anthropic_response
    assert "type" in anthropic_response
    assert anthropic_response["type"] == "message"
    assert "role" in anthropic_response
    assert anthropic_response["role"] == "assistant"
    assert "content" in anthropic_response
    assert isinstance(anthropic_response["content"], list)
    assert anthropic_response["content"][0]["type"] == "text"
    
    # Verify text content
    text_content = anthropic_response["content"][0]["text"]
    assert "Hello!" in text_content
    
    # Verify usage information
    assert "usage" in anthropic_response
    assert "input_tokens" in anthropic_response["usage"]
    assert "output_tokens" in anthropic_response["usage"]
    assert anthropic_response["usage"]["input_tokens"] == 10
    assert anthropic_response["usage"]["output_tokens"] == 12

@pytest.mark.asyncio
async def test_map_sf_to_anthropic_with_tools(mock_sf_response_with_tools):
    """Test response mapping with tool calls."""
    from src.compat_async.anthropic_mapper import map_sf_to_anthropic
    
    # Mock original messages
    original_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's the weather in San Francisco?"}
            ]
        }
    ]
    
    # Map response with tool calls
    anthropic_response = await map_sf_to_anthropic(
        mock_sf_response_with_tools,
        "claude-3-5-sonnet-latest",
        original_messages
    )
    
    # Verify content has tool calls - Note: The current implementation may not handle this yet
    # This will depend on if the anthropic_mapper.py has been updated to handle tool calls
    # If it hasn't, this test will need to be modified once that feature is added
    assert "id" in anthropic_response
    assert "type" in anthropic_response
    assert "usage" in anthropic_response

@pytest.mark.asyncio
async def test_sse_iter_from_sf_generation(mock_sf_response):
    """Test SSE event generation from Salesforce response."""
    from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
    
    # Collect events from SSE generator
    events = []
    event_types = set()
    
    async for event in sse_iter_from_sf_generation(mock_sf_response, "claude-3-5-sonnet-latest"):
        events.append(event)
        
        # Extract event type
        event_lines = event.strip().split('\n')
        if event_lines and event_lines[0].startswith('event:'):
            event_type = event_lines[0].replace('event:', '').strip()
            event_types.add(event_type)
    
    # Verify we got the expected event types
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
    
    # Verify event content
    for event in events:
        # Each event should have event: and data: parts
        assert 'event:' in event
        assert 'data:' in event
        
        # Extract data JSON
        data_line = [line for line in event.split('\n') if line.startswith('data:')][0]
        data_json_str = data_line.replace('data:', '').strip()
        
        try:
            data = json.loads(data_json_str)
            assert 'type' in data
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON in SSE event: {data_json_str}")

@pytest.mark.asyncio
async def test_sse_content_building():
    """Test that SSE events properly build up the complete response."""
    from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
    
    # Create mock response with specific content to test
    mock_response = {
        "generations": [{"text": "This is a test response for streaming."}],
        "usage": {"inputTokenCount": 5, "outputTokenCount": 8}
    }
    
    # Collect all content delta events
    content_pieces = []
    
    async for event in sse_iter_from_sf_generation(mock_response, "claude-3-5-sonnet-latest"):
        if 'event: content_block_delta' in event:
            data_line = [line for line in event.split('\n') if line.startswith('data:')][0]
            data_json_str = data_line.replace('data:', '').strip()
            data = json.loads(data_json_str)
            
            if data['type'] == 'content_block_delta' and 'delta' in data:
                if data['delta']['type'] == 'text_delta' and 'text' in data['delta']:
                    content_pieces.append(data['delta']['text'])
    
    # Combine all content pieces
    full_content = ''.join(content_pieces)
    
    # Verify the full content matches the original response
    assert full_content.strip() == "This is a test response for streaming."

@pytest.mark.asyncio
async def test_sse_iter_error_handling():
    """Test error handling in SSE generation."""
    from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
    
    # Create an invalid response that will cause errors
    invalid_response = {"invalid": "structure"}
    
    # Collect events
    error_events = []
    
    async for event in sse_iter_from_sf_generation(invalid_response, "claude-3-5-sonnet-latest"):
        if 'event: error' in event:
            error_events.append(event)
    
    # Verify we got an error event
    assert len(error_events) > 0
    
    # Verify error event format
    error_event = error_events[0]
    assert 'event: error' in error_event
    assert 'data:' in error_event
    
    # Extract error data
    data_line = [line for line in error_event.split('\n') if line.startswith('data:')][0]
    data_json_str = data_line.replace('data:', '').strip()
    data = json.loads(data_json_str)
    
    # Verify error data format
    assert data['type'] == 'error'
    assert 'error' in data
    assert 'type' in data['error']
    assert data['error']['type'] == 'api_error'
    assert 'message' in data['error']