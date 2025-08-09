#!/usr/bin/env python3
"""
Token Estimation Tests for Anthropic Compatibility Layer
=======================================================

Tests for the async token estimation components ensuring:
- Accurate token counting for various message formats
- System message token counting
- Content block token counting
- Tool definition token counting
- Model-specific token limits validation
"""

import json
import pytest
import asyncio
from typing import Dict, Any, List

@pytest.mark.asyncio
async def test_count_tokens_async_basic():
    """Test basic token counting with simple messages."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Simple message
    messages = [
        {
            "role": "user",
            "content": "Hello, how are you today?"
        }
    ]
    
    # Count tokens
    token_count = await count_tokens_async(messages)
    
    # Verify token count is reasonable (exact count will depend on implementation)
    assert token_count > 0
    assert token_count < 50  # This should be a reasonable upper bound for this message

@pytest.mark.asyncio
async def test_count_tokens_async_with_system():
    """Test token counting with system message."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Message with system
    messages = [
        {
            "role": "user",
            "content": "Hello!"
        }
    ]
    system = "You are a helpful assistant that specializes in Python programming."
    
    # Count tokens without and with system
    token_count_no_system = await count_tokens_async(messages)
    token_count_with_system = await count_tokens_async(messages, system=system)
    
    # Verify system adds tokens
    assert token_count_with_system > token_count_no_system
    
    # Verify system token contribution is reasonable
    system_contribution = token_count_with_system - token_count_no_system
    assert system_contribution > 0
    assert system_contribution < 50  # Reasonable upper bound for this system message

@pytest.mark.asyncio
async def test_count_tokens_async_with_content_blocks():
    """Test token counting with content blocks."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Messages with content blocks
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello, how are you today?"}
            ]
        }
    ]
    
    # Messages with equivalent string content
    string_messages = [
        {
            "role": "user",
            "content": "Hello, how are you today?"
        }
    ]
    
    # Count tokens for both
    block_token_count = await count_tokens_async(messages)
    string_token_count = await count_tokens_async(string_messages)
    
    # Token counts should be similar (might not be exactly equal due to implementation details)
    assert abs(block_token_count - string_token_count) < 5

@pytest.mark.asyncio
async def test_count_tokens_async_multiple_blocks():
    """Test token counting with multiple content blocks."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Messages with multiple content blocks
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": ", how are you today?"}
            ]
        }
    ]
    
    # Messages with equivalent single content block
    single_block_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello, how are you today?"}
            ]
        }
    ]
    
    # Count tokens for both
    multi_block_token_count = await count_tokens_async(messages)
    single_block_token_count = await count_tokens_async(single_block_messages)
    
    # Token counts should be similar
    assert abs(multi_block_token_count - single_block_token_count) < 5

@pytest.mark.asyncio
async def test_count_tokens_async_with_image_blocks():
    """Test token counting with image content blocks."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Messages with image content blocks
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "base64data"}}
            ]
        }
    ]
    
    # Messages with equivalent text only
    text_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"}
            ]
        }
    ]
    
    # Count tokens for both
    image_token_count = await count_tokens_async(messages)
    text_token_count = await count_tokens_async(text_messages)
    
    # Image should add tokens
    assert image_token_count > text_token_count
    
    # Image contribution should be reasonable (implementation uses 85 tokens)
    image_contribution = image_token_count - text_token_count
    assert image_contribution >= 80  # Approximate image token cost

@pytest.mark.asyncio
async def test_count_tokens_async_with_tools(mock_anthropic_tools):
    """Test token counting with tool definitions."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Simple message
    messages = [
        {
            "role": "user",
            "content": "What's the weather in San Francisco?"
        }
    ]
    
    # Count tokens without and with tools
    token_count_no_tools = await count_tokens_async(messages)
    token_count_with_tools = await count_tokens_async(messages, tools=mock_anthropic_tools)
    
    # Tools should add tokens
    assert token_count_with_tools > token_count_no_tools
    
    # Tool contribution should be reasonable
    tool_contribution = token_count_with_tools - token_count_no_tools
    assert tool_contribution > 0

@pytest.mark.asyncio
async def test_count_tokens_async_conversation():
    """Test token counting with a multi-turn conversation."""
    from src.compat_async.tokenizers import count_tokens_async
    
    # Conversation messages
    messages = [
        {
            "role": "user",
            "content": "Hello, how are you?"
        },
        {
            "role": "assistant",
            "content": "I'm doing well! How can I help you today?"
        },
        {
            "role": "user",
            "content": "Tell me about Python programming."
        }
    ]
    
    # Count tokens
    token_count = await count_tokens_async(messages)
    
    # Verify token count is reasonable
    assert token_count > 0
    
    # Each message should contribute to the token count
    single_message_count = await count_tokens_async([messages[0]])
    assert token_count > single_message_count

