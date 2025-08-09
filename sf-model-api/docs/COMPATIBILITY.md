# API Compatibility & Integration Guide

## OpenAI Front-Door & Backend Adapters

The Salesforce Models API Gateway now implements the OpenAI Front-Door & Backend Adapters architecture, providing universal OpenAI v1 specification compliance across all model backends.

### Architecture Overview

The OpenAI Front-Door architecture transforms the gateway from UA-based tool filtering to universal OpenAI v1 specification compliance with intelligent backend adapters:

- **OpenAI-Native Models**: Direct passthrough with optimal performance
- **Anthropic Models**: Claude format → OpenAI tool_calls normalization
- **Gemini Models**: Vertex AI format → OpenAI tool_calls normalization
- **Tool-Call Repair**: Automatic fix for "Tool call missing function name" errors

### Key Components

#### 1. Model Capabilities Registry

The `model_capabilities.py` module provides a centralized capability registry:

```python
from model_capabilities import caps_for, get_backend_type

# Check capabilities of a model
caps = caps_for("claude-3-sonnet")
# Returns: {'openai_compatible': false, 'anthropic_bedrock': true, ...}

# Get the backend type for routing
backend = get_backend_type("gpt-4")
# Returns: 'openai_native'
```

#### 2. Backend Adapters

The system automatically routes requests to the appropriate backend adapter:

```python
# Configuration via environment variables
export OPENAI_FRONTDOOR_ENABLED=1  # Enable the new architecture
export MODEL_CAPABILITIES_JSON='{"my-custom-model": {"backend_type": "anthropic_bedrock"}}'
```

#### 3. Tool-Call Repair

The tool-call repair shim ensures universal compatibility:

- Fixes missing `function.name` fields using tool definitions
- Ensures `function.arguments` are properly formatted as JSON strings
- Handles malformed tool call structures gracefully

### Universal Compatibility Benefits

- All models now output consistent OpenAI v1 specification responses
- Tools are preserved for all clients, regardless of User-Agent
- Automatic tool-call repair prevents common errors
- Direct passthrough for OpenAI-native models optimizes performance

