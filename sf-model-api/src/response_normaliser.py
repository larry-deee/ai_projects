#!/usr/bin/env python3
"""
Response Normaliser for Tool Behaviour Compatibility Layer
=========================================================

Comprehensive response normalization module that ensures consistent OpenAI-compatible 
tool_calls format across all backends (Anthropic, Vertex, Salesforce, etc.).

Key Features:
- Unified OpenAI tool_calls format conversion
- Cross-backend compatibility (Anthropic/Vertex → OpenAI format)
- Thread-safe operations with async/await support
- Predictable finish_reason determination ("tool_calls" or "stop")
- Consistent assistant.content handling (empty when tools are called)
- High-performance JSON serialization with proper escaping

Usage:
    from response_normaliser import to_openai_tool_call, normalise_assistant_tool_response
    
    # Convert individual tool call to OpenAI format
    tool_call = to_openai_tool_call("get_weather", {"location": "NYC"}, "call_123")
    
    # Normalize complete assistant response
    normalized = normalise_assistant_tool_response(message, tool_calls, "tool_calls")
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import lru_cache
import os

logger = logging.getLogger(__name__)

@dataclass
class NormalizationResult:
    """Result of response normalization with metadata."""
    normalized_response: Dict[str, Any]
    original_backend: str
    tool_calls_count: int
    content_modified: bool
    finish_reason: str
    processing_time_ms: float
    normalization_applied: bool = True

@dataclass
class ToolCallNormalization:
    """Configuration for tool call normalization."""
    ensure_string_arguments: bool = True
    validate_json_format: bool = True
    preserve_call_ids: bool = True
    generate_missing_ids: bool = True
    strict_openai_compliance: bool = True

class ResponseNormaliser:
    """
    High-performance response normalizer for Tool Behaviour Compatibility Layer.
    
    Ensures all backends produce consistent OpenAI-compatible tool_calls format
    with optimal performance through caching and async operations.
    """
    
    def __init__(self, config: Optional[ToolCallNormalization] = None):
        """
        Initialize response normalizer with configuration.
        
        Args:
            config: Optional normalization configuration
        """
        self.config = config or ToolCallNormalization()
        self.normalization_cache = {}
        self.cache_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
        
        # Performance metrics
        self.normalizations_performed = 0
        self.cache_hits = 0
        self.avg_processing_time = 0.0
        self.backend_stats = {}
        
        # Debug mode from environment
        self.debug_mode = os.getenv('RESPONSE_NORMALISER_DEBUG', 'false').lower() == 'true'
        
        logger.debug("🔧 ResponseNormaliser initialized with OpenAI compatibility mode")
    
    def to_openai_tool_call(self, name: str, args_obj: dict, call_id: str) -> Dict[str, Any]:
        """
        Convert tool call to OpenAI format with JSON string arguments.
        
        This is the core function that ensures consistent OpenAI tool_calls format
        regardless of the backend model used.
        
        Args:
            name: Function name
            args_obj: Function arguments as dictionary
            call_id: Unique tool call identifier
            
        Returns:
            Dict: OpenAI-compatible tool call object
        """
        # Validate inputs
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool call name must be a non-empty string")
        
        if not isinstance(args_obj, dict):
            raise ValueError("Tool call arguments must be a dictionary")
        
        if not isinstance(call_id, str) or not call_id.strip():
            call_id = f"call_{uuid.uuid4().hex[:8]}"
        
        try:
            # Convert arguments to JSON string with proper formatting
            # Use separators for compact JSON and ensure_ascii=False for proper Unicode handling
            arguments_json = json.dumps(
                args_obj, 
                separators=(",", ":"), 
                ensure_ascii=False,
                sort_keys=True  # For consistent output
            )
            
            # Validate JSON if strict compliance is enabled
            if self.config.validate_json_format:
                json.loads(arguments_json)  # Validate it can be parsed back
            
            openai_tool_call = {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": arguments_json
                }
            }
            
            if self.debug_mode:
                logger.debug(f"✅ Converted to OpenAI tool call: {name} -> {call_id}")
            
            return openai_tool_call
            
        except (TypeError, ValueError, json.JSONEncodeError) as e:
            logger.error(f"❌ Failed to convert tool call to OpenAI format: {name}, error: {e}")
            
            # Fallback with error handling
            return {
                "id": call_id,
                "type": "function", 
                "function": {
                    "name": name,
                    "arguments": json.dumps({"error": f"Invalid arguments: {str(e)}"})
                }
            }
    
    def normalise_assistant_tool_response(
        self, 
        message: Dict[str, Any], 
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        finish_reason_hint: str = "tool_calls"
    ) -> Dict[str, Any]:
        """
        Normalize assistant response to consistent OpenAI schema.
        
        Key behaviors:
        - Ensures assistant.content is empty when tools are called
        - Sets finish_reason predictably ("tool_calls" or "stop")  
        - Normalizes tool_calls array to OpenAI format
        - Maintains thread-safety for concurrent requests
        
        Args:
            message: Assistant message object to normalize
            tool_calls: Optional tool calls to include
            finish_reason_hint: Hint for finish reason determination
            
        Returns:
            Dict: Normalized assistant message in OpenAI format
        """
        start_time = time.time()
        
        try:
            # Create normalized message copy
            normalized_message = message.copy() if message else {}
            
            # Ensure required fields exist
            if "role" not in normalized_message:
                normalized_message["role"] = "assistant"
            
            # Handle tool calls presence
            if tool_calls and len(tool_calls) > 0:
                # When tool calls are present, content should be empty or minimal
                # This is critical for n8n and other OpenAI-compatible clients
                normalized_message["content"] = ""
                
                # Normalize each tool call to OpenAI format
                normalized_tool_calls = []
                for i, tool_call in enumerate(tool_calls):
                    try:
                        if isinstance(tool_call, dict):
                            # Extract tool call components
                            call_id = tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}")
                            
                            if "function" in tool_call:
                                function_data = tool_call["function"]
                                function_name = function_data.get("name", "unknown")
                                function_args = function_data.get("arguments", {})
                                
                                # Handle arguments that might already be JSON strings
                                if isinstance(function_args, str):
                                    try:
                                        # Try to parse as JSON to validate format
                                        parsed_args = json.loads(function_args)
                                        # Use parsed version for re-serialization to ensure consistency
                                        function_args = parsed_args
                                    except json.JSONDecodeError:
                                        # If invalid JSON string, wrap it
                                        function_args = {"raw_arguments": function_args}
                                
                                # Convert to OpenAI format
                                openai_call = self.to_openai_tool_call(
                                    function_name, 
                                    function_args, 
                                    call_id
                                )
                                normalized_tool_calls.append(openai_call)
                                
                            else:
                                # Handle malformed tool call
                                logger.warning(f"⚠️ Malformed tool call at index {i}: missing 'function' field")
                                continue
                        
                    except Exception as e:
                        logger.error(f"❌ Error normalizing tool call {i}: {e}")
                        continue
                
                # Set normalized tool calls
                if normalized_tool_calls:
                    normalized_message["tool_calls"] = normalized_tool_calls
                    finish_reason = "tool_calls"
                else:
                    # No valid tool calls found
                    normalized_message.pop("tool_calls", None)
                    finish_reason = "stop"
            else:
                # No tool calls - ensure content is present
                if "content" not in normalized_message or not normalized_message["content"]:
                    normalized_message["content"] = ""
                
                # Remove any existing tool_calls field
                normalized_message.pop("tool_calls", None)
                finish_reason = "stop"
            
            # Update performance metrics
            self.normalizations_performed += 1
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(processing_time)
            
            if self.debug_mode:
                tool_count = len(tool_calls) if tool_calls else 0
                logger.debug(f"✅ Normalized assistant response: {tool_count} tool calls, finish_reason: {finish_reason}")
            
            return normalized_message
            
        except Exception as e:
            logger.error(f"❌ Error normalizing assistant response: {e}")
            
            # Return safe fallback
            return {
                "role": "assistant",
                "content": message.get("content", "") if message else "Error processing response"
            }
    
    async def normalise_response_async(
        self,
        response: Dict[str, Any],
        backend_type: str = "salesforce",
        model_name: str = "unknown"
    ) -> NormalizationResult:
        """
        Async response normalization for high-performance concurrent processing.
        
        Args:
            response: Raw response from backend
            backend_type: Type of backend (anthropic, vertex, openai, salesforce)
            model_name: Model name for backend-specific handling
            
        Returns:
            NormalizationResult: Complete normalization result with metadata
        """
        start_time = time.time()
        
        try:
            # Check cache for repeated normalizations
            cache_key = self._generate_cache_key(response, backend_type)
            
            if self.cache_lock:
                async with self.cache_lock:
                    if cache_key in self.normalization_cache:
                        self.cache_hits += 1
                        cached_result = self.normalization_cache[cache_key]
                        if self.debug_mode:
                            logger.debug(f"🎯 Cache hit for {backend_type} response")
                        return cached_result
            
            # Apply backend-specific normalization
            if backend_type.lower() == "anthropic":
                normalized = await self._normalize_anthropic_async(response)
            elif backend_type.lower() == "vertex":
                normalized = await self._normalize_vertex_async(response)
            elif backend_type.lower() == "openai":
                normalized = await self._normalize_openai_async(response)
            else:
                # Default Salesforce normalization
                normalized = await self._normalize_salesforce_async(response)
            
            # Extract tool calls and normalize message
            tool_calls = normalized.get("choices", [{}])[0].get("message", {}).get("tool_calls", [])
            message = normalized.get("choices", [{}])[0].get("message", {})
            
            # Apply message normalization
            normalized_message = self.normalise_assistant_tool_response(
                message, 
                tool_calls, 
                "tool_calls" if tool_calls else "stop"
            )
            
            # Update response with normalized message
            if "choices" in normalized and normalized["choices"]:
                normalized["choices"][0]["message"] = normalized_message
                normalized["choices"][0]["finish_reason"] = "tool_calls" if tool_calls else "stop"
            
            # Create result
            processing_time = (time.time() - start_time) * 1000
            result = NormalizationResult(
                normalized_response=normalized,
                original_backend=backend_type,
                tool_calls_count=len(tool_calls),
                content_modified="content" in normalized_message,
                finish_reason="tool_calls" if tool_calls else "stop",
                processing_time_ms=processing_time,
                normalization_applied=True
            )
            
            # Cache result for performance
            if self.cache_lock:
                async with self.cache_lock:
                    self.normalization_cache[cache_key] = result
                    # Limit cache size to prevent memory leaks
                    if len(self.normalization_cache) > 1000:
                        # Remove oldest entries (simple FIFO)
                        oldest_keys = list(self.normalization_cache.keys())[:100]
                        for key in oldest_keys:
                            self.normalization_cache.pop(key, None)
            
            # Update backend statistics
            if backend_type not in self.backend_stats:
                self.backend_stats[backend_type] = {"count": 0, "avg_time": 0.0}
            
            self.backend_stats[backend_type]["count"] += 1
            self.backend_stats[backend_type]["avg_time"] = (
                (self.backend_stats[backend_type]["avg_time"] * (self.backend_stats[backend_type]["count"] - 1) + processing_time) 
                / self.backend_stats[backend_type]["count"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Async normalization failed for {backend_type}: {e}")
            
            # Return error result
            return NormalizationResult(
                normalized_response=response,
                original_backend=backend_type,
                tool_calls_count=0,
                content_modified=False,
                finish_reason="stop",
                processing_time_ms=(time.time() - start_time) * 1000,
                normalization_applied=False
            )
    
    async def _normalize_anthropic_async(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Anthropic Claude responses to OpenAI format.
        
        Anthropic uses a different response structure:
        - content is an array of content blocks
        - tool_use blocks contain function calls
        - stop_reason instead of finish_reason
        """
        try:
            # Create OpenAI-compatible response structure
            openai_response = {
                "id": response.get("id", f"chatcmpl-{int(time.time())}"),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": response.get("model", "claude-3-haiku"),
                "choices": [],
                "usage": {
                    "prompt_tokens": response.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": response.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": 0
                }
            }
            
            # Calculate total tokens
            openai_response["usage"]["total_tokens"] = (
                openai_response["usage"]["prompt_tokens"] + 
                openai_response["usage"]["completion_tokens"]
            )
            
            # Extract message content and tool calls
            content = response.get("content", [])
            message_content = ""
            tool_calls = []
            
            # Process Anthropic content blocks
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        message_content += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        # Convert Anthropic tool_use to OpenAI tool_calls format
                        tool_call = self.to_openai_tool_call(
                            block.get("name", "unknown"),
                            block.get("input", {}),
                            block.get("id", f"call_{uuid.uuid4().hex[:8]}")
                        )
                        tool_calls.append(tool_call)
            
            # Create choice object
            choice = {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": message_content.strip() if not tool_calls else ""
                },
                "finish_reason": "tool_calls" if tool_calls else "stop"
            }
            
            # Add tool calls if present
            if tool_calls:
                choice["message"]["tool_calls"] = tool_calls
            
            openai_response["choices"] = [choice]
            
            if self.debug_mode:
                logger.debug(f"✅ Normalized Anthropic response: {len(tool_calls)} tool calls")
            
            return openai_response
            
        except Exception as e:
            logger.error(f"❌ Anthropic normalization failed: {e}")
            return response
    
    async def _normalize_vertex_async(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Google Vertex AI responses to OpenAI format.
        
        Vertex AI has its own response structure with functionCall objects.
        """
        try:
            # Create OpenAI-compatible response structure
            openai_response = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": response.get("model", "gemini-pro"),
                "choices": [],
                "usage": {
                    "prompt_tokens": response.get("usageMetadata", {}).get("promptTokenCount", 0),
                    "completion_tokens": response.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                    "total_tokens": response.get("usageMetadata", {}).get("totalTokenCount", 0)
                }
            }
            
            # Extract candidates and process
            candidates = response.get("candidates", [])
            if candidates:
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                
                message_content = ""
                tool_calls = []
                
                # Process Vertex AI parts
                for part in parts:
                    if isinstance(part, dict):
                        if "text" in part:
                            message_content += part["text"]
                        elif "functionCall" in part:
                            # Convert Vertex functionCall to OpenAI format
                            func_call = part["functionCall"]
                            tool_call = self.to_openai_tool_call(
                                func_call.get("name", "unknown"),
                                func_call.get("args", {}),
                                f"call_{uuid.uuid4().hex[:8]}"
                            )
                            tool_calls.append(tool_call)
                
                # Create choice object
                choice = {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": message_content.strip() if not tool_calls else ""
                    },
                    "finish_reason": "tool_calls" if tool_calls else "stop"
                }
                
                # Add tool calls if present
                if tool_calls:
                    choice["message"]["tool_calls"] = tool_calls
                
                openai_response["choices"] = [choice]
            
            if self.debug_mode:
                tool_count = len(openai_response.get("choices", [{}])[0].get("message", {}).get("tool_calls", []))
                logger.debug(f"✅ Normalized Vertex response: {tool_count} tool calls")
            
            return openai_response
            
        except Exception as e:
            logger.error(f"❌ Vertex normalization failed: {e}")
            return response
    
    async def _normalize_openai_async(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize OpenAI responses (passthrough with validation).
        
        For OpenAI-native responses, we primarily validate format and ensure
        tool_calls are properly structured.
        """
        try:
            # OpenAI responses should already be in correct format
            # But we still normalize tool_calls for consistency
            if "choices" in response and response["choices"]:
                choice = response["choices"][0]
                message = choice.get("message", {})
                tool_calls = message.get("tool_calls", [])
                
                if tool_calls:
                    # Re-normalize tool calls to ensure format consistency
                    normalized_tool_calls = []
                    for tool_call in tool_calls:
                        if isinstance(tool_call, dict) and "function" in tool_call:
                            function = tool_call["function"]
                            normalized_call = self.to_openai_tool_call(
                                function.get("name", "unknown"),
                                json.loads(function.get("arguments", "{}")) if isinstance(function.get("arguments"), str) else function.get("arguments", {}),
                                tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}")
                            )
                            normalized_tool_calls.append(normalized_call)
                    
                    # Update response with normalized tool calls
                    response["choices"][0]["message"]["tool_calls"] = normalized_tool_calls
                    response["choices"][0]["message"]["content"] = ""  # Ensure empty content with tool calls
                    response["choices"][0]["finish_reason"] = "tool_calls"
            
            if self.debug_mode:
                logger.debug("✅ Validated OpenAI response format")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ OpenAI normalization failed: {e}")
            return response
    
    async def _normalize_salesforce_async(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Salesforce-hosted model responses to OpenAI format.
        
        Salesforce responses need significant transformation to OpenAI format.
        """
        try:
            # Use unified response formatter for basic extraction
            from unified_response_formatter import UnifiedResponseFormatter
            formatter = UnifiedResponseFormatter()
            
            # Create basic OpenAI response
            openai_response = formatter.format_openai_response(response, response.get("model", "claude-3-haiku"))
            
            # Extract and normalize tool calls if present
            tool_calls = formatter.extract_tool_calls(response)
            if tool_calls:
                # Ensure tool calls are in proper OpenAI format
                normalized_tool_calls = []
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict):
                        function = tool_call.get("function", {})
                        args = function.get("arguments", "{}")
                        
                        # Parse arguments if they're a string
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {"raw_arguments": args}
                        
                        normalized_call = self.to_openai_tool_call(
                            function.get("name", "unknown"),
                            args,
                            tool_call.get("id", f"call_{uuid.uuid4().hex[:8]}")
                        )
                        normalized_tool_calls.append(normalized_call)
                
                # Update response with normalized tool calls
                if "choices" in openai_response and openai_response["choices"]:
                    openai_response["choices"][0]["message"]["tool_calls"] = normalized_tool_calls
                    openai_response["choices"][0]["message"]["content"] = ""
                    openai_response["choices"][0]["finish_reason"] = "tool_calls"
            
            if self.debug_mode:
                tool_count = len(tool_calls) if tool_calls else 0
                logger.debug(f"✅ Normalized Salesforce response: {tool_count} tool calls")
            
            return openai_response
            
        except Exception as e:
            logger.error(f"❌ Salesforce normalization failed: {e}")
            # Fallback to basic response
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion", 
                "created": int(time.time()),
                "model": response.get("model", "unknown"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": str(response)
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
    
    def _generate_cache_key(self, response: Dict[str, Any], backend_type: str) -> str:
        """Generate cache key for response normalization."""
        import hashlib
        
        # Create a hash of the response structure for caching
        response_str = json.dumps(response, sort_keys=True)
        return f"{backend_type}:{hashlib.md5(response_str.encode()).hexdigest()[:16]}"
    
    def _update_performance_metrics(self, processing_time_ms: float) -> None:
        """Update performance metrics in thread-safe manner."""
        # Simple moving average for processing time
        if self.avg_processing_time == 0.0:
            self.avg_processing_time = processing_time_ms
        else:
            # Exponential moving average with alpha=0.1
            self.avg_processing_time = 0.1 * processing_time_ms + 0.9 * self.avg_processing_time
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        total_operations = self.normalizations_performed
        cache_hit_rate = (self.cache_hits / total_operations * 100) if total_operations > 0 else 0
        
        return {
            "normalizations_performed": self.normalizations_performed,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "avg_processing_time_ms": self.avg_processing_time,
            "backend_statistics": self.backend_stats.copy(),
            "cache_size": len(self.normalization_cache),
            "debug_mode": self.debug_mode
        }
    
    def clear_cache(self) -> None:
        """Clear normalization cache."""
        self.normalization_cache.clear()
        self.cache_hits = 0
        logger.info("🧹 Response normalization cache cleared")


# Global instance for easy import and use
default_normaliser = ResponseNormaliser()

# Convenience functions for backward compatibility
def to_openai_tool_call(name: str, args_obj: dict, call_id: str) -> Dict[str, Any]:
    """
    Convenience function to convert tool call to OpenAI format.
    
    Args:
        name: Function name
        args_obj: Function arguments as dictionary
        call_id: Unique tool call identifier
        
    Returns:
        Dict: OpenAI-compatible tool call object
    """
    return default_normaliser.to_openai_tool_call(name, args_obj, call_id)

def normalise_assistant_tool_response(
    message: Dict[str, Any], 
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    finish_reason_hint: str = "tool_calls"
) -> Dict[str, Any]:
    """
    Convenience function to normalize assistant response.
    
    Args:
        message: Assistant message object to normalize
        tool_calls: Optional tool calls to include
        finish_reason_hint: Hint for finish reason determination
        
    Returns:
        Dict: Normalized assistant message in OpenAI format
    """
    return default_normaliser.normalise_assistant_tool_response(message, tool_calls, finish_reason_hint)

async def normalise_response_async(
    response: Dict[str, Any],
    backend_type: str = "salesforce",
    model_name: str = "unknown"
) -> NormalizationResult:
    """
    Convenience function for async response normalization.
    
    Args:
        response: Raw response from backend
        backend_type: Type of backend (anthropic, vertex, openai, salesforce)
        model_name: Model name for backend-specific handling
        
    Returns:
        NormalizationResult: Complete normalization result with metadata
    """
    return await default_normaliser.normalise_response_async(response, backend_type, model_name)

# Export key components
__all__ = [
    "ResponseNormaliser",
    "NormalizationResult", 
    "ToolCallNormalization",
    "to_openai_tool_call",
    "normalise_assistant_tool_response",
    "normalise_response_async",
    "default_normaliser"
]