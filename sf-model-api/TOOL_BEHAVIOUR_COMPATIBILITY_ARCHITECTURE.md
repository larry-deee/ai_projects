# Tool Behaviour Compatibility Layer Architecture

## Executive Summary

The Tool Behaviour Compatibility Layer is a sophisticated enhancement to the sf-model-api that transforms tool calling behavior from "ignoring tools for n8n" to "preserving tools with smart routing and response normalization." This architecture enables n8n clients to fully utilize tool calling capabilities while maintaining backward compatibility and adding intelligent model routing for optimal performance.

## Architecture Overview

The Tool Behaviour Compatibility Layer introduces three core components that work together to provide seamless tool calling compatibility across different client types and backend models:

1. **Tool Preservation Logic** - Preserves tools for n8n clients while disabling streaming
2. **Smart Model Router** - Detects OpenAI-native models for direct passthrough optimization
3. **Response Normalization** - Ensures consistent OpenAI tool_calls schema across backends

### System Architecture Diagram

```
┌─────────────────┐    ┌──────────────────────────┐    ┌─────────────────────┐
│   Client        │    │  Tool Behaviour          │    │  Backend Models     │
│   (n8n/OpenAI)  │    │  Compatibility Layer     │    │  (SF/OpenAI/Claude) │
│                 │    │                          │    │                     │
│  ┌─────────────┐│    │ ┌──────────────────────┐ │    │ ┌─────────────────┐ │
│  │ Tool Request││───▶│ │ n8n Detection       │ │    │ │ Salesforce      │ │
│  └─────────────┘│    │ │ & Tool Preservation │ │    │ │ Models API      │ │
│                 │    │ └──────────────────────┘ │    │ └─────────────────┘ │
│  ┌─────────────┐│    │ ┌──────────────────────┐ │    │ ┌─────────────────┐ │
│  │ Response    ││◀───│ │ Model Router &       │ │    │ │ OpenAI-native   │ │
│  │ (OpenAI     ││    │ │ Response Normalizer  │ │    │ │ GPT Models      │ │
│  │  format)    ││    │ └──────────────────────┘ │    │ └─────────────────┘ │
│  └─────────────┘│    │                          │    │                     │
└─────────────────┘    └──────────────────────────┘    └─────────────────────┘
```

## Service Definitions

### Tool Preservation Service

**Responsibilities:**
- Detect n8n and openai/js clients via User-Agent analysis
- Preserve incoming tool definitions instead of ignoring them
- Disable streaming for n8n compatibility (prevents connection issues)
- Provide environment-based control via `N8N_COMPAT_PRESERVE_TOOLS`

**Key Functions:**
- `n8n_detected = (('n8n' in user_agent) or user_agent.startswith('openai/js')) and n8n_compat_env`
- Tool preservation with `PRESERVE_TOOLS = os.getenv("N8N_COMPAT_PRESERVE_TOOLS", "1") == "1"`
- Streaming downgrade with logging: "🔧 N8N compat: streaming disabled (non-streaming)."

### Model Router Service

**Responsibilities:**
- Detect OpenAI-native models for direct tool_calls passthrough
- Provide model capability information for routing decisions
- Cache model capabilities for performance optimization
- Control behavior via `OPENAI_NATIVE_TOOL_PASSTHROUGH` environment variable

**Key Functions:**
- `is_openai_native(model)` - Detects models supporting native tool_calls
- `get_model_capabilities(model)` - Returns comprehensive model information
- `should_use_direct_passthrough(model, tools)` - Routing decision logic

**Supported OpenAI-Native Patterns:**
- `sfdc_ai__DefaultGPT4Omni` - GPT-4 Omni via Salesforce
- `gpt-*` - Direct GPT models (gpt-4, gpt-3.5-turbo, etc.)
- `o-*` - OpenAI o-series models (o1, o3, etc.)
- `openai/gpt-oss` - Open source GPT models

### Response Normalization Service

**Responsibilities:**
- Normalize tool calling responses to consistent OpenAI tool_calls format
- Apply backend-specific response transformations
- Ensure cross-backend compatibility for tool call results
- Provide direct passthrough for OpenAI-native models

**Key Functions:**
- `normalize_tool_response(response, model, tools)` - Main normalization entry point
- `_normalize_anthropic_response()` - Claude-specific transformations
- `_normalize_google_response()` - Gemini-specific transformations
- `_normalize_salesforce_response()` - Salesforce-hosted model transformations

