#!/usr/bin/env python3
"""
OpenAI Specification Adapter Framework
======================================

Universal backend adapter system that normalizes responses from different LLM backends
to the OpenAI v1 specification format. Provides the "front-door" OpenAI compatibility
layer with intelligent backend routing and response normalization.

Key Features:
- Universal OpenAI v1 API compliance at the edge
- Backend-specific adapters for Anthropic, Gemini, and Salesforce models
- Capability-based routing using model_capabilities registry
- Tool call normalization across all backends
- Performance optimization with direct passthrough for OpenAI-native models

Architecture:
    Client Request (OpenAI format)
    ↓
    route_and_normalise() 
    ↓
    Backend-specific client call
    ↓
    Backend-specific normalizer
    ↓
    OpenAI v1 compliant response

Usage:
    from openai_spec_adapter import route_and_normalise
    
    openai_response = await route_and_normalise(request_payload, clients)
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
import logging

from model_capabilities import caps_for, get_backend_type
from openai_tool_fix import repair_openai_response

logger = logging.getLogger(__name__)

def _generate_call_id() -> str:
    """Generate a unique call ID for tool calls."""
    return f"call_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"

def _tool_call(name: str, args_obj: Dict[str, Any], call_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a properly formatted OpenAI tool call object.
    
    Args:
        name: Function name
        args_obj: Function arguments dictionary  
        call_id: Optional call ID (auto-generated if not provided)
        
    Returns:
        Dict: OpenAI-formatted tool call object
    """
    if call_id is None:
        call_id = _generate_call_id()
        
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args_obj, separators=(',', ':'), ensure_ascii=False)
        }
    }

