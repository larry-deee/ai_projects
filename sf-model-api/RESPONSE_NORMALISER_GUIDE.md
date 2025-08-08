# Response Normaliser Guide

## Overview

The Response Normaliser is a comprehensive module that ensures consistent OpenAI-compatible `tool_calls` format across all backends (Anthropic, Vertex AI, Salesforce, etc.). It's a core component of the Tool Behaviour Compatibility Layer.

## Key Features

✅ **Unified OpenAI Format**: All backends produce identical `tool_calls` structure  
✅ **Cross-Backend Compatibility**: Seamless support for Anthropic, Vertex, OpenAI, Salesforce  
✅ **Thread-Safe Operations**: Safe for concurrent requests and async/await patterns  
✅ **Predictable Behavior**: `assistant.content` is empty when tools are called  
✅ **Consistent Finish Reasons**: Always returns "tool_calls" or "stop"  
✅ **High Performance**: Caching, async operations, and optimized JSON handling  

## Quick Start

```python
from src.response_normaliser import (
    to_openai_tool_call, 
    normalise_assistant_tool_response,
    normalise_response_async
)

# Convert individual tool call to OpenAI format
tool_call = to_openai_tool_call(
    name="get_weather",
    args_obj={"location": "NYC", "units": "metric"},
    call_id="call_123"
)

# Normalize assistant response
message = {"role": "assistant", "content": "I'll get the weather."}
tool_calls = [tool_call]

normalized_message = normalise_assistant_tool_response(message, tool_calls)
# Result: content is now empty, tool_calls are normalized
```

## Core Functions

### `to_openai_tool_call(name, args_obj, call_id)`

Converts a tool call to OpenAI format with JSON string arguments.

```python
# Example
tool_call = to_openai_tool_call(
    "calculate_mortgage",
    {
        "principal": 500000,
        "rate": 3.5,
        "term": 30
    },
    "call_mortgage_123"
)

# Returns:
{
    "id": "call_mortgage_123",
    "type": "function",
    "function": {
        "name": "calculate_mortgage", 
        "arguments": '{"principal":500000,"rate":3.5,"term":30}'
    }
}
```

### `normalise_assistant_tool_response(message, tool_calls, finish_reason_hint)`

Normalizes assistant response to consistent OpenAI schema.

**Key Behaviors:**
- 🔹 When tool calls are present: `content` becomes empty
- 🔹 When no tool calls: `content` is preserved
- 🔹 `tool_calls` array is normalized to OpenAI format
- 🔹 Thread-safe for concurrent requests

```python
# With tool calls - content becomes empty
message = {
    "role": "assistant",
    "content": "I'll help you with that task."
}

tool_calls = [{
    "id": "call_123",
    "type": "function", 
    "function": {
        "name": "process_data",
        "arguments": '{"data": "example"}'
    }
}]

result = normalise_assistant_tool_response(message, tool_calls)

# Result:
{
    "role": "assistant",
    "content": "",  # Now empty!
    "tool_calls": [...] # Normalized format
}
```

### `normalise_response_async(response, backend_type, model_name)`

Async response normalization for high-performance processing.

```python
import asyncio

async def normalize_response():
    # Anthropic response
    anthropic_response = {
        "content": [
            {"type": "text", "text": "I'll help you."},
            {"type": "tool_use", "name": "get_data", "input": {"id": 123}}
        ]
    }
    
    result = await normalise_response_async(
        anthropic_response, 
        "anthropic", 
        "claude-3-sonnet"
    )
    
    # Result includes metadata
    print(f"Processing time: {result.processing_time_ms}ms")
    print(f"Tool calls found: {result.tool_calls_count}")
    print(f"Finish reason: {result.finish_reason}")
    
    return result.normalized_response

# Run async
openai_format = asyncio.run(normalize_response())
```

## Backend-Specific Normalization

### Anthropic Claude

```python
# Original Anthropic format
anthropic_response = {
    "content": [
        {"type": "text", "text": "I'll get the weather."},
        {
            "type": "tool_use",
            "id": "toolu_123", 
            "name": "get_weather",
            "input": {"location": "NYC"}
        }
    ]
}

# Becomes OpenAI format
{
    "choices": [{
        "message": {
            "role": "assistant",
            "content": "",  # Empty when tool calls present
            "tool_calls": [{
                "id": "toolu_123",
                "type": "function",
                "function": {
                    "name": "get_weather", 
                    "arguments": '{"location":"NYC"}'
                }
            }]
        },
        "finish_reason": "tool_calls"
    }]
}
```

### Google Vertex AI

```python
# Original Vertex format  
vertex_response = {
    "candidates": [{
        "content": {
            "parts": [
                {"text": "Let me search for that."},
                {
                    "functionCall": {
                        "name": "search_web",
                        "args": {"query": "python tutorials"}
                    }
                }
            ]
        }
    }]
}

# Normalized to OpenAI format with consistent structure
```

