# Anthropic Native Pass-Through Hardening Architecture

## Overview

This document describes the **Anthropic Native Pass-Through Hardening** architecture implemented for the sf-model-api project. This architecture provides a secure, high-performance native pass-through to the Anthropic API while maintaining complete isolation from the OpenAI front-door functionality.

## Architecture Principles

### 1. Native Pass-Through Philosophy
- **Zero Schema Transformation**: Preserves native Anthropic request/response formats
- **Direct Proxy Pattern**: Minimal transformation between client and upstream API
- **Tool Format Preservation**: Tool calls remain in native Anthropic format without normalization

### 2. Security-First Design
- **Hardened HTTP Client**: httpx with strict security configuration
- **No Redirect Following**: Prevents potential redirect attacks
- **Connection Limits**: Resource exhaustion protection
- **Header Filtering**: Secure header management with allow-list approach

### 3. Performance Optimization
- **Connection Pooling**: Persistent connections to upstream API
- **SSE Streaming**: Verbatim relay without buffering
- **Graceful Lifecycle**: Proper resource cleanup and shutdown

### 4. Isolation Architecture
- **Path Isolation**: All Anthropic functionality under `/anthropic` path
- **Zero Interference**: No modifications to existing OpenAI front-door paths
- **Independent Error Handling**: Separate error processing pipeline

## Component Architecture

```
Client Request (Native Anthropic)
↓
Flask Application (/anthropic/* paths)
↓
AnthropicNativeRouter
├── Request Validation
├── Header Processing
└── Adapter Integration
    ↓
    AnthropicNativeAdapter
    ├── httpx Client (Hardened)
    ├── Connection Pool
    ├── Header Filtering
    └── SSE Streaming
        ↓
        Anthropic API
        ↓
        Native Response (Verbatim)
        ↓
        Client
```

## Implementation Components

### 1. AnthropicNativeAdapter (`src/adapters/anthropic_native.py`)

**Purpose**: Hardened HTTP adapter for direct Anthropic API communication.

**Key Features**:
- **Hardened httpx Client Configuration**:
  ```python
  limits = httpx.Limits(
      max_keepalive_connections=10,
      max_connections=20,
      keepalive_expiry=30.0
  )
  
  timeout_config = httpx.Timeout(
      connect=10.0,
      read=timeout,
      write=10.0,
      pool=5.0
  )
  
  client = httpx.AsyncClient(
      follow_redirects=False,  # Security
      verify=True,            # SSL verification
      limits=limits,
      timeout=timeout_config
  )
  ```

- **Header Management**:
  - Preserves `anthropic-beta` headers for feature flags
  - Filters hop-by-hop headers for security
  - Maintains `anthropic-request-id` for correlation
  - Enforces required authentication headers

- **SSE Streaming**:
  - Verbatim relay of server-sent events
  - No buffering or event transformation
  - Proper error handling within stream

- **Lifecycle Management**:
  - Async context manager support
  - Graceful shutdown with resource cleanup
  - Singleton pattern for application-wide use

### 2. AnthropicNativeRouter (`src/routers/anthropic_native.py`)

**Purpose**: Flask router providing native Anthropic API endpoints.

**Endpoints**:
- `POST /anthropic/v1/messages` - Native Anthropic messages API
- `GET /anthropic/health` - Health check endpoint

**Key Features**:
- **Native Request Processing**:
  - Direct pass-through of Anthropic request format
  - Content-Type validation
  - JSON request body validation

- **SSE Streaming Support**:
  ```python
  response = Response(
      generate_stream(),
      mimetype='text/event-stream',
      headers={
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no'
      }
  )
  ```

- **Error Handling**:
  - Native Anthropic error format
  - Status code preservation
  - Proper error event streaming

### 3. Application Integration

**Flask Application Integration**:
```python
# Register Anthropic native router
try:
    anthropic_bp = create_anthropic_router()
    app.register_blueprint(anthropic_bp)
    logger.info("✅ Anthropic native router registered at /anthropic")
except ImportError as e:
    logger.warning(f"⚠️ Anthropic native router disabled: {e}")
```

**Lifecycle Management**:
```python
finally:
    # Cleanup Anthropic adapter resources
    try:
        from adapters.anthropic_native import shutdown_anthropic_adapter
        asyncio.run(shutdown_anthropic_adapter())
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")
```

## Configuration

### Environment Variables
```bash
# Required for native pass-through
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional configuration
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_VERSION=2023-06-01
```

### JSON Configuration (`config.json`)
```json
{
  "anthropic_native": {
    "base_url": "https://api.anthropic.com",
    "version": "2023-06-01",
    "timeout": 60.0,
    "api_key": "YOUR_ANTHROPIC_API_KEY"
  }
}
```

## Acceptance Criteria Validation

### 1. Native Anthropic JSON Format ✅
- **Requirement**: `/anthropic/v1/messages` returns native Anthropic JSON format
- **Implementation**: Zero schema transformation, direct response relay
- **Validation**: Response structure matches Anthropic API specification