def _create_openai_response(content: str, model: str, tool_calls: Optional[List[Dict[str, Any]]] = None, 
                           usage: Optional[Dict[str, Any]] = None, response_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized OpenAI response format.
    
    Args:
        content: Response text content
        model: Model name for the response
        tool_calls: Optional tool calls array
        usage: Optional usage statistics
        response_id: Optional response ID
        
    Returns:
        Dict: OpenAI v1 compliant response
    """
    if response_id is None:
        response_id = f"chatcmpl-{int(time.time())}{hash(str(tool_calls or content)) % 1000}"
    
    message = {
        "role": "assistant", 
        "content": content
    }
    
    if tool_calls:
        message["tool_calls"] = tool_calls
    
    return {
        "id": response_id,
        "object": "chat.completion", 
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": "tool_calls" if tool_calls else "stop"
        }],
        "usage": usage or {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None
        }
    }

def normalise_anthropic(raw_response: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    Normalize Anthropic/Bedrock responses to OpenAI v1 format.
    
    Handles both direct Anthropic API responses and Salesforce-wrapped responses
    that contain Anthropic-style content blocks and tool use events.
    
    Args:
        raw_response: Raw response from Anthropic/Bedrock API
        model: Model name for the normalized response
        
    Returns:
        Dict: OpenAI v1 compliant response
    """
    logger.debug(f"🔧 Normalizing Anthropic response for model: {model}")
    
    tool_calls = []
    call_id_counter = 1
    content = ""
    
    # Handle Salesforce-wrapped responses first
    if "generations" in raw_response and raw_response["generations"]:
        generation = raw_response["generations"][0]
        text = generation.get("text", generation.get("content", ""))
        
        # Try to extract tool calls from text if present
        if text and isinstance(text, str) and "<function_calls>" in text:
            # Use existing parsing logic from the system
            try:
                from tool_schemas import parse_tool_calls_from_response
                parsed_calls = parse_tool_calls_from_response(text)
                tool_calls.extend(parsed_calls)
                # Remove function_calls from content for clean response
                import re
                content = re.sub(r'<function_calls>.*?</function_calls>', '', text, flags=re.DOTALL).strip()
            except ImportError:
                # Fallback if tool_schemas not available
                content = text
        else:
            content = text or ""
    
    # Handle direct Anthropic API responses
    elif "events" in raw_response:
        for event in raw_response.get("events", []):
            if event.get("type") in ("tool_use", "message_tool_call"):
                tool_calls.append(_tool_call(
                    name=event.get("name", "unknown_function"),
                    args_obj=event.get("input", event.get("arguments", {})),
                    call_id=f"call_{call_id_counter}"
                ))
                call_id_counter += 1
            elif event.get("type") == "text" or "text" in event:
                content += event.get("text", "")
    
    # Handle standard content field
    elif "content" in raw_response:
        if isinstance(raw_response["content"], list):
            # Content blocks format
            for block in raw_response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")
                elif block.get("type") == "tool_use":
                    tool_calls.append(_tool_call(
                        name=block.get("name", "unknown_function"),
                        args_obj=block.get("input", {}),
                        call_id=f"call_{call_id_counter}"
                    ))
                    call_id_counter += 1
        else:
            content = str(raw_response["content"])
    
    # Handle simple text responses
    elif "text" in raw_response:
        content = str(raw_response["text"])
    
    # Extract usage information
    usage = None
    if "usage" in raw_response:
        anthropic_usage = raw_response["usage"]
        usage = {
            "prompt_tokens": anthropic_usage.get("input_tokens", anthropic_usage.get("prompt_tokens")),
            "completion_tokens": anthropic_usage.get("output_tokens", anthropic_usage.get("completion_tokens")),
            "total_tokens": anthropic_usage.get("total_tokens")
        }
        # Calculate total if not provided
        if not usage["total_tokens"] and usage["prompt_tokens"] and usage["completion_tokens"]:
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
    
    return _create_openai_response(
        content=content,
        model=model,
        tool_calls=tool_calls if tool_calls else None,
        usage=usage,
        response_id=raw_response.get("id", f"chatcmpl_anthropic_{int(time.time())}")
    )

def normalise_gemini(raw_response: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    Normalize Google Gemini/Vertex responses to OpenAI v1 format.
    
    Handles Gemini's functionCall format and converts to OpenAI tool_calls.
    
    Args:
        raw_response: Raw response from Gemini/Vertex API
        model: Model name for the normalized response
        
    Returns:
        Dict: OpenAI v1 compliant response
    """
    logger.debug(f"🔧 Normalizing Gemini response for model: {model}")
    
    tool_calls = []
    call_id_counter = 1
    content = ""
    
    # Handle Salesforce-wrapped Gemini responses
    if "generations" in raw_response and raw_response["generations"]:
        generation = raw_response["generations"][0]
        text = generation.get("text", generation.get("content", ""))
        content = text or ""
    
    # Handle direct Gemini responses
    elif "candidates" in raw_response:
        candidates = raw_response.get("candidates", [])
        if candidates:
            candidate = candidates[0]
            content_obj = candidate.get("content", {})
            parts = content_obj.get("parts", [])
            
            for part in parts:
                if "text" in part:
                    content += part["text"]
                elif "functionCall" in part:
                    func_call = part["functionCall"]
                    tool_calls.append(_tool_call(
                        name=func_call.get("name", "unknown_function"),
                        args_obj=func_call.get("args", {}),
                        call_id=f"call_{call_id_counter}"
                    ))
                    call_id_counter += 1
    
    # Handle simple text responses
    elif "text" in raw_response:
        content = str(raw_response["text"])
    
    # Extract usage information if available
    usage = None
    if "usage" in raw_response:
        gemini_usage = raw_response["usage"]
        usage = {
            "prompt_tokens": gemini_usage.get("promptTokenCount", gemini_usage.get("prompt_tokens")),
            "completion_tokens": gemini_usage.get("candidatesTokenCount", gemini_usage.get("completion_tokens")),
            "total_tokens": gemini_usage.get("totalTokenCount", gemini_usage.get("total_tokens"))
        }
    
    return _create_openai_response(
        content=content,
        model=model,
        tool_calls=tool_calls if tool_calls else None,
        usage=usage,
        response_id=raw_response.get("id", f"chatcmpl_gemini_{int(time.time())}")
    )

def normalise_generic(raw_response: Dict[str, Any], model: str) -> Dict[str, Any]:
    """
    Generic response normalizer for unknown backends.
    
    Attempts to intelligently parse common response formats and convert to OpenAI format.
    
    Args:
        raw_response: Raw response from unknown API
        model: Model name for the normalized response
        
    Returns:
        Dict: OpenAI v1 compliant response
    """
    logger.debug(f"🔧 Applying generic normalization for model: {model}")
    
    content = ""
    
    # Try common content extraction patterns
    if "generations" in raw_response and raw_response["generations"]:
        generation = raw_response["generations"][0]
        content = generation.get("text", generation.get("content", ""))
    elif "choices" in raw_response and raw_response["choices"]:
        # Already in OpenAI format
        return raw_response
    elif "content" in raw_response:
        content = str(raw_response["content"])
    elif "text" in raw_response:
        content = str(raw_response["text"])
    elif "response" in raw_response:
        content = str(raw_response["response"])
    else:
        # Last resort: convert entire response to string
        content = str(raw_response)
    
    return _create_openai_response(
        content=content or "No content generated",
        model=model,
        response_id=f"chatcmpl_generic_{int(time.time())}"
    )

async def route_and_normalise(payload: Dict[str, Any], clients: Any) -> Dict[str, Any]:
    """
    Universal request router and response normalizer.
    
    Routes requests to appropriate backends based on model capabilities and
    normalizes all responses to OpenAI v1 specification format.
    
    Args:
        payload: OpenAI-compatible request payload
        clients: Client instances for different backends (expected to have .openai, .anthropic, .gemini, .generic)
        
    Returns:
        Dict: OpenAI v1 compliant response
    """
    model_id = payload.get("model", "claude-3-haiku")
    capabilities = caps_for(model_id)
    backend_type = get_backend_type(model_id)
    tools = payload.get("tools")
    
    logger.info(f"🔧 Routing request: model={model_id}, backend={backend_type}")
    
    try:
        # Route based on capabilities
        normalized_response = None
        
        if capabilities.get("openai_compatible"):
            logger.debug(f"✅ Using OpenAI passthrough for {model_id}")
            # Direct passthrough with tool preservation
            if hasattr(clients, 'openai'):
                raw_response = await clients.openai.roundtrip(payload)
                # For OpenAI-compatible models, response may already be in correct format
                if "choices" in raw_response and "object" in raw_response:
                    normalized_response = raw_response  # Already in OpenAI format
                else:
                    normalized_response = normalise_generic(raw_response, model_id)
            else:
                # Fallback to generic client
                raw_response = await clients.generic.roundtrip(payload)
                normalized_response = normalise_generic(raw_response, model_id)
        
        elif capabilities.get("anthropic_bedrock"):
            logger.debug(f"🔧 Using Anthropic adapter for {model_id}")
            if hasattr(clients, 'anthropic'):
                raw_response = await clients.anthropic.roundtrip(payload)
            else:
                raw_response = await clients.generic.roundtrip(payload)
            normalized_response = normalise_anthropic(raw_response, model_id)
        
        elif capabilities.get("vertex_gemini"):
            logger.debug(f"🔧 Using Gemini adapter for {model_id}")
            if hasattr(clients, 'gemini'):
                raw_response = await clients.gemini.roundtrip(payload)
            else:
                raw_response = await clients.generic.roundtrip(payload)
            normalized_response = normalise_gemini(raw_response, model_id)
        
        else:
            logger.debug(f"🔧 Using generic adapter for {model_id}")
            # Generic fallback
            raw_response = await clients.generic.roundtrip(payload)
            normalized_response = normalise_generic(raw_response, model_id)
        
        # TOOL-CALL REPAIR: Apply universal repair shim for OpenAI compliance
        if normalized_response:
            repaired_response, was_repaired = repair_openai_response(normalized_response, tools)
            if was_repaired:
                logger.debug(f"🔧 Tool calls repaired in OpenAI Front-Door for model: {model_id}")
                normalized_response = repaired_response
        
        return normalized_response
    
    except Exception as e:
        logger.error(f"❌ Error in route_and_normalise for model {model_id}: {e}")
        # Return error response in OpenAI format
        return {
            "id": f"chatcmpl_error_{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                },
                "finish_reason": "error"
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "error": {
                "message": str(e),
                "type": "api_error"
            }
        }

def create_streaming_adapter(backend_type: str) -> callable:
    """
    Create a streaming adapter for a specific backend type.
    
    Args:
        backend_type: Backend type identifier
        
    Returns:
        callable: Streaming adapter function
    """
    async def stream_adapter(raw_stream: AsyncGenerator, model: str) -> AsyncGenerator[str, None]:
        """Convert backend streaming format to OpenAI Server-Sent Events format."""
        
        stream_id = f"chatcmpl-{int(time.time())}{hash(model) % 1000}"
        created = int(time.time())
        
        async for chunk in raw_stream:
            try:
                if backend_type == "openai_native":
                    # Direct passthrough for OpenAI-compatible streams
                    if isinstance(chunk, str) and chunk.startswith("data: "):
                        yield chunk
                    else:
                        # Convert to SSE format if needed
                        yield f"data: {json.dumps(chunk)}\n\n"
                
                elif backend_type == "anthropic_bedrock":
                    # Convert Anthropic streaming to OpenAI format
                    openai_chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": str(chunk)},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                
                elif backend_type == "vertex_gemini":
                    # Convert Gemini streaming to OpenAI format  
                    openai_chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": str(chunk)},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                
                else:
                    # Generic streaming format
                    openai_chunk = {
                        "id": stream_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": str(chunk)},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                    
            except Exception as e:
                logger.error(f"❌ Error in streaming adapter: {e}")
                # Send error chunk
                error_chunk = {
                    "id": stream_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "error": {"message": str(e), "type": "stream_error"}
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        # Send final completion chunk
        final_chunk = {
            "id": stream_id,
            "object": "chat.completion.chunk", 
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return stream_adapter

# Convenience exports
__all__ = [
    "route_and_normalise",
    "normalise_anthropic", 
    "normalise_gemini",
    "normalise_generic",
    "create_streaming_adapter"
]