@pytest.mark.asyncio
async def test_estimate_text_tokens():
    """Test the text token estimation utility."""
    from src.compat_async.tokenizers import _estimate_text_tokens
    
    # Test various text inputs
    test_cases = [
        ("", 0),  # Empty string
        ("Hello", 1),  # Short word
        ("Hello, world!", 3),  # Simple greeting
        ("This is a longer sentence with multiple words.", 10),  # Longer sentence
    ]
    
    for text, expected_min_tokens in test_cases:
        token_count = await _estimate_text_tokens(text)
        assert token_count >= expected_min_tokens

@pytest.mark.asyncio
async def test_estimate_tool_tokens():
    """Test the tool token estimation utility."""
    from src.compat_async.tokenizers import _estimate_tool_tokens
    
    # Simple tool definition
    tool = {
        "name": "get_weather",
        "description": "Get current weather in a location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Location to get weather for"}
            },
            "required": ["location"]
        }
    }
    
    # Count tokens
    token_count = await _estimate_tool_tokens(tool)
    
    # Verify token count is reasonable
    assert token_count > 0
    
    # More complex tool should have more tokens
    complex_tool = {
        "name": "search_database",
        "description": "Search a database with multiple parameters and filtering options",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "filters": {
                    "type": "object",
                    "properties": {
                        "date_range": {"type": "string", "description": "Date range for results"},
                        "categories": {"type": "array", "items": {"type": "string"}, "description": "Categories to filter by"},
                        "sort_by": {"type": "string", "enum": ["relevance", "date", "popularity"], "description": "Sort order"}
                    }
                },
                "limit": {"type": "integer", "description": "Maximum number of results to return"}
            },
            "required": ["query"]
        }
    }
    
    complex_token_count = await _estimate_tool_tokens(complex_tool)
    assert complex_token_count > token_count

@pytest.mark.asyncio
async def test_estimate_max_output_tokens():
    """Test the max output tokens estimation function."""
    from src.compat_async.tokenizers import estimate_max_output_tokens
    
    # Test with different models and input token counts
    test_cases = [
        ("claude-3-5-sonnet-latest", 1000, 199000 - 50),  # 200k - 1k - overhead
        ("claude-3-haiku-20240307", 5000, 195000 - 50),   # 200k - 5k - overhead
        ("unknown-model", 2000, 198000 - 50)              # 200k - 2k - overhead
    ]
    
    for model, input_tokens, expected_available in test_cases:
        max_output = await estimate_max_output_tokens(model, input_tokens)
        
        # Verify available tokens is reasonable
        assert max_output == expected_available

@pytest.mark.asyncio
async def test_validate_token_limits():
    """Test the token limits validation function."""
    from src.compat_async.tokenizers import validate_token_limits
    
    # Simple message
    messages = [
        {
            "role": "user",
            "content": "Hello, how are you today?"
        }
    ]
    
    # Test with valid limits
    valid_result = await validate_token_limits(
        messages, 
        "claude-3-5-sonnet-latest", 
        max_tokens=1000
    )
    
    # Should be valid
    assert valid_result["valid"] is True
    assert "input_tokens" in valid_result
    assert "requested_output_tokens" in valid_result
    assert "max_available_output_tokens" in valid_result
    assert valid_result["requested_output_tokens"] == 1000
    
    # Test with invalid limits (extremely large max_tokens)
    invalid_result = await validate_token_limits(
        messages, 
        "claude-3-5-sonnet-latest", 
        max_tokens=1000000
    )
    
    # Should be invalid
    assert invalid_result["valid"] is False
    assert "error" in invalid_result
    assert "recommendation" in invalid_result

@pytest.mark.asyncio
async def test_validate_token_limits_with_tools_and_system():
    """Test token limits validation with tools and system message."""
    from src.compat_async.tokenizers import validate_token_limits
    
    # Message
    messages = [
        {
            "role": "user",
            "content": "What's the weather in San Francisco?"
        }
    ]
    
    # System message
    system = "You are a helpful assistant."
    
    # Tool definition
    tools = [
        {
            "name": "get_weather",
            "description": "Get current weather in a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "Location to get weather for"}
                },
                "required": ["location"]
            }
        }
    ]
    
    # Validate with all components
    result = await validate_token_limits(
        messages,
        "claude-3-5-sonnet-latest",
        max_tokens=1000,
        system=system,
        tools=tools
    )
    
    # Should be valid
    assert result["valid"] is True
    
    # Input tokens should account for all components
    assert result["input_tokens"] > 0