## API Contracts

### Tool Preservation Endpoint Enhancement

**Enhanced `/v1/chat/completions` behavior:**

**Request (n8n client with tools):**
```json
{
  "model": "claude-3-haiku",
  "messages": [{"role": "user", "content": "What's the weather?"}],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {
          "type": "object",
          "properties": {"location": {"type": "string"}},
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto",
  "stream": true
}
```

**Response Headers (n8n client):**
```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
x-stream-downgraded: true
x-proxy-latency-ms: 150
```

**Response Body (preserved tools with normalized format):**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "claude-3-haiku",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "I'll help you get weather information.",
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\": \"San Francisco\"}"
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

### Model Router API

**Routing Information Endpoint:**
```python
# Internal API - used by compatibility layer
routing_info = model_router.get_routing_info("gpt-4", tools)

# Response format:
{
  "model": "gpt-4",
  "capabilities": {
    "supports_native_tools": True,
    "backend_type": "openai_native",
    "requires_normalization": False,
    "supports_streaming": True
  },
  "routing_decision": {
    "use_direct_passthrough": True,
    "requires_normalization": False,
    "environment_settings": {
      "openai_passthrough_enabled": True,
      "preserve_tools_enabled": True
    }
  },
  "performance_optimizations": {
    "cached_capabilities": True,
    "direct_passthrough_available": True
  }
}
```

## Data Schema

### Model Capabilities Schema

```python
@dataclass
class ModelCapabilities:
    """Model capability definition for routing decisions."""
    supports_native_tools: bool = False      # Direct tool_calls support
    backend_type: str = "salesforce"         # Backend classification
    requires_normalization: bool = True      # Response normalization needed
    max_tokens_default: int = 1000          # Default token limit
    supports_streaming: bool = True          # Streaming capability
```

### Environment Configuration Schema

```bash
# Core Compatibility Settings
N8N_COMPAT_MODE=1                          # Enable n8n detection (default: 1)
N8N_COMPAT_PRESERVE_TOOLS=1                # Preserve tools for n8n (default: 1)
OPENAI_NATIVE_TOOL_PASSTHROUGH=1           # Enable native passthrough (default: 1)

# Logging and Debug
VERBOSE_TOOL_LOGS=0                        # Detailed tool logs (default: 0)  
MODEL_ROUTER_LOG_LEVEL=WARNING             # Model router logging level
SF_RESPONSE_DEBUG=false                    # Response debug logging
```

## Technology Stack Rationale

### Model Router (`src/model_router.py`)

**Choice:** Pure Python with `@lru_cache` decorators and dataclasses
**Justification:** 
- High performance with O(1) model detection after first lookup
- Thread-safe caching with minimal memory footprint
- Simple integration with existing Flask/Quart architecture
- No additional dependencies required

**Trade-offs:**
- **vs. External Cache (Redis):** Model router cache is in-memory only, but model capabilities rarely change and cache warming is fast
- **vs. Database Storage:** Capabilities are static configuration, not dynamic data requiring persistence
- **vs. Configuration Files:** Python-based detection allows for complex pattern matching and runtime flexibility

### Response Normalization Architecture

**Choice:** Pluggable backend-specific normalizers with common interface
**Justification:**
- Each backend (Anthropic, Google, Salesforce) has unique response formats
- Extensible architecture supports adding new backends without core changes
- Direct passthrough optimization eliminates normalization overhead for native models
- Maintains backward compatibility with existing response processing

**Trade-offs:**
- **vs. Universal Parser:** Backend-specific normalizers handle edge cases better than generic parsing
- **vs. Schema Validation:** Response transformation focuses on format conversion rather than validation
- **vs. Client-Side Processing:** Server-side normalization ensures consistent API contract

### Environment-Based Control

**Choice:** Environment variables with sensible defaults
**Justification:**
- Zero-config operation with `N8N_COMPAT_PRESERVE_TOOLS=1` by default
- Production deployment flexibility without code changes
- Backward compatibility via `N8N_COMPAT_PRESERVE_TOOLS=0` legacy mode
- Clear feature toggles for debugging and rollback scenarios

## Key Considerations

### Scalability

**How will the system handle 10x the initial load?**

