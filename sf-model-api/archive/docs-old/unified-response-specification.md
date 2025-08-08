# Unified Response Formatting Specification

## Overview

This specification defines the standardized response formatting system for the Salesforce Models API Gateway to ensure 100% OpenAI and Anthropic API compliance across both synchronous and asynchronous server implementations.

## Design Principles

1. **API Specification Compliance:** Exact adherence to OpenAI OpenAPI 3.0 and Anthropic API specifications
2. **Response Consistency:** Identical inputs must produce identical responses across both servers
3. **Backward Compatibility:** No breaking changes to existing client integrations
4. **Performance Optimization:** Efficient response processing without sacrificing accuracy
5. **Error Transparency:** Clear, actionable error responses that aid debugging

## Unified Response Extraction Logic

### Priority-Based Response Text Extraction

```python
def extract_response_text_unified(sf_response: Dict[str, Any], debug_mode: bool = False) -> Optional[str]:
    """
    Unified response text extraction supporting all Salesforce API response formats.
    
    PRIORITY ORDER (based on frequency analysis):
    1. generation.generatedText (70% - sync server primary)
    2. generation.text (15% - sync server secondary) 
    3. generations[0].text (10% - legacy format)
    4. generationDetails.generations[0].content (3% - new format)
    5. Direct text/content fields (2% - fallback)
    
    Args:
        sf_response: Salesforce API response dictionary
        debug_mode: Enable detailed logging for debugging
        
    Returns:
        Optional[str]: Extracted text or None if extraction fails
    """
    if not isinstance(sf_response, dict):
        logger.error(f"Invalid response type: {type(sf_response)}")
        return None
    
    extraction_paths = [
        # Path 1: Standard Salesforce format (highest priority)
        ('generation', 'generatedText'),
        ('generation', 'text'),
        
        # Path 2: Legacy generations format  
        ('generations', 0, 'text'),
        ('generations', 0, 'content'),
        
        # Path 3: New generationDetails format
        ('generationDetails', 'generations', 0, 'content'),
        
        # Path 4: OpenAI-style format
        ('choices', 0, 'message', 'content'),
        ('choices', 0, 'text'),
        
        # Path 5: Direct fields
        ('text',),
        ('content',),
    ]
    
    for path in extraction_paths:
        try:
            current = sf_response
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and isinstance(key, int) and len(current) > key:
                    current = current[key]
                else:
                    raise KeyError(f"Path {path} failed at {key}")
            
            if isinstance(current, str) and current.strip():
                if debug_mode:
                    logger.debug(f"✅ Extracted via path: {' -> '.join(str(p) for p in path)}")
                return current.strip()
                
        except (KeyError, IndexError, TypeError):
            continue
    
    # Handle error responses
    if 'error' in sf_response:
        error_info = sf_response['error']
        if isinstance(error_info, dict):
            return f"API Error: {error_info.get('message', str(error_info))}"
        return f"API Error: {str(error_info)}"
    
    logger.warning(f"No extractable content found in response: {list(sf_response.keys())}")
    return None
```

### Unified Usage Information Extraction

```python
def extract_usage_info_unified(sf_response: Dict[str, Any]) -> Dict[str, int]:
    """
    Extract token usage information with consistent field mapping.
    
    PRIORITY ORDER:
    1. generationDetails.parameters.usage (new format)
    2. parameters.usage (standard format)  
    3. Direct usage field (fallback)
    4. Content-based estimation (last resort)
    
    Args:
        sf_response: Salesforce API response dictionary
        
    Returns:
        Dict[str, int]: OpenAI-compatible usage information
    """
    usage_default = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }
    
    usage_paths = [
        # Path 1: New generationDetails format
        ('generationDetails', 'parameters', 'usage'),
        
        # Path 2: Standard parameters format
        ('parameters', 'usage'),
        
        # Path 3: Direct usage field
        ('usage',),
    ]
    
    for path in usage_paths:
        try:
            current = sf_response
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    raise KeyError(f"Usage path {path} failed at {key}")
            
            if isinstance(current, dict):
                return {
                    "prompt_tokens": current.get('inputTokenCount', current.get('input_tokens', 0)),
                    "completion_tokens": current.get('outputTokenCount', current.get('output_tokens', 0)),
                    "total_tokens": current.get('totalTokenCount', current.get('total_tokens', 0))
                }
                
        except (KeyError, TypeError):
            continue
    
    # Fallback: estimate from content
    try:
        content = extract_response_text_unified(sf_response)
        if content:
            estimated_tokens = len(content.split()) + len(content) // 4
            return {
                "prompt_tokens": 0,  # Cannot estimate without original prompt
                "completion_tokens": estimated_tokens,
                "total_tokens": estimated_tokens
            }
    except Exception:
        pass
    
    return usage_default
```