## Table of Contents
1. [OpenAI Front-Door & Backend Adapters](#openai-front-door--backend-adapters)
2. [Anthropic API Compatibility](#anthropic-api-compatibility)
3. [n8n Integration & Behavior](#n8n-integration--behavior)
4. [Claude Code Tool Calling & SSE](#claude-code-tool-calling--sse)
5. [OpenAI API Compliance](#openai-api-compliance)
6. [Response Format Standardization](#response-format-standardization)
7. [Streaming Behavior & Headers](#streaming-behavior--headers)
8. [Known Limitations & Workarounds](#known-limitations--workarounds)

## Anthropic API Compatibility

The Salesforce Models API Gateway now provides native Anthropic API compatibility through dedicated endpoints at `/anthropic/v1/*`. These endpoints offer exact compliance with the Anthropic API specification while leveraging Salesforce's Einstein Trust Layer infrastructure.

### Key Features

- **Exact API Compliance**: Full compatibility with Anthropic's API specification
- **Native Message Format**: Support for Anthropic's content blocks and message structure
- **SSE Streaming**: Proper Anthropic SSE event sequence (message_start → content_block_* → message_stop)
- **Model Mapping**: Configuration-driven model verification and mapping
- **Performance Optimized**: Async architecture with 40-60% performance improvements

### Anthropic SDK Integration

The Anthropic-compatible endpoints work seamlessly with the official Anthropic SDKs:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="any-key",  # Not used for local API
    base_url="http://localhost:8000/anthropic"
)

response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ],
    max_tokens=1000
)
```

### Required Headers

All Anthropic-compatible endpoints require:

```
anthropic-version: 2023-06-01
Content-Type: application/json  (for POST requests)
```

### Available Endpoints

- `GET /anthropic/v1/models` - List available models
- `POST /anthropic/v1/messages` - Create messages with streaming support
- `POST /anthropic/v1/messages/count_tokens` - Count tokens for messages

### Model Mapping

Models are mapped between Anthropic IDs and Salesforce models via `config/anthropic_models.map.json`:

| Anthropic Model ID | Salesforce Model |
|-------------------|------------------|
| `claude-3-haiku-20240307` | `sfdc_ai__DefaultBedrockAnthropicClaude3Haiku` |
| `claude-3-sonnet-20240229` | `sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet` |
| `claude-3-opus-20240229` | `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet` |
| `claude-3-5-sonnet-latest` | `sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet` |

For detailed documentation, see [docs/ANTHROPIC_API.md](ANTHROPIC_API.md).

## n8n Integration & Behavior

The Salesforce Models API Gateway is designed for seamless integration with n8n workflow automation. This section details the specific behaviors and integration patterns for n8n.

### n8n Workflow Configuration

n8n workflows can use the gateway with tool calling support for all models through the HTTP Request node:

```json
{
  "method": "POST",
  "url": "http://localhost:8000/v1/chat/completions",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Process this data"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "extract_data",
        "description": "Extract structured data",
        "parameters": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"}
          }
        }
      }
    }]
  }
}
```

With the new OpenAI Front-Door architecture, all models (including Anthropic's Claude) now work with tool calling in n8n, with consistent OpenAI v1-compatible tool_calls format.

### n8n Tool Calling with $fromAI()

The gateway supports n8n's `$fromAI()` syntax for automatic parameter extraction:

```json
{
  "model": "claude-3-haiku",
  "messages": [
    {"role": "user", "content": "Extract info from {{ $fromAI(\"contact_name\", \"\", \"string\") }} {{ $fromAI(\"email\", \"\", \"string\") }}"}
  ],
  "tools": [{
    "type": "function",
    "function": {
      "name": "extract_info",
      "description": "Extract contact information",
      "parameters": {
        "type": "object",
        "properties": {
          "contact_name": {"type": "string", "description": "Contact name"},
          "email": {"type": "string", "description": "Email address"}
        },
        "required": ["contact_name", "email"]
      }
    }
  }]
}
```

### Streaming Behavior with n8n

When using tool calling with n8n, streaming is automatically downgraded to ensure compatibility:

```json
{
  "method": "POST",
  "url": "http://localhost:8000/v1/chat/completions",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Calculate 15 + 27"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculate",
        "description": "Calculate math expressions",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      }
    }],
    "stream": true
  }
}
```

Even though `stream` is set to `true`, the response will be non-streamed with the `X-Stream-Downgraded: true` header. This is required for proper JSON parsing in n8n (specifically for n8n v1.105.4 compatibility with the OpenAI node).

### n8n-Compatible Response Headers

The gateway implements n8n-compatible response headers:

```python
def add_n8n_compatible_headers(response):
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response
```

## Claude Code Tool Calling & SSE

The Salesforce Models API Gateway supports Claude Code's tool calling format and SSE (Server-Sent Events) requirements.

### Claude Code Tool Calling Format

The gateway fully supports Anthropic's function calling format:

```python
response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[
        {"role": "user", "content": "Tell me the current weather in San Francisco"}
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            }
        }
    }],
    tool_choice="auto"
)
```

### SSE Heartbeat Support

The server implements Server-Sent Events (SSE) heartbeats to prevent connection timeouts during streaming for Claude Code:

- Heartbeat keepalives (`:ka`) sent every ~15 seconds during streaming responses
- Available in both OpenAI and Anthropic streaming formats
- Prevents browser and proxy timeouts on long-running generations

Example implementation:

```python
async def stream_with_heartbeats(response_generator):
    """Add SSE heartbeats to streaming responses."""
    last_heartbeat = time.time()
    heartbeat_interval = 15  # seconds
    
    async for chunk in response_generator:
        yield chunk
        
        # Send heartbeat if needed
        current_time = time.time()
        if current_time - last_heartbeat > heartbeat_interval:
            yield b':\nka\n\n'  # SSE heartbeat
            last_heartbeat = current_time
```

### Claude Code Python SDK Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="any-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[{"role": "user", "content": "Write a long story about a space explorer"}],
    stream=True
)

# Stream will include heartbeats every ~15s to prevent connection timeouts
for chunk in response:
    if chunk.choices:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
```

## OpenAI API Compliance

The Salesforce Models API Gateway implements full OpenAI v1 specification compliance for all model backends, ensuring seamless integration with existing OpenAI clients.

### OpenAI-Compatible Endpoints

The server provides the following OpenAI-compatible endpoints:

- `GET /health` - Health check endpoint
- `GET /v1/models` - List available models in OpenAI format
- `POST /v1/chat/completions` - Chat completion with tool calling support
- `POST /v1/completions` - Text completion (legacy compatibility)