1. **Model Router Caching:** `@lru_cache(maxsize=128)` provides O(1) model detection after cache warming
2. **Response Normalization:** Direct passthrough for OpenAI-native models eliminates processing overhead
3. **Tool Preservation:** Minimal overhead (single User-Agent string check and environment variable lookup)
4. **Connection Pooling:** Existing 20-30% performance improvement from connection pooling is preserved
5. **Async Architecture:** Full async/await support maintains 40-60% performance improvement

**Scaling Strategy:**
- Increase `maxsize` for model capabilities cache if using >128 unique models
- Monitor cache hit rates via `routing_info["performance_optimizations"]["cached_capabilities"]`
- Scale horizontally with existing gunicorn async workers

### Security

**Primary threat vectors and mitigation strategies:**

1. **User-Agent Spoofing:** 
   - **Threat:** Malicious clients spoofing n8n User-Agent to bypass tool restrictions
   - **Mitigation:** Tool preservation is a *feature*, not a restriction - no security risk from spoofing

2. **Tool Injection:**
   - **Threat:** Clients injecting malicious tool definitions
   - **Mitigation:** Existing tool validation in `tool_schemas.py` unchanged - all tools validated before execution

3. **Model Name Manipulation:**
   - **Threat:** Clients requesting non-existent or restricted models
   - **Mitigation:** Model mapping in `map_model_name()` unchanged - invalid models rejected by Salesforce API

4. **Environment Variable Exposure:**
   - **Threat:** Configuration leakage in logs or error messages
   - **Mitigation:** No sensitive data in new environment variables - boolean flags only

### Observability

**How will we monitor the system's health and debug issues?**

1. **Routing Decision Logging:**
   ```
   🔧 Tool routing: model=gpt-4, native=true, backend=openai_native
   🔧 N8N compat: tools PRESERVED (tool_choice unchanged).
   🔧 Applied response normalization for claude-3-haiku
   ```

2. **Performance Metrics:**
   - Cache hit rates: `routing_info["performance_optimizations"]["cached_capabilities"]`
   - Passthrough usage: Count of `use_direct_passthrough=true` decisions
   - Normalization overhead: Response processing time by backend type

3. **Health Check Integration:**
   ```python
   # Model router health included in existing /health endpoint
   router_status = {
       "model_router": {
           "cache_size": len(router.model_capabilities_cache),
           "openai_passthrough_enabled": router.openai_passthrough_enabled
       }
   }
   ```

4. **Error Tracking:**
   - Model detection failures logged with full model name and pattern matching results
   - Response normalization errors captured with original response structure
   - Environment variable conflicts logged at startup

### Deployment & CI/CD

**How this architecture integrates with deployment:**

1. **Zero-Downtime Deployment:** New environment variables have safe defaults - no configuration required
2. **Feature Flags:** All new functionality controlled by environment variables for gradual rollout
3. **Rollback Strategy:** Set `N8N_COMPAT_PRESERVE_TOOLS=0` to return to legacy behavior instantly
4. **Health Monitoring:** Enhanced health check endpoint includes model router status
5. **Performance Monitoring:** Existing `/v1/performance/metrics` endpoint enhanced with routing statistics

**Production Checklist:**
- ✅ `N8N_COMPAT_PRESERVE_TOOLS=1` (default - tool preservation enabled)
- ✅ `OPENAI_NATIVE_TOOL_PASSTHROUGH=1` (default - performance optimization enabled)
- ✅ `MODEL_ROUTER_LOG_LEVEL=WARNING` (production logging level)
- ✅ Monitor cache hit rates and normalization overhead
- ✅ Test both n8n and regular clients in staging environment

## Implementation Files

### Core Implementation
- `/src/async_endpoint_server.py` - Updated n8n compatibility logic with tool preservation
- `/src/model_router.py` - **NEW** - Smart model routing and response normalization
- `/start_async_service.sh` - Updated with new environment variables

### Testing & Validation
- `/test_tool_behaviour_compatibility.py` - **NEW** - Comprehensive test suite
- `/N8N_COMPATIBILITY.md` - Updated documentation (legacy reference)
- `/TOOL_BEHAVIOUR_COMPATIBILITY_ARCHITECTURE.md` - **NEW** - This architecture document

### Configuration Integration
- Environment variables integrated into startup scripts
- Health check endpoints enhanced with router status
- Performance metrics include routing decision tracking

This architecture provides a robust, scalable, and maintainable solution for tool calling compatibility that preserves n8n functionality while adding intelligent optimizations for OpenAI-native models. The design ensures backward compatibility while providing a clear path for future enhancements and additional backend integrations.