## Standardized OpenAI Response Format

### Complete OpenAI Chat Completion Response

```python
def format_openai_response_unified(
    sf_response: Dict[str, Any], 
    model: str, 
    request_messages: List[Dict[str, Any]] = None,
    is_streaming: bool = False
) -> Dict[str, Any]:
    """
    Create OpenAI-compliant chat completion response with unified formatting.
    
    Args:
        sf_response: Raw Salesforce API response
        model: Model name for the response  
        request_messages: Original request messages for context
        is_streaming: Whether this is for streaming response
        
    Returns:
        Dict[str, Any]: OpenAI-compliant response object
    """
    # Extract core response data
    generated_text = extract_response_text_unified(sf_response)
    usage_info = extract_usage_info_unified(sf_response)
    
    # Handle extraction failures
    if generated_text is None:
        generated_text = "Error: Could not extract response from Salesforce API. Please try again."
    
    # Validate and sanitize content
    if not isinstance(generated_text, str):
        generated_text = str(generated_text) if generated_text else "Error: Invalid response format"
    
    # Prevent excessive response lengths
    if len(generated_text) > 100000:
        generated_text = generated_text[:100000] + "\n\n[Response truncated due to length limit]"
    
    # Generate consistent response ID
    response_id = f"chatcmpl-{int(time.time())}"
    created_timestamp = int(time.time())
    
    # Determine finish reason
    finish_reason = determine_finish_reason_unified(sf_response, generated_text)
    
    # Extract tool calls if present
    tool_calls = extract_tool_calls_unified(sf_response)
    
    # Build message object
    message = {
        "role": "assistant",
        "content": generated_text
    }
    
    # Add tool calls if present
    if tool_calls:
        message["tool_calls"] = tool_calls
    
    # Create OpenAI-compliant response
    openai_response = {
        "id": response_id,
        "object": "chat.completion",
        "created": created_timestamp,
        "model": model,
        "choices": [{
            "index": 0,
            "message": message,
            "finish_reason": finish_reason
        }],
        "usage": usage_info
    }
    
    # Add system fingerprint for reproducibility (if available)
    if 'system_fingerprint' in sf_response:
        openai_response['system_fingerprint'] = sf_response['system_fingerprint']
    
    return openai_response

def determine_finish_reason_unified(sf_response: Dict[str, Any], content: str) -> str:
    """
    Determine the finish reason based on response analysis.
    
    Returns:
        str: One of "stop", "length", "tool_calls", "content_filter"
    """
    # Check for tool calls in various response locations
    if has_tool_calls_unified(sf_response):
        return "tool_calls"
    
    # Check for content filtering
    if is_content_filtered_unified(sf_response):
        return "content_filter"
    
    # Check for length truncation
    if is_length_truncated_unified(sf_response, content):
        return "length"
    
    # Default to stop
    return "stop"
```

### Tool Calls Support

```python
def extract_tool_calls_unified(sf_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract tool calls from Salesforce response in OpenAI format.
    
    Args:
        sf_response: Salesforce API response
        
    Returns:
        List[Dict[str, Any]]: OpenAI-format tool calls array
    """
    tool_calls = []
    
    # Check multiple locations for tool calls
    tool_call_locations = [
        ('tool_calls',),
        ('choices', 0, 'message', 'tool_calls'),
        ('generationDetails', 'tool_calls'),
        ('message', 'tool_calls'),
    ]
    
    for path in tool_call_locations:
        try:
            current = sf_response
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and isinstance(key, int) and len(current) > key:
                    current = current[key]
                else:
                    raise KeyError
            
            if isinstance(current, list):
                # Validate and format tool calls
                for i, tool_call in enumerate(current):
                    if isinstance(tool_call, dict):
                        formatted_call = {
                            "id": tool_call.get('id', f"call_{i}_{int(time.time())}"),
                            "type": "function",
                            "function": {
                                "name": tool_call.get('function', {}).get('name', 'unknown'),
                                "arguments": tool_call.get('function', {}).get('arguments', '{}')
                            }
                        }
                        tool_calls.append(formatted_call)
                break
                
        except (KeyError, IndexError, TypeError):
            continue
    
    return tool_calls

def has_tool_calls_unified(sf_response: Dict[str, Any]) -> bool:
    """Check if response contains tool calls."""
    return len(extract_tool_calls_unified(sf_response)) > 0
```