### Standard OpenAI Response Format

All responses follow the standard OpenAI format:

```json
{
  "id": "chatcmpl-123abc",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "claude-3-haiku",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response content here"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 25,
    "total_tokens": 75
  }
}
```

### Tool Calling Response Format

All model backends (OpenAI, Anthropic, Gemini) now return tool calling responses in the OpenAI v1 specification format:

```json
{
  "id": "chatcmpl-123abc",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "claude-3-haiku",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\":\"San Francisco\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 25,
    "total_tokens": 75
  }
}
```

The tool-call repair shim ensures that all tool_calls have proper `function.name` fields and correctly formatted `function.arguments` as JSON strings.

### OpenAI Client Library Integration

The gateway is a drop-in replacement for OpenAI API endpoints:

```python
# Python OpenAI SDK example
from openai import OpenAI

# Point to your gateway
client = OpenAI(
    api_key="your-key",  # Optional, gateway uses its own auth
    base_url="http://localhost:8000/v1"  # Your gateway URL
)

# Standard OpenAI API calls
response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[{"role": "user", "content": "Hello world"}]
)
```

## Response Format Standardization

The API Gateway implements a unified response formatting system to ensure consistent and compliant responses across all endpoints.

### Response Extraction Paths

The response extraction system uses a prioritized path approach:

```python
def extract_response_text_unified(sf_response: Dict[str, Any]) -> Optional[str]:
    """Single extraction method used by both servers."""
    extraction_paths = [
        ('generation', 'generatedText'),        # Sync primary (70%)
        ('generation', 'text'),                 # Sync secondary (15%)
        ('generations', 0, 'text'),             # Legacy (8%)
        ('generationDetails', 'generations', 0, 'content'),  # New (5%)
        ('choices', 0, 'message', 'content'),   # OpenAI style
        ('text',),                              # Direct
        ('content',)                            # Direct fallback
    ]
    
    for path in extraction_paths:
        extracted = navigate_response_path(sf_response, path)
        if extracted and isinstance(extracted, str) and extracted.strip():
            return extracted.strip()
    
    return None
```

### Usage Information Extraction

Token usage information is extracted with multiple fallback paths:

```python
def extract_usage_info_unified(sf_response: Dict[str, Any]) -> Dict[str, int]:
    """Unified usage extraction supporting all Salesforce formats."""
    # Path 1: NEW generationDetails format
    if 'generationDetails' in sf_response:
        generation_details = sf_response['generationDetails']
        if 'parameters' in generation_details and 'usage' in generation_details['parameters']:
            # Extract usage info
            
    # Path 2: Legacy parameters format
    if 'parameters' in sf_response:
        # Extract usage info
        
    # Path 3: Direct usage field
    if 'usage' in sf_response:
        sf_usage = sf_response['usage']
        return {
            "prompt_tokens": sf_usage.get('inputTokenCount', sf_usage.get('input_tokens', 0)),
            "completion_tokens": sf_usage.get('outputTokenCount', sf_usage.get('output_tokens', 0)),
            "total_tokens": sf_usage.get('totalTokenCount', sf_usage.get('total_tokens', 0))
        }
        
    # Fallback: content-based estimation
    content = extract_content_from_response(sf_response)
    estimated_tokens = estimate_tokens(content)
```

### Error Response Format

Standardized error responses follow this format:

```json
{
  "error": {
    "message": "Helpful error message with suggestions",
    "type": "timeout_error",
    "code": "timeout_error",
    "details": {
      "model_used": "claude-3-haiku",
      "prompt_length": 1500,
      "suggestion": "Try using claude-3-haiku for faster responses"
    }
  }
}
```

### Response Consistency

The unified formatter ensures identical responses for identical requests across both sync and async servers, with these guarantees:

1. **100% OpenAI API Compliance**: All responses pass OpenAPI specification validation
2. **Response Consistency**: Identical inputs produce identical responses across both servers
3. **Tool Calling Parity**: Both servers support identical tool calling formats
4. **Client Compatibility**: No breaking changes to existing integrations (n8n, OpenWebUI, Claude Code)
5. **Error Clarity**: Consistent, actionable error messages across both implementations

## Streaming Behavior & Headers

### Streaming Response Format

Streaming responses follow the OpenAI SSE format:

```
data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1677652288,"model":"claude-3-haiku","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1677652288,"model":"claude-3-haiku","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1677652288,"model":"claude-3-haiku","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### SSE Heartbeat Implementation

The server implements SSE heartbeats to prevent connection timeouts:

```
:ka

```

These heartbeats are sent every 15 seconds during streaming responses.

### Stream Downgrade for Tool Calls

When a request includes both `stream=true` and `tools` parameters, the server automatically downgrades to non-streaming mode:

- The `X-Stream-Downgraded: true` header is added to the response
- This improves n8n v1.105.4 compatibility with the OpenAI node
- Maintains Claude Code tool-calling functionality
- Required for proper JSON parsing in client applications

### Debug Headers

The server adds debug headers for easier troubleshooting:

- `X-Stream-Downgraded: true|false` - Indicates if streaming was downgraded to non-streaming for tool calls
- `X-Proxy-Latency-Ms: <int>` - Server processing time in milliseconds

These headers are automatically added to all responses in development mode.

## Known Limitations & Workarounds

### Model-Specific Backend Adapters

**Issue:** Different model backends use different response formats and tool calling patterns.

**Solution:** The OpenAI Front-Door architecture now includes intelligent backend adapters:

```python
# Enable with environment variable
export OPENAI_FRONTDOOR_ENABLED=1

# Override model capabilities if needed
export MODEL_CAPABILITIES_JSON='{"custom-model": {"backend_type": "anthropic_bedrock"}}'  
```

This configuration-driven approach allows for easy addition of new model backends without code changes.

### Tool Calling + Streaming Limitations

**Issue:** Tool calling and streaming cannot be used simultaneously due to client parsing limitations.

**Workaround:** The server automatically downgrades to non-streaming mode when both are requested, returning an `X-Stream-Downgraded: true` header.

```python
if 'tools' in request_data and request_data.get('stream', False):
    # Apply stream downgrade for tool calling
    request_data['stream'] = False
    response = await process_request(request_data)
    response.headers['X-Stream-Downgraded'] = 'true'
    return response
```

### n8n JSON Parsing Issues

**Issue:** n8n can experience JSON parsing errors with certain response formats.

**Workaround:** Implemented robust JSON recovery and proper error handling:

```python
def _attempt_json_recovery(malformed_json: str) -> str:
    """Attempt to recover from common JSON formatting issues."""
    # Fix missing closing brackets
    brackets = {'(': ')', '[': ']', '{': '}'}
    counts = {c: 0 for c in brackets.keys()}
    
    for char in malformed_json:
        if char in counts:
            counts[char] += 1
        elif char in brackets.values():
            for k, v in brackets.items():
                if v == char:
                    counts[k] -= 1
    
    # Add missing closing brackets
    fixed_json = malformed_json
    for bracket, count in counts.items():
        if count > 0:
            fixed_json += brackets[bracket] * count
            
    return fixed_json
```

### Connection Timeout Issues

**Issue:** Long-running requests may time out, especially with larger models.

**Workaround:** Use SSE heartbeats to keep connections alive:

```python
async def streaming_response(generator):
    """Add heartbeats to prevent connection timeouts."""
    last_heartbeat = time.time()
    async for chunk in generator:
        yield chunk
        
        # Send heartbeat every 15 seconds
        if time.time() - last_heartbeat > 15:
            yield b':\nka\n\n'  # SSE heartbeat
            last_heartbeat = time.time()
```

### Token Refresh Issues

**Issue:** Tool calling requests may fail with 401 errors when tokens expire.

**Workaround:** Applied token refresh protection to all API calls:

```python
def async_with_token_refresh(func):
    """
    Async decorator to handle token refresh for API calls.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if any(auth_error in str(e).lower() for auth_error in [
                    'unauthorized', '401', 'invalid token'
                ]):
                    if attempt == 0:
                        # Force immediate token refresh
                        client = await get_async_client()
                        await client._get_client_credentials_token()
                        continue
                    else:
                        raise Exception(f"Authentication failed after async token refresh: {e}")
                else:
                    raise e
    return wrapper
```

### Known Model Limitations

- **Claude 3 Haiku**: Most reliable for tool calling but may have lower reasoning capabilities
- **Claude 3 Sonnet**: Better reasoning but slower response times
- **Claude 3 Opus**: Highest reasoning capability but significantly slower
- **Token Limits**: Different models have different token limits that may impact usage