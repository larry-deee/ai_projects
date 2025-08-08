# Response Format Implementation Guide

This guide provides detailed implementation instructions for standardizing response formatting between the synchronous and asynchronous servers using the unified_response_formatter module.

## Server Modifications

### 1. Sync Server (`llm_endpoint_server.py`)

#### Import Changes

Add the following imports at the top of the file:

```python
from unified_response_formatter import (
    extract_response_text_unified,
    format_openai_response_unified,
    format_anthropic_response_unified,
    format_error_response_unified,
    add_n8n_compatible_headers
)
```

#### Function Replacements

Replace `extract_response_text_optimized` with `extract_response_text_unified`:

```python
# BEFORE:
generated_text = extract_response_text_optimized(sf_response, debug_mode)

# AFTER:
generated_text = extract_response_text_unified(sf_response)
```

Replace `format_openai_response_optimized` with `format_openai_response_unified`:

```python
# BEFORE:
openai_response = format_openai_response_optimized(sf_response, model, is_streaming)

# AFTER:
openai_response = format_openai_response_unified(sf_response, model)
```

Replace Anthropic response formatting:

```python
# BEFORE (the manual formatting):
anthropic_response = {
    "id": f"msg_{int(time.time())}",
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
        "input_tokens": usage_info.get("prompt_tokens", 0),
        "output_tokens": usage_info.get("completion_tokens", 0)
    }
}

# AFTER:
anthropic_response = format_anthropic_response_unified(sf_response, model)
```

Add n8n header support by adding this function:

```python
def add_n8n_compatible_headers(response):
    """
    Add n8n-compatible headers to ensure proper content type validation.
    
    Args:
        response: Flask response object
        
    Returns:
        Response object with n8n-compatible headers
    """
    from unified_response_formatter import add_n8n_compatible_headers as add_headers
    return add_headers(response)
```

#### Apply n8n Headers

Update response return statements to apply n8n headers:

```python
# BEFORE:
return jsonify(openai_response)

# AFTER:
return add_n8n_compatible_headers(jsonify(openai_response))
```

#### Error Response Formatting

Replace error response formatting:

```python
# BEFORE:
error_response = jsonify({"error": str(e)})
return error_response, 500

# AFTER:
error_response = format_error_response_unified(e, model)
return add_n8n_compatible_headers(jsonify(error_response)), 500
```

### 2. Async Server (`async_endpoint_server.py`)

#### Import Changes

Add the following imports at the top of the file:

```python
from unified_response_formatter import (
    extract_response_text_unified,
    format_openai_response_unified,
    format_anthropic_response_unified,
    format_error_response_unified,
    add_n8n_compatible_headers
)
```

#### Function Replacements

Replace `extract_content_from_response` with `extract_response_text_unified`:

```python
# BEFORE:
def extract_content_from_response(response: Dict[str, Any]) -> Optional[str]:
    # Function implementation
    ...

# Call site:
content = extract_content_from_response(response)

# AFTER:
# Remove the function definition and use the unified version:
content = extract_response_text_unified(response)
```

Replace `format_openai_response_async` with `format_openai_response_unified`:

```python
# BEFORE:
async def format_openai_response_async(sf_response: Dict[str, Any], model: str, is_streaming: bool = False) -> Dict[str, Any]:
    # Function implementation
    ...

# Call site:
openai_response = await format_openai_response_async(response, model)

# AFTER:
# Remove the function definition and use the unified version:
openai_response = format_openai_response_unified(response, model)
```

Update n8n header implementation to use the unified version:

```python
# BEFORE:
def add_n8n_compatible_headers(response):
    # Function implementation
    ...

# AFTER:
# Import and use the unified version, no need for async syntax since it's a simple function
```

#### Error Response Formatting

Replace error response formatting:

```python
# BEFORE:
error_response = jsonify({"error": str(e)})
return add_n8n_compatible_headers(error_response), 500

# AFTER:
error_response = format_error_response_unified(e, model)
return add_n8n_compatible_headers(jsonify(error_response)), 500
```

### 3. Tool Handler (`tool_handler.py`)

#### Import Changes

Add the following imports:

```python
from unified_response_formatter import (
    format_openai_response_unified,
    format_error_response_unified
)
```

#### Function Replacements

Replace `_format_error_response` with the unified version:

```python
# BEFORE:
def _format_error_response(self, error_message: str, model: str) -> Dict[str, Any]:
    # Function implementation
    ...

# AFTER:
def _format_error_response(self, error_message: str, model: str) -> Dict[str, Any]:
    """Format error response using unified formatter."""
    return format_error_response_unified(error_message, model=model)
```

Update tool call response formatting to use a consistent approach:

```python
# BEFORE:
def _format_tool_response(
    self,
    response_text: str,
    tool_calls: List[ToolCall],
    tool_responses: List[Any],
    model: str
) -> Dict[str, Any]:
    """Format response with tool calls."""
    
    # Build OpenAI-compatible response
    choice = {
        "index": 0,
        "message": {
            "role": "assistant",
            "content": response_text,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function_name,
                        "arguments": json.dumps(call.function_arguments)
                    }
                }
                for call in tool_calls
            ]
        },
        "finish_reason": "tool_calls"
    }
    
    response = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [choice],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
    
    # Store tool calls in conversation state
    self.conversation_state.last_assistant_tool_calls = tool_calls
    
    return response

# AFTER:
def _format_tool_response(
    self,
    response_text: str,
    tool_calls: List[ToolCall],
    tool_responses: List[Any],
    model: str
) -> Dict[str, Any]:
    """Format response with tool calls using unified formatter."""
    
    # Convert ToolCall objects to dictionaries for the unified formatter
    tool_calls_dicts = [
        {
            "id": call.id,
            "function_name": call.function_name,
            "function_arguments": call.function_arguments
        }
        for call in tool_calls
    ]
    
    # Create response using unified formatter
    from unified_response_formatter import format_tool_response
    response = format_tool_response(response_text, tool_calls_dicts, tool_responses, model)
    
    # Store tool calls in conversation state
    self.conversation_state.last_assistant_tool_calls = tool_calls
    
    return response
```

## Parameter Contamination Fix

The critical parameter contamination bug in the sync server's tool calling can be fixed by ensuring proper parameter handling:

```python
# BEFORE (in llm_endpoint_server.py):
# Location of the bug - in tool calling function
sf_response = client.generate_text(
    prompt=enhanced_prompt,
    model=model,
    system_message=system_message,
    max_tokens=max_tokens,
    temperature=temperature,
    tools=tools,  # Bug: passing unsupported parameters
    tool_choice=tool_choice  # Bug: passing unsupported parameters
)

# AFTER:
sf_response = client.generate_text(
    prompt=enhanced_prompt,
    model=model,
    system_message=system_message,
    max_tokens=max_tokens,
    temperature=temperature
    # Remove unsupported parameters
)
```

## Testing and Validation

### Response Consistency Test

Create a simple test script to validate response consistency across both servers:

```python
def test_response_consistency():
    """Test that both servers produce identical responses for the same input."""
    from unified_response_formatter import format_openai_response_unified
    from llm_endpoint_server import format_openai_response_optimized
    from async_endpoint_server import format_openai_response_async
    
    # Test cases with different response formats
    test_cases = [
        {"generation": {"generatedText": "Sample response"}},
        {"generations": [{"text": "Sample response"}]},
        {"generationDetails": {"generations": [{"content": "Sample response"}]}},
    ]
    
    for tc in test_cases:
        model = "claude-3-haiku"
        
        # Generate responses using all formatters
        unified = format_openai_response_unified(tc, model)
        sync = format_openai_response_optimized(tc, model)
        async_format = format_openai_response_async(tc, model)
        
        # Compare response structures (ignoring dynamic fields like id and timestamp)
        assert unified['choices'][0]['message']['content'] == sync['choices'][0]['message']['content']
        assert unified['choices'][0]['message']['content'] == async_format['choices'][0]['message']['content']
        
        print(f"✅ Response consistency validated for format: {list(tc.keys())[0]}")
```

### Client Compatibility Test

Test with various OpenAI clients to ensure backward compatibility:

```bash
# Test with curl
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku", 
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Test with n8n (specific headers)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "n8n-version: 1.0.0" \
  -d '{
    "model": "claude-3-haiku", 
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Test with tool calling
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku", 
    "messages": [{"role": "user", "content": "What time is it?"}],
    "tools": [{"type": "function", "function": {"name": "get_time", "description": "Get the current time", "parameters": {}}}],
    "tool_choice": "auto"
  }'
```

## Migration Checklist

- [ ] Update imports in both servers
- [ ] Replace response extraction functions
- [ ] Replace OpenAI response formatters
- [ ] Replace Anthropic response formatters
- [ ] Add n8n header support to sync server
- [ ] Update tool handler response formatting
- [ ] Fix parameter contamination bug
- [ ] Update streaming response formats
- [ ] Update error response formats
- [ ] Run response consistency tests
- [ ] Run client compatibility tests
- [ ] Monitor error rates after deployment

## Potential Issues and Solutions

1. **Performance Impact**:
   - **Issue**: The unified formatter might have performance overhead due to more complex extraction logic.
   - **Solution**: Profile the performance and optimize critical paths if needed.

2. **Backward Compatibility**:
   - **Issue**: Some clients may depend on specific response format quirks.
   - **Solution**: Maintain backward compatibility by ensuring all essential fields are preserved.

3. **Error Handling Differences**:
   - **Issue**: Different error handling approaches between servers.
   - **Solution**: Use unified error formats but preserve existing HTTP status codes.

4. **Tool Calling Edge Cases**:
   - **Issue**: Tool calling is complex with many edge cases.
   - **Solution**: Add comprehensive tests for tool calling scenarios.

## Conclusion

By following this implementation guide, the response formatting will be fully standardized between the sync and async servers, ensuring 100% OpenAI and Anthropic API compliance. The unified formatter provides a single source of truth for response formatting logic, eliminating drift and improving maintainability.