## Standardized Error Response Format

### Unified Error Response Structure

```python
class UnifiedErrorResponse:
    """Standardized error response format across both servers."""
    
    @staticmethod
    def format_error_response(
        error: Union[Exception, str],
        error_type: str = "internal_error",
        error_code: str = None,
        model: str = "unknown",
        request_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error response.
        
        Args:
            error: The error that occurred
            error_type: Type classification of the error
            error_code: Specific error code
            model: Model that was being used
            request_context: Additional context about the request
            
        Returns:
            Dict[str, Any]: Standardized error response
        """
        error_message = str(error)
        
        # Determine error type and code if not provided
        if not error_code:
            error_code = classify_error_code(error_message)
        
        if not error_type:
            error_type = classify_error_type(error_message)
        
        # Build context information
        context = request_context or {}
        error_details = {
            "model_used": model,
            "timestamp": int(time.time()),
            "suggestion": generate_error_suggestion(error_message, context)
        }
        
        # Add request context if available
        if "prompt_length" in context:
            error_details["prompt_length"] = context["prompt_length"]
        if "messages_count" in context:
            error_details["messages_count"] = context["messages_count"]
        
        # Create OpenAI-compatible error response
        return {
            "error": {
                "message": error_message,
                "type": error_type,
                "code": error_code,
                "details": error_details
            }
        }
    
    @staticmethod
    def format_streaming_error(error: Exception, model: str = "unknown") -> str:
        """Format error for streaming response."""
        error_chunk = {
            "id": f"chatcmpl-error-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "error"
            }],
            "error": {
                "message": str(error),
                "type": "streaming_error"
            }
        }
        return f"data: {json.dumps(error_chunk)}\n\n"

def classify_error_code(error_message: str) -> str:
    """Classify error message into specific error code."""
    error_lower = error_message.lower()
    
    if any(auth_term in error_lower for auth_term in ['401', 'unauthorized', 'authentication', 'invalid_session']):
        return "authentication_error"
    elif any(rate_term in error_lower for rate_term in ['rate limit', '429', 'too many requests']):
        return "rate_limit_exceeded"
    elif any(timeout_term in error_lower for timeout_term in ['timeout', 'timed out', '408']):
        return "timeout_error"
    elif any(service_term in error_lower for service_term in ['503', '504', 'maintenance', 'unavailable']):
        return "service_unavailable"
    elif any(content_term in error_lower for content_term in ['content_filter', 'policy violation']):
        return "content_filter"
    else:
        return "internal_error"

def classify_error_type(error_message: str) -> str:
    """Classify error message into error type category."""
    error_code = classify_error_code(error_message)
    
    type_mapping = {
        "authentication_error": "authentication",
        "rate_limit_exceeded": "rate_limit", 
        "timeout_error": "timeout",
        "service_unavailable": "service_error",
        "content_filter": "content_filter",
        "internal_error": "server_error"
    }
    
    return type_mapping.get(error_code, "server_error")
```

## Anthropic API Response Format

### Anthropic Messages Response

