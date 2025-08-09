#!/usr/bin/env python3
"""
Anthropic Format Transformation Layer
=====================================

Async-compatible format transformation utilities for converting between 
Anthropic API format and Salesforce backend format. Provides enterprise-grade
async patterns with proper error handling and SSE streaming support.

Key Components:
- Header validation: require_anthropic_headers()
- Request mapping: map_messages_to_sf_async()
- Response mapping: map_sf_to_anthropic() 
- SSE streaming: sse_iter_from_sf_generation()

Usage:
    from compat_async.anthropic_mapper import require_anthropic_headers
    
    await require_anthropic_headers(request.headers)
"""

import json
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from werkzeug.datastructures import Headers
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unified_response_formatter import UnifiedResponseFormatter

logger = logging.getLogger(__name__)

# Initialize unified formatter for consistent response handling
formatter = UnifiedResponseFormatter()

async def require_anthropic_headers(headers: Headers) -> None:
    """
    Validate required Anthropic API headers.
    
    Enforces the anthropic-version header requirement which is mandatory
    for all Anthropic API requests to ensure API version compatibility.
    
    Args:
        headers: Request headers from Quart request
        
    Raises:
        ValueError: If anthropic-version header is missing or invalid
    """
    anthropic_version = headers.get('anthropic-version')
    
    if not anthropic_version:
        raise ValueError("Missing required header: anthropic-version")
    
    # Validate version format (basic validation)
    valid_versions = ['2023-06-01', '2023-01-01', '2024-02-15', '2024-06-01']
    if anthropic_version not in valid_versions:
        logger.warning(f"⚠️ Unrecognized anthropic-version: {anthropic_version}")
        # Allow through but log warning - some clients may use newer versions
    
    logger.debug(f"✅ Anthropic version validated: {anthropic_version}")

async def map_messages_to_sf_async(
    messages: List[Dict[str, Any]], 
    model: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convert Anthropic message format to Salesforce backend format asynchronously.
    
    Transforms Anthropic's message-based format with content blocks into
    Salesforce's expected format while preserving all semantic information.
    
    Args:
        messages: Anthropic format messages
        model: Model name (will be mapped to Salesforce model ID)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        system: System message content
        tools: Tool definitions in Anthropic format
        tool_choice: Tool choice specification
        
    Returns:
        Dict: Salesforce-compatible request format
    """
    # Map Anthropic model names to Salesforce model IDs
    model_mapping = {
        "claude-3-5-sonnet-latest": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
        "claude-3-haiku-20240307": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
        "claude-3-sonnet-20240229": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
        "claude-3-opus-20240229": "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet"
    }
    
    sf_model = model_mapping.get(model, model)
    logger.debug(f"🔧 Model mapping: {model} → {sf_model}")
    
    # Convert Anthropic messages to Salesforce format
    sf_messages = []
    
    # Add system message if provided
    if system:
        sf_messages.append({
            "role": "system",
            "content": system
        })
    
    # Process Anthropic messages
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content')
        
        # Handle content blocks (Anthropic format)
        if isinstance(content, list):
            text_content = ""
            for block in content:
                if block.get('type') == 'text':
                    text_content += block.get('text', '')
                # Note: Image blocks and other content types can be added here
            content = text_content
        
        sf_messages.append({
            "role": role,
            "content": content
        })
    
    # Build Salesforce request
    sf_request = {
        "messages": sf_messages,
        "model": sf_model,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    # Add tools if provided (convert Anthropic tool format if needed)
    if tools:
        # For now, pass tools through - more sophisticated conversion can be added
        # when Salesforce backend supports native tool calling
        sf_request["tools"] = tools
        
    if tool_choice:
        sf_request["tool_choice"] = tool_choice
    
    logger.debug(f"✅ Anthropic → SF mapping completed: {len(sf_messages)} messages")
    return sf_request

async def map_sf_to_anthropic(
    sf_response: Dict[str, Any], 
    model: str, 
    original_messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Convert Salesforce response to Anthropic message format asynchronously.
    
    Transforms Salesforce API response into Anthropic's expected message format
    with proper content blocks and usage information.
    
    Args:
        sf_response: Salesforce API response
        model: Original model name from request
        original_messages: Original message array for context
        
    Returns:
        Dict: Anthropic-compatible response format
    """
    # Extract content using unified formatter
    extraction_result = formatter.extract_response_text(sf_response)
    generated_text = extraction_result.text
    
    if not generated_text:
        generated_text = "Error: Unable to extract response content"
        logger.warning("⚠️ Failed to extract content from Salesforce response")
    
    # Extract usage information
    usage_info = formatter.extract_usage_info(sf_response)
    
    # Generate message ID
    message_id = f"msg_{int(time.time())}{hash(str(sf_response)) % 1000}"
    
    # Build Anthropic response format
    anthropic_response = {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": generated_text
            }
        ],
        "model": model,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage_info.prompt_tokens,
            "output_tokens": usage_info.completion_tokens
        }
    }
    
    logger.debug(f"✅ SF → Anthropic mapping completed: {len(generated_text)} chars")
    return anthropic_response