### 2. SSE Streaming with Proper Headers ✅
- **Requirement**: SSE streaming with proper headers and no buffering
- **Implementation**: 
  - `Content-Type: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
- **Validation**: Headers match SSE requirements, events stream in real-time

### 3. Tool Round-Trip Unchanged ✅
- **Requirement**: Tool calls preserved in native format
- **Implementation**: No OpenAI normalization, direct pass-through
- **Validation**: Tool schemas and responses maintain Anthropic format

### 4. Error Pass-Through ✅
- **Requirement**: Original HTTP status codes preserved
- **Implementation**: Status code relay, native error format
- **Validation**: Error responses match upstream status codes

### 5. Anthropic-Request-Id Preservation ✅
- **Requirement**: Correlation IDs maintained
- **Implementation**: Header filtering preserves correlation headers
- **Validation**: Request IDs passed through when provided

### 6. Beta Header Forwarding ✅
- **Requirement**: Support for `anthropic-beta` feature flags
- **Implementation**: Beta header detection and forwarding
- **Validation**: Feature flag headers reach upstream API

## Security Features

### HTTP Client Hardening
- **No Redirect Following**: Prevents redirect-based attacks
- **SSL Verification**: Enforced certificate validation
- **Connection Limits**: Resource exhaustion protection
- **Timeout Controls**: Prevents hanging connections

### Header Security
- **Allow-List Filtering**: Only permitted headers forwarded
- **Hop-by-Hop Removal**: Network-level headers filtered
- **Authentication Enforcement**: Required headers validated

### Error Handling
- **Information Disclosure Prevention**: No internal error details exposed
- **Rate Limit Preservation**: Upstream rate limits respected
- **Status Code Accuracy**: Original error codes maintained

## Performance Characteristics

### Connection Management
- **Connection Pooling**: Up to 20 concurrent connections
- **Keep-Alive**: 30-second connection reuse
- **Timeout Optimization**: Adaptive timeouts based on operation type

### Streaming Performance
- **Zero Buffering**: Events relayed immediately
- **Memory Efficiency**: No event accumulation
- **Low Latency**: Minimal processing overhead

### Resource Usage
- **Bounded Memory**: Connection limits prevent memory growth
- **Graceful Degradation**: Proper error handling under load
- **Clean Shutdown**: Resource cleanup on termination

## Testing and Validation

### Test Suite (`test_anthropic_native_hardening.py`)
- **Unit Tests**: Component-level validation
- **Integration Tests**: End-to-end API validation
- **Acceptance Tests**: Criteria-specific validation
- **Performance Tests**: Load and streaming validation

### Demo Script (`anthropic_native_demo.py`)
- **Format Comparison**: Native vs OpenAI format demonstration
- **Streaming Demo**: SSE functionality showcase
- **Tool Calling**: Native tool format demonstration
- **Error Handling**: Status code preservation demo
- **Header Handling**: Correlation and beta feature demo

## Integration Guide

### For n8n Integration
```javascript
// Use native Anthropic endpoint
const anthropicUrl = 'http://localhost:8000/anthropic/v1/messages';

// Native Anthropic request format
const request = {
  model: 'claude-3-haiku-20240307',
  max_tokens: 1000,
  messages: [
    {
      role: 'user',
      content: 'Your message here'
    }
  ]
};
```

### For Direct API Clients
```python
import httpx

# Native Anthropic client usage
async with httpx.AsyncClient() as client:
    response = await client.post(
        'http://localhost:8000/anthropic/v1/messages',
        json={
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": "Hello!"}
            ]
        },
        headers={
            'Content-Type': 'application/json',
            'anthropic-beta': 'tools-2024-04-04'  # Optional
        }
    )
```

### For Streaming Applications
```python
# SSE streaming example
async with client.stream(
    'POST',
    'http://localhost:8000/anthropic/v1/messages',
    json={"model": "claude-3-haiku-20240307", "stream": True, ...}
) as response:
    async for chunk in response.aiter_text():
        # Process SSE events
        if chunk.startswith('data: '):
            data = json.loads(chunk[6:])
            # Handle native Anthropic event
```

## Deployment Considerations

### Dependencies
- **httpx >= 0.24.0**: Required for hardened HTTP client
- **Flask ecosystem**: Existing Flask application dependencies
- **Environment variables**: Anthropic API key configuration

### Resource Requirements
- **Memory**: ~10MB additional for connection pooling
- **CPU**: Minimal overhead for pass-through processing
- **Network**: Direct connection to Anthropic API required

### Monitoring
- **Health Endpoint**: `/anthropic/health` for service monitoring
- **Error Logging**: Structured logging for debugging
- **Performance Metrics**: Connection pool and request metrics

## Migration Path

### From OpenAI Front-Door
1. **Parallel Deployment**: Both endpoints available simultaneously
2. **Gradual Migration**: Move clients to `/anthropic` endpoints
3. **Format Validation**: Ensure native Anthropic format compatibility
4. **Performance Testing**: Validate streaming and tool calling

### Integration Testing
1. **Unit Tests**: Run `python test_anthropic_native_hardening.py`
2. **Demo Validation**: Execute `python anthropic_native_demo.py`
3. **Load Testing**: Validate under production load
4. **Security Audit**: Review security configuration

This architecture provides a robust, secure, and performant foundation for native Anthropic API integration while maintaining complete isolation from existing OpenAI compatibility layers.