```python
def format_anthropic_response_unified(
    sf_response: Dict[str, Any],
    model: str,
    request_messages: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create Anthropic-compliant message response.
    
    Args:
        sf_response: Raw Salesforce API response
        model: Model name for the response
        request_messages: Original request messages for token counting
        
    Returns:
        Dict[str, Any]: Anthropic-compliant response object
    """
    # Extract response data using unified extractors
    generated_text = extract_response_text_unified(sf_response)
    usage_info = extract_usage_info_unified(sf_response)
    
    # Handle extraction failures
    if generated_text is None:
        generated_text = "Error: Could not extract response from Salesforce API"
    
    # Generate response ID
    message_id = f"msg_{int(time.time())}"
    
    # Determine stop reason
    stop_reason = determine_anthropic_stop_reason(sf_response)
    
    # Create Anthropic response structure
    anthropic_response = {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "content": [{
            "type": "text",
            "text": generated_text
        }],
        "model": model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage_info.get("prompt_tokens", 0),
            "output_tokens": usage_info.get("completion_tokens", 0)
        }
    }
    
    return anthropic_response

def determine_anthropic_stop_reason(sf_response: Dict[str, Any]) -> str:
    """
    Determine Anthropic stop reason.
    
    Returns:
        str: One of "end_turn", "max_tokens", "stop_sequence", "tool_use"
    """
    if has_tool_calls_unified(sf_response):
        return "tool_use"
    elif is_length_truncated_unified(sf_response, None):
        return "max_tokens"
    else:
        return "end_turn"
```

## Streaming Response Format

### Unified Streaming Architecture

```python
class UnifiedStreamingFormatter:
    """Unified streaming response formatter for both servers."""
    
    def __init__(self, model: str, response_format: str = "openai"):
        self.model = model
        self.response_format = response_format
        self.response_id = f"chatcmpl-{int(time.time())}"
        self.created = int(time.time())
    
    def format_openai_stream(self, content: str, tool_calls: List[Dict] = None) -> Generator[str, None, None]:
        """Generate OpenAI-compatible streaming response."""
        
        # Send role delta first (OpenAI compliance)
        yield self._format_openai_chunk({"role": "assistant"})
        
        # Stream content in chunks
        if content:
            yield from self._stream_content_chunks(content)
        
        # Stream tool calls if present
        if tool_calls:
            yield from self._stream_tool_calls(tool_calls)
        
        # Send final chunk
        yield self._format_openai_chunk({}, finish_reason="stop" if not tool_calls else "tool_calls")
        
        # Send [DONE] marker
        yield "data: [DONE]\n\n"
    
    def _format_openai_chunk(self, delta: Dict[str, Any], finish_reason: str = None) -> str:
        """Format individual OpenAI streaming chunk."""
        chunk = {
            "id": self.response_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason
            }]
        }
        return f"data: {json.dumps(chunk)}\n\n"
    
    def _stream_content_chunks(self, content: str, chunk_size: int = 20) -> Generator[str, None, None]:
        """Stream content in word-based chunks."""
        words = content.split()
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Add space if not last chunk
            if i + chunk_size < len(words):
                chunk_text += " "
            
            yield self._format_openai_chunk({"content": chunk_text})
            
            # Small delay for streaming effect
            time.sleep(0.01)
```

## Implementation Guidelines

### 1. Shared Module Structure

```
src/
├── response_formatter/
│   ├── __init__.py
│   ├── unified_extractor.py      # Response text and usage extraction
│   ├── openai_formatter.py       # OpenAI-compliant formatting
│   ├── anthropic_formatter.py    # Anthropic-compliant formatting  
│   ├── error_formatter.py        # Unified error responses
│   ├── streaming_formatter.py    # Streaming response handling
│   └── validators.py             # Response format validation
```

### 2. Migration Strategy

1. **Phase 1:** Create shared module with unified logic
2. **Phase 2:** Update sync server to use unified formatters
3. **Phase 3:** Update async server to use unified formatters  
4. **Phase 4:** Remove old formatting code and add validation tests

### 3. Testing Requirements

```python
def test_response_consistency():
    """Ensure both servers return identical responses for identical inputs."""
    pass

def test_openai_compliance():
    """Validate responses against OpenAI API specification."""
    pass

def test_anthropic_compliance():
    """Validate responses against Anthropic API specification."""
    pass

def test_error_format_consistency():
    """Ensure error responses are consistent across servers."""
    pass
```

## Success Criteria

1. **100% API Compliance:** All responses pass OpenAI and Anthropic specification validation
2. **Response Consistency:** Identical responses for identical inputs across both servers
3. **Backward Compatibility:** No breaking changes to existing client integrations
4. **Performance Maintained:** No significant performance degradation
5. **Error Clarity:** Clear, actionable error messages for all failure scenarios

This specification provides the foundation for implementing a robust, compliant, and consistent response formatting system that ensures seamless API compatibility across both server implementations.