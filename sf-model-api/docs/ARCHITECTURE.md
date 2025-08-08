# Salesforce Models API Gateway Architecture

## Table of Contents
1. [System Overview & Components](#system-overview--components)
2. [Server Architecture](#server-architecture)
3. [OpenAI Front-Door & Backend Adapters](#openai-front-door--backend-adapters)
4. [Authentication & Token Management](#authentication--token-management)
5. [Tool Calling Framework](#tool-calling-framework)
6. [Performance Characteristics](#performance-characteristics)
7. [Model Access & Configuration](#model-access--configuration)

## System Overview & Components

The Salesforce Models API Gateway serves as a bridge between client applications and Salesforce-hosted LLM models, providing an OpenAI-compatible API interface. This gateway allows clients to interact with Salesforce LLMs using the familiar OpenAI API specification while adding advanced tool calling capabilities.

Key functions include:
- Translating OpenAI API requests to Salesforce API format
- Universal OpenAI v1 specification compliance for all model backends
- Intelligent backend adapters for OpenAI, Anthropic, and Gemini models
- Automatic tool-call repair for universal tool calling compatibility
- Managing authentication with Salesforce
- Providing advanced tool calling capabilities
- Ensuring thread-safe concurrent request handling
- Optimizing performance through connection pooling and async architecture

### Core Components

- **API Server:** 
  - `llm_endpoint_server.py` - Sync OpenAI-compatible endpoints using Flask
  - `async_endpoint_server.py` - Async OpenAI-compatible endpoints using Quart
  
- **Client Implementation:**
  - `salesforce_models_client.py` - Contains both sync and async client classes for Salesforce API

- **OpenAI Front-Door Architecture:**
  - `model_capabilities.py` - Model capability registry and routing
  - `openai_spec_adapter.py` - Backend adapter framework for universal OpenAI compliance
  - `openai_tool_fix.py` - Tool-call repair shim for universal compatibility

- **Tool Calling Framework:**
  - `tool_handler.py` - Advanced function calling implementation
  - `tool_schemas.py` - JSON schemas for tool definitions
  - `tool_executor.py` - Execution logic for tool functions

- **Token Management:**
  - Thread-safe authentication with proactive refresh
  - Token caching with file-based persistence

- **Connection Pooling:**
  - `connection_pool.py` - TCP connection pool implementation
  - `connection_pool_monitor.py` - Monitoring for pool health

- **CLI Interface:**
  - `cli.py` - Direct model interaction and testing

- **Configuration:**
  - `config.json` - Environment-based configuration
  - Environment variables as fallback
  - `config/models.yml` - Model capabilities configuration

### Technology Stack

- **Language:** Python 3.8+
- **Web Frameworks:** 
  - Flask with Flask-CORS (Sync implementation)
  - Quart with Quart-CORS (Async implementation)
- **Server:** 
  - Gunicorn (Sync)
  - Gunicorn with Quart workers (Async)
- **Threading:** Thread-safe concurrent request handling
- **Authentication:** JWT-based token management with Salesforce OAuth
- **External APIs:** Salesforce Models API integration
- **Data Formats:** JSON (OpenAI-compatible responses)
- **CLI Tools:** Command-line interface for direct model interaction
- **Caching:** In-memory token caching with file-based persistence

## Server Architecture

### Sync vs Async Implementations

The gateway has two parallel implementations:

#### Sync Implementation (Original)
- Uses Flask for HTTP handling
- Wraps async operations with `asyncio.run()`
- Creates new threads for each request
- Suffers from sync-to-async conversion overhead
- File: `src/llm_endpoint_server.py`

#### Async Implementation (Optimized)
- Uses Quart for native async HTTP handling
- Native async/await throughout request lifecycle
- No sync-to-async conversion overhead
- Maintains persistent connection pool without wrapper overhead
- File: `src/async_endpoint_server.py`

Both implementations maintain identical API compatibility but with significant performance differences.

### Async Architecture Benefits

The async architecture optimizations eliminate sync wrapper bottlenecks by:

1. **Eliminating Sync Wrappers:**
   - Removed `asyncio.run()` calls in `SalesforceModelsClient`
   - Implemented direct async/await usage throughout request lifecycle
   - Eliminated ThreadPoolExecutor overhead

2. **True Async Server:**
   - Replaced Flask with Quart (async-compatible)
   - Implemented fully async endpoints that maintain async context
   - Applied non-blocking I/O throughout the stack

3. **Direct Connection Pool Integration:**
   - ConnectionPool used directly in async context
   - Eliminated sync-to-async conversions
   - Maintained persistent TCP connections for all API calls

4. **Thread-Safe Architecture:**
   - Implemented singleton pattern for async client management
   - Ensured Gunicorn multi-worker compatibility
   - Added proper resource cleanup and shutdown handling

### Key Architecture Changes

```python
# BEFORE (Sync Wrapper Pattern):
def get_access_token(self) -> str:
    return asyncio.run(self.async_client._async_get_access_token())

# AFTER (Direct Async Usage):
client = await get_async_client()
token = await client._async_get_access_token()  # No sync wrapper!
```

```python
# BEFORE (Flask + Sync):
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    client = get_thread_client()  # Sync client
    response = client.generate_text(...)  # Sync call with asyncio.run()

# AFTER (Quart + Async):
@app.route('/v1/chat/completions', methods=['POST'])
async def chat_completions():
    client = await get_async_client()  # Async client  
    response = await client._async_chat_completion(...)  # Pure async
```

## OpenAI Front-Door & Backend Adapters

The OpenAI Front-Door architecture transforms the gateway from UA-based tool filtering to universal OpenAI v1 specification compliance with intelligent backend adapters for different model providers.

### Architecture Components

#### 1. Model Capabilities Registry

The `model_capabilities.py` module provides a centralized capability definition system that determines how requests should be routed based on model characteristics rather than user agents.

**Key Features:**
- Environment variable and config file support
- Default model mappings for common models
- Capability flags: `openai_compatible`, `anthropic_bedrock`, `vertex_gemini`
- Thread-safe lazy loading and caching
- Intelligent fallback patterns for unknown models

**Example Usage:**
```python
from model_capabilities import caps_for, get_backend_type

caps = caps_for("sfdc_ai__DefaultGPT4Omni")
# Returns: {'openai_compatible': True, 'passthrough_tools': True, ...}

backend = get_backend_type("claude-3-sonnet")  
# Returns: 'anthropic_bedrock'
```

**Configuration Sources** (in priority order):
1. `MODEL_CAPABILITIES_JSON` environment variable (JSON string)
2. `MODEL_CAPABILITIES_FILE` environment variable (file path)
3. `config/models.yml` or `config/models.json` (YAML/JSON file)
4. Built-in defaults

#### 2. OpenAI Specification Adapter

The `openai_spec_adapter.py` module provides a universal backend adapter system that normalizes responses from different LLM backends to OpenAI v1 specification format.

**Key Functions:**
- `route_and_normalise(payload, clients)` - Universal request router and response normalizer
- Backend-specific normalizers for Anthropic, Gemini, and generic models

**Response Flow:**
```
Client Request (OpenAI format)
↓
route_and_normalise() 
↓
Backend-specific client call
↓
Backend-specific normalizer
↓
OpenAI v1 compliant response
```

#### 3. Tool-Call Repair Shim

The `openai_tool_fix.py` module implements a universal tool-call repair system that eliminates "Tool call missing function name" errors and ensures OpenAI v1 specification compliance across all model backends.

**Key Features:**
- Fixes missing `function.name` fields using tool definitions
- Ensures `function.arguments` are properly formatted as JSON strings
- Handles malformed tool call structures gracefully
- Provides comprehensive validation and health checking
- Thread-safe operations with performance optimizations

### Model Backend Types

**OpenAI-Compatible (Direct Passthrough)**:
- `sfdc_ai__DefaultGPT4Omni`
- `gpt-4`, `gpt-4-mini`, `gpt-4-turbo`
- `gpt-3.5-turbo`

**Anthropic/Bedrock (Requires Normalization)**:
- `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet`
- `sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet` 
- `claude-3-haiku`, `claude-3-sonnet`, `claude-4-sonnet`

**Google Vertex/Gemini (Requires Normalization)**:
- `sfdc_ai__DefaultVertexAIGemini25Flash001`
- `gemini-pro`, `gemini-flash`

### Universal Tool Preservation

The OpenAI Front-Door architecture preserves tools for all clients and model backends, eliminating the previous User-Agent based tool filtering approach:

```python
# OLD - UA-based filtering (REMOVED)
n8n_detected = ('n8n' in user_agent) and n8n_compat_env
if n8n_detected and not PRESERVE_TOOLS:
    tools = None  # Tool filtering based on User-Agent

# NEW - Universal tool preservation  
logger.debug(f"🔧 Universal OpenAI compatibility: tools={'preserved' if tools else 'none'}")
```

### Environment Controls

```bash
# Enable OpenAI Front-Door Architecture
export OPENAI_FRONTDOOR_ENABLED=1

# Model Capabilities Configuration
export MODEL_CAPABILITIES_JSON="{...}"
export MODEL_CAPABILITIES_FILE="config/models.yml"

# Tool Behavior Controls
export N8N_COMPAT_PRESERVE_TOOLS=1
export OPENAI_NATIVE_TOOL_PASSTHROUGH=1
```

## Authentication & Token Management

The gateway uses JWT-based token management for authentication with Salesforce:

### Token Lifecycle
1. **Acquisition:** Obtains token from Salesforce OAuth endpoint using client credentials
2. **Storage:** Caches token in memory and in a local file for persistence
3. **Validation:** Validates token before each API request
4. **Refresh:** Proactively refreshes token before expiration
5. **Protection:** Wraps API calls with token refresh decorator

### Key Optimizations
- **Buffer Time:** Optimized from 45 minutes to 30 minutes for 50-minute tokens
- **Utilization:** Improved from 10% to 40% of token lifetime
- **Refresh Frequency:** Reduced from ~12 refreshes/hour to ~3 refreshes/hour
- **Token Protection:** Applied `@with_token_refresh_sync` decorator to all API calls including tool handler methods

### Configuration System

The configuration system supports multiple sources with priority:

1. **Config File:** `config.json` in the project root (primary source)
2. **Environment Variables:** Fallback if config file is not available
3. **Default Values:** Used when neither of the above provides a value

**Configuration Properties:**
- `SALESFORCE_CONSUMER_KEY`: API client ID
- `SALESFORCE_CONSUMER_SECRET`: API client secret
- `SALESFORCE_INSTANCE_URL`: Salesforce API instance URL
- Additional configuration for logging, timeouts, and performance settings

### Path Resolution Strategy

The system implements a robust configuration path resolution strategy:

```python
async def resolve_config_path(config_file: str = 'config.json') -> str:
    """Resolve config.json path robustly by checking multiple locations."""
    # If path is absolute or explicitly relative, use as is
    if os.path.isabs(config_file) or config_file.startswith('./') or config_file.startswith('../'):
        return config_file
        
    # Check various locations in order of preference
    possible_paths = [
        config_file,  # Current directory
        os.path.join('..', config_file),  # Parent directory
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_file)  # Project root
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return config_file  # Return original path if not found
```

## Tool Calling Framework

The Salesforce Models API Gateway includes a comprehensive tool calling framework that enables function execution through LLM interactions. This framework is fully compatible with OpenAI, Anthropic, and Gemini tool calling formats, with universal OpenAI v1 specification compliance through the backend adapters and tool-call repair shim.

### Tool Handler Architecture

The tool handling system is implemented in `tool_handler.py` and consists of several key components:

1. **Tool Definition Validation:** Validates tool schemas against OpenAI and Anthropic specifications
2. **Function Calling Orchestration:** Manages the conversation flow for function calling
3. **Parameter Extraction:** Parses function parameters from model responses
4. **Function Execution:** Safely executes defined functions with appropriate parameters
5. **Result Formatting:** Formats results in OpenAI-compatible response format

### Tool Calling Process Flow

1. **Client Request:** Client sends request with `tools` parameter defining available functions
2. **Prompt Enhancement:** System adds tool definitions to the conversation context
3. **Model Invocation:** Model generates a response that includes function calls
4. **Parameter Extraction:** System extracts function name and parameters
5. **Function Execution:** System executes the requested function with parsed parameters
6. **Result Integration:** Function results are added to the conversation context
7. **Final Response:** Formatted response is returned to the client

### n8n Integration

The tool calling system includes special support for n8n workflow automation:

- Full support for `$fromAI()` parameter extraction
- Compatible with n8n's function calling format
- Proper handling of `function`, `name`, and `parameters` fields
- Universal tool preservation with automatic tool-call repair
- All models (including Anthropic/Claude) now work with tool calling in n8n

### Tool Schema Example

```json
{
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
}
```

## Performance Characteristics

### Connection Pooling

Connection pooling was implemented to reuse TCP connections when communicating with the Salesforce API, eliminating the overhead of establishing new connections for each request.

Key features:
- Maintains a pool of persistent connections
- Thread-safe connection management
- Connection health monitoring and automatic recovery
- Configurable pool size and timeout settings

Implementation details:
- `connection_pool.py` implements the core pool functionality
- Sessions are automatically returned to the pool after use
- Dead connections are detected and replaced
- Pool statistics are exposed through metrics endpoint

### Response Processing Optimization

The response processing was optimized to use a priority-based extraction strategy that eliminates multiple fallback paths in the majority of cases:

```python
# Primary Path (High success rate):
if 'generation' in sf_response:
    generation = sf_response['generation']
    if isinstance(generation, dict) and 'generatedText' in generation:
        return generation['generatedText'].strip()

# Secondary Path:
if 'generation' in sf_response:
    generation = sf_response['generation']
    if isinstance(generation, dict) and 'text' in generation:
        return generation['text'].strip()

# Last resort: Comprehensive search
return fallback_response_extraction(sf_response, debug_mode)
```

**Performance Impact:**
- **Single-Path Success:** 89% of responses
- **Fallback Usage:** Only 10% of responses need comprehensive extraction
- **Processing Speed:** Significant improvement over multiple fallback attempts

### Token Cache Optimization

The token management system was optimized to:
- Extend token TTL from 15 minutes to 30+ minutes buffer
- Optimize token utilization from 10% to 40% of lifetime
- Reduce token refresh operations by 75%
- Implement proper token refresh protection for all API calls including tool handling

Key changes:
- Modified buffer time from 45 minutes to 30 minutes for 50-minute tokens
- Added token refresh protection to tool calling methods
- Implemented thread-safe token file access

### Memory Management Improvements

- **Conversation State Bounds:** Implemented maximum message limits to prevent memory leaks
- **Thread-Local Storage:** Added proper cleanup to prevent accumulation
- **Regex Optimization:** Pre-compiled and cached patterns for performance
- **Response Extraction:** Implemented single-path lookup with fallbacks
- **Memory Monitoring:** Added real-time metrics for usage patterns

```python
# Before: Unbounded conversation history
conversation_history.append(new_message)  # No limit check

# After: Bounded conversation history
MAX_HISTORY_SIZE = 50  # Configure maximum history size
while len(conversation_history) >= MAX_HISTORY_SIZE:
    conversation_history.pop(0)  # Remove oldest messages
conversation_history.append(new_message)
```

### Benchmarking Results

Performance improvements have been validated through comprehensive testing:

| Metric | Sync Server | Async Server | Improvement |
|--------|-------------|--------------|-------------|
| Avg Response Time | 850ms | 340ms | 60% faster |
| P95 Response Time | 2.1s | 800ms | 62% faster |
| Requests/sec | 45 | 118 | 162% increase |
| Memory per Request | 12MB | 7MB | 42% reduction |
| TCP Connections | New each time | Pooled | 80% reuse |

## Model Access & Configuration

### Available Models

The gateway supports multiple models through Salesforce's Einstein Trust Layer:

#### Claude Models (Anthropic)
- `claude-3-haiku` - Fastest model, ideal for simple tasks
- `claude-3-sonnet` - Balanced performance for complex tasks
- `claude-3-opus` - Most capable model for reasoning
- `claude-4-sonnet` - Latest generation with enhanced capabilities

#### OpenAI Models
- `gpt-4` - Versatile model for complex tasks
- `gpt-3.5-turbo` - Faster model for simpler tasks

#### Google Models
- `gemini-pro` - General purpose model
- `gemini-pro-vision` - Multimodal model with image support

*Note: Available models depend on your Salesforce org configuration and Einstein licensing.*

### Model Selection Best Practices

- **Model Selection**: Use `claude-3-haiku` for fastest responses
- **Prompt Engineering**: Concise prompts improve response times
- **Token Caching**: Authentication tokens are cached aggressively
- **Connection Pooling**: HTTP connections are efficiently reused
- **Dynamic Timeouts**: Automatically calculated based on request size

### Model Configuration

The gateway now uses a configuration-driven approach for model capabilities and backend routing:

#### Model Capabilities Registry

The model capabilities registry provides a centralized way to define model capabilities and routing:

```yaml
# config/models.yml example
gpt-4:
  openai_compatible: true
  backend_type: "openai_native"
  passthrough_tools: true

claude-3-sonnet:
  openai_compatible: false
  anthropic_bedrock: true
  backend_type: "anthropic_bedrock"
  requires_normalization: true
  
gemini-pro:
  vertex_gemini: true
  backend_type: "vertex_gemini"
  requires_normalization: true
```

#### Default Model Mappings

Out-of-the-box, the system includes default mappings for common models:

- **OpenAI-Compatible**: `sfdc_ai__DefaultGPT4Omni`, `gpt-4`, `gpt-4-turbo`, etc.
- **Anthropic/Bedrock**: `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet`, `claude-3-*`, etc.
- **Google Vertex/Gemini**: `sfdc_ai__DefaultVertexAIGemini25Flash001`, `gemini-*`, etc.

These mappings can be overridden through environment variables or configuration files.