### Salesforce-Hosted Models

```python
# Original Salesforce format
sf_response = {
    "generation": {
        "generatedText": "I'll process that data."
    },
    "tool_calls": [{
        "id": "call_sf_123",
        "function": {
            "name": "process_data",
            "arguments": {"batch_id": 456}
        }
    }]
}

# Normalized to standard OpenAI format
```

## Integration Examples

### With Unified Response Formatter

The response normaliser automatically integrates with the existing unified response formatter:

```python
# In unified_response_formatter.py
def format_openai_response(self, sf_response, model):
    # ... existing code ...
    
    # Response normaliser integration
    try:
        from response_normaliser import normalise_assistant_tool_response
        message = normalise_assistant_tool_response(message, tool_calls, finish_reason)
    except ImportError:
        # Fallback behavior
        if tool_calls:
            message["content"] = ""
```

### With Model Router

```python
# In model_router.py
def normalize_tool_response(self, response, model):
    capabilities = self.get_model_capabilities(model)
    
    if capabilities.supports_native_tools:
        # Even OpenAI-native models get normalized for consistency
        from response_normaliser import normalise_assistant_tool_response
        # ... normalization logic ...
    else:
        # Use async normalization for other backends
        from response_normaliser import default_normaliser
        result = await default_normaliser.normalise_response_async(
            response, capabilities.backend_type, model
        )
        return result.normalized_response
```

### With Tool Handler

```python
# In tool_handler.py
def _format_tool_response(self, response_text, tool_calls, tool_responses, model):
    # Use response normalizer for consistent formatting
    for call in tool_calls:
        from response_normaliser import to_openai_tool_call
        
        openai_call = to_openai_tool_call(
            call.function_name,
            call.function_arguments, 
            call.id
        )
        openai_tool_calls.append(openai_call)
    
    # Apply response normalization
    from response_normaliser import normalise_assistant_tool_response
    message = normalise_assistant_tool_response(message, openai_tool_calls)
```

## Performance Features

### Caching

- Automatic caching of normalized responses
- Thread-safe cache management
- Memory-bounded cache (max 1000 entries)
- High cache hit rates for repeated requests

### Async Operations

```python
# High-performance async normalization
async def process_multiple_responses(responses):
    tasks = [
        normalise_response_async(resp, "anthropic", "claude-3-haiku") 
        for resp in responses
    ]
    results = await asyncio.gather(*tasks)
    return [r.normalized_response for r in results]
```

### Performance Monitoring

```python
from src.response_normaliser import default_normaliser

# Get performance statistics
stats = default_normaliser.get_performance_stats()

print(f"Normalizations: {stats['normalizations_performed']}")
print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%") 
print(f"Avg time: {stats['avg_processing_time_ms']:.2f}ms")
print(f"Backend stats: {stats['backend_statistics']}")
```

## Error Handling

The response normaliser provides robust error handling:

```python
# Invalid inputs are handled gracefully
try:
    result = to_openai_tool_call("", {}, "call_123")  # Empty name
except ValueError as e:
    print(f"Caught expected error: {e}")

# Malformed tool calls don't crash the system  
malformed_calls = [{"invalid": "structure"}]
result = normalise_assistant_tool_response(message, malformed_calls)
# Returns safe fallback response

# None inputs handled gracefully
result = normalise_assistant_tool_response(None, None)
# Returns: {"role": "assistant", "content": ""}
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_response_normaliser.py

# Run specific test
python -m pytest test_response_normaliser.py::TestResponseNormaliser::test_to_openai_tool_call_basic -v

# Run demo
python demo_response_normaliser.py
```

## Environment Variables

Control response normaliser behavior:

```bash
# Enable debug mode for detailed logging
export RESPONSE_NORMALISER_DEBUG=true

# Control model router integration
export OPENAI_NATIVE_TOOL_PASSTHROUGH=1

# n8n compatibility settings
export N8N_COMPAT_PRESERVE_TOOLS=1
```

## Key Benefits

🎯 **Consistency**: All backends now produce identical OpenAI tool_calls format  
⚡ **Performance**: Optimized with caching and async operations  
🛡️ **Reliability**: Robust error handling prevents system crashes  
🔧 **Compatibility**: Works with existing unified response formatter and model router  
📈 **Scalability**: Thread-safe for high-concurrency deployments  
🔍 **Debugging**: Comprehensive logging and performance metrics  

## Migration Guide

If you're upgrading from the legacy tool calling system:

1. **No breaking changes** - Response normaliser integrates seamlessly
2. **Automatic activation** - Works through existing `format_openai_response()` calls  
3. **Enhanced behavior** - `assistant.content` now properly empty when tools called
4. **Performance gains** - Faster tool call processing with caching

The response normaliser ensures your sf-model-api provides consistent, high-performance tool calling across all supported backends while maintaining full backward compatibility.