async def sse_iter_from_sf_generation(
    sf_response: Dict[str, Any], 
    model: str
) -> AsyncGenerator[str, None]:
    """
    Generate Anthropic-compatible SSE events from Salesforce response.
    
    Implements the exact Anthropic SSE specification with proper event sequence:
    1. message_start event with full message structure
    2. content_block_start event
    3. content_block_delta events for streaming text
    4. content_block_stop event  
    5. message_delta event with stop reason
    6. message_stop event
    
    Args:
        sf_response: Salesforce API response
        model: Model name for response
        
    Yields:
        str: SSE-formatted events in Anthropic specification
    """
    try:
        # Extract content and usage info
        extraction_result = formatter.extract_response_text(sf_response)
        generated_text = extraction_result.text or "Error: Unable to extract response content"
        usage_info = formatter.extract_usage_info(sf_response)
        
        # Generate message ID
        message_id = f"msg_{int(time.time())}{hash(str(sf_response)) % 1000}"
        
        logger.debug(f"🔄 Starting Anthropic SSE generation for {len(generated_text)} chars")
        
        # 1. Message start event
        message_start_data = {
            "type": "message_start",
            "message": {
                "id": message_id,
                "type": "message", 
                "role": "assistant",
                "content": [],
                "model": model,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {
                    "input_tokens": usage_info.prompt_tokens,
                    "output_tokens": 0
                }
            }
        }
        yield f"event: message_start\ndata: {json.dumps(message_start_data)}\n\n"
        
        # 2. Content block start event
        content_block_start_data = {
            "type": "content_block_start",
            "index": 0,
            "content_block": {
                "type": "text",
                "text": ""
            }
        }
        yield f"event: content_block_start\ndata: {json.dumps(content_block_start_data)}\n\n"
        
        # 3. Content block delta events (stream text in chunks)
        chunk_size = 5  # Words per chunk for smooth streaming
        words = generated_text.split()
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Add space if not the last chunk
            if i + chunk_size < len(words):
                chunk_text += " "
            
            content_block_delta_data = {
                "type": "content_block_delta",
                "index": 0,
                "delta": {
                    "type": "text_delta",
                    "text": chunk_text
                }
            }
            yield f"event: content_block_delta\ndata: {json.dumps(content_block_delta_data)}\n\n"
            
            # Small async delay for streaming effect
            await asyncio.sleep(0.01)
        
        # 4. Content block stop event
        content_block_stop_data = {
            "type": "content_block_stop",
            "index": 0
        }
        yield f"event: content_block_stop\ndata: {json.dumps(content_block_stop_data)}\n\n"
        
        # 5. Message delta event
        message_delta_data = {
            "type": "message_delta",
            "delta": {
                "stop_reason": "end_turn",
                "stop_sequence": None
            },
            "usage": {
                "output_tokens": usage_info.completion_tokens
            }
        }
        yield f"event: message_delta\ndata: {json.dumps(message_delta_data)}\n\n"
        
        # 6. Message stop event
        message_stop_data = {
            "type": "message_stop"
        }
        yield f"event: message_stop\ndata: {json.dumps(message_stop_data)}\n\n"
        
        logger.debug(f"✅ Anthropic SSE generation completed: {message_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in Anthropic SSE generation: {e}")
        # Send error event in Anthropic format
        error_data = {
            "type": "error",
            "error": {
                "type": "api_error",
                "message": str(e)
            }
        }
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"