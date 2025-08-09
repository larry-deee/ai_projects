#!/usr/bin/env python3
"""
Async Token Estimation for Anthropic Compatibility
==================================================

Async-compatible token counting utilities for Anthropic message format.
Provides fast token estimation for the /v1/messages/count_tokens endpoint
with support for system messages, user messages, and tool definitions.

Key Features:
- Simple token estimation algorithm (len(text)//4 approach)
- Support for Anthropic message content blocks
- Tool definition token counting
- Async-compatible patterns for enterprise performance

Usage:
    from compat_async.tokenizers import count_tokens_async
    
    token_count = await count_tokens_async(messages, system, tools)
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

async def count_tokens_async(
    messages: List[Dict[str, Any]], 
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None
) -> int:
    """
    Count tokens for Anthropic message format asynchronously.
    
    Provides fast token estimation using a simple algorithm that approximates
    the token count without requiring expensive tokenizer libraries.
    
    Algorithm: Roughly 4 characters per token, plus word count estimation
    This provides reasonable accuracy for token budgeting and billing estimation.
    
    Args:
        messages: List of Anthropic format messages
        system: Optional system message content
        tools: Optional tool definitions
        
    Returns:
        int: Estimated token count
    """
    try:
        total_tokens = 0
        
        # Count system message tokens
        if system:
            total_tokens += await _estimate_text_tokens(system)
        
        # Count message tokens
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            # Add role overhead (small constant for role tokens)
            total_tokens += 2  # Approximate tokens for role specification
            
            # Handle content blocks (Anthropic format)
            if isinstance(content, list):
                for block in content:
                    if block.get('type') == 'text':
                        text = block.get('text', '')
                        total_tokens += await _estimate_text_tokens(text)
                    elif block.get('type') == 'image':
                        # Image tokens are more complex, use a reasonable estimate
                        total_tokens += 85  # Anthropic's typical image token cost
                    # Add support for other content block types as needed
            elif isinstance(content, str):
                total_tokens += await _estimate_text_tokens(content)
        
        # Count tool definition tokens
        if tools:
            for tool in tools:
                tool_tokens = await _estimate_tool_tokens(tool)
                total_tokens += tool_tokens
        
        logger.debug(f"📊 Token estimation: {total_tokens} tokens for {len(messages)} messages")
        return total_tokens
        
    except Exception as e:
        logger.error(f"❌ Error counting tokens: {e}")
        # Return a conservative estimate on error
        return 1000

async def _estimate_text_tokens(text: str) -> int:
    """
    Estimate token count for text content.
    
    Uses a simple heuristic: roughly 4 characters per token plus word count.
    This approximates the behavior of most modern tokenizers.
    
    Args:
        text: Text content to estimate
        
    Returns:
        int: Estimated token count
    """
    if not text or not isinstance(text, str):
        return 0
    
    # Simple estimation: 4 characters per token + word count adjustment
    char_tokens = len(text) // 4
    word_tokens = len(text.split())
    
    # Use the average of character-based and word-based estimates
    # This handles both dense text and whitespace-heavy content better
    estimated_tokens = (char_tokens + word_tokens) // 2
    
    # Minimum of 1 token for non-empty text
    return max(1, estimated_tokens) if text.strip() else 0

async def _estimate_tool_tokens(tool: Dict[str, Any]) -> int:
    """
    Estimate token count for tool definitions.
    
    Tool definitions include function names, descriptions, and parameter schemas
    which all contribute to the token count.
    
    Args:
        tool: Tool definition in Anthropic format
        
    Returns:
        int: Estimated token count for the tool
    """
    try:
        total_tokens = 0
        
        # Tool name tokens
        if 'name' in tool:
            total_tokens += await _estimate_text_tokens(tool['name'])
        
        # Tool description tokens
        if 'description' in tool:
            total_tokens += await _estimate_text_tokens(tool['description'])
        
        # Input schema tokens (parameters)
        if 'input_schema' in tool:
            schema = tool['input_schema']
            # Convert schema to text representation and estimate tokens
            schema_text = str(schema)  # Simple conversion for estimation
            total_tokens += await _estimate_text_tokens(schema_text)
        
        # Add overhead for tool structure (JSON formatting, etc.)
        total_tokens += 10  # Approximate overhead for tool JSON structure
        
        return total_tokens
        
    except Exception as e:
        logger.error(f"❌ Error estimating tool tokens: {e}")
        return 50  # Conservative estimate for a tool

async def estimate_max_output_tokens(model: str, input_tokens: int) -> int:
    """
    Estimate maximum output tokens based on model and input.
    
    Provides reasonable estimates for different Anthropic models based on
    their known context windows and typical usage patterns.
    
    Args:
        model: Anthropic model ID
        input_tokens: Estimated input token count
        
    Returns:
        int: Estimated maximum output tokens available
    """
    # Model context window limits (approximate)
    model_limits = {
        "claude-3-5-sonnet-latest": 200000,
        "claude-3-haiku-20240307": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-opus-20240229": 200000
    }
    
    # Get model limit, default to 200k for unknown models 
    max_context = model_limits.get(model, 200000)
    
    # Reserve some tokens for response formatting overhead
    overhead = 50
    available_output = max_context - input_tokens - overhead
    
    # Ensure we don't return negative values
    return max(0, available_output)

async def validate_token_limits(
    messages: List[Dict[str, Any]], 
    model: str,
    max_tokens: int,
    system: Optional[str] = None,
    tools: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Validate that request fits within model token limits.
    
    Checks input token count and requested output tokens against model limits
    and returns validation results with recommendations.
    
    Args:
        messages: Anthropic format messages
        model: Model ID to validate against
        max_tokens: Requested maximum output tokens
        system: Optional system message
        tools: Optional tool definitions
        
    Returns:
        Dict: Validation results with status and recommendations
    """
    try:
        # Count input tokens
        input_tokens = await count_tokens_async(messages, system, tools)
        
        # Get available output tokens
        max_output = await estimate_max_output_tokens(model, input_tokens)
        
        # Check if request is valid
        is_valid = max_tokens <= max_output
        
        result = {
            "valid": is_valid,
            "input_tokens": input_tokens,
            "requested_output_tokens": max_tokens,
            "max_available_output_tokens": max_output,
            "model": model
        }
        
        if not is_valid:
            result["error"] = f"Requested {max_tokens} output tokens exceeds limit of {max_output}"
            result["recommendation"] = f"Reduce max_tokens to {max_output} or shorten input"
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error validating token limits: {e}")
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}"
        }