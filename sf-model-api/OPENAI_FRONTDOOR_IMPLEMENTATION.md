# OpenAI Front-Door & Backend Adapters Implementation

## Overview

This document describes the implementation of the **OpenAI Front-Door & Backend Adapters** architecture for the sf-model-api project. This new architecture transforms the system from UA-based tool filtering to universal OpenAI v1 specification compliance.

## Architecture Components

### 1. Model Capabilities Registry (`src/model_capabilities.py`)

**Purpose**: Centralized capability definition system that determines how requests should be routed based on model characteristics rather than user agents.

**Key Features**:
- Environment variable and config file support
- Default model mappings for common models  
- Capability flags: `openai_compatible`, `anthropic_bedrock`, `vertex_gemini`
- Thread-safe lazy loading and caching
- Intelligent fallback patterns for unknown models

**Configuration Sources** (in priority order):
1. `MODEL_CAPABILITIES_JSON` environment variable (JSON string)
2. `MODEL_CAPABILITIES_FILE` environment variable (file path)
3. `config/models.yml` or `config/models.json` (YAML/JSON file)
4. Built-in defaults

**Example Usage**:
```python
from model_capabilities import caps_for, get_backend_type

caps = caps_for("sfdc_ai__DefaultGPT4Omni")
# Returns: {'openai_compatible': True, 'passthrough_tools': True, ...}

backend = get_backend_type("claude-3-sonnet")  
# Returns: 'anthropic_bedrock'
```

### 2. OpenAI Specification Adapter (`src/openai_spec_adapter.py`)

**Purpose**: Universal backend adapter system that normalizes responses from different LLM backends to OpenAI v1 specification format.

**Key Functions**:

#### `route_and_normalise(payload, clients)`
- Universal request router and response normalizer
- Routes requests to appropriate backends based on model capabilities
- Normalizes all responses to OpenAI v1 specification format

#### Backend-Specific Normalizers:
- `normalise_anthropic()` - Handles Anthropic/Bedrock responses with tool use events
- `normalise_gemini()` - Converts Gemini functionCall format to OpenAI tool_calls
- `normalise_generic()` - Fallback normalizer for unknown backends

**Response Flow**:
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

### 3. Integration Layer (`src/async_endpoint_server.py`)

**Changes Made**:

#### Removed UA-Based Tool Filtering:
```python
# OLD - UA-based filtering (REMOVED)
n8n_detected = ('n8n' in user_agent) and n8n_compat_env
if n8n_detected and not PRESERVE_TOOLS:
    tools = None  # Tool filtering based on User-Agent

# NEW - Universal tool preservation  
logger.debug(f"🔧 Universal OpenAI compatibility: tools={'preserved' if tools else 'none'}")
```

#### Added New Architecture Integration:
```python
# Enable with OPENAI_FRONTDOOR_ENABLED=1
use_new_architecture = os.getenv("OPENAI_FRONTDOOR_ENABLED", "0") == "1"

if use_new_architecture:
    multi_client = MultiClientAdapter(client)
    openai_response = await route_and_normalise(payload, multi_client)
    return normalized_response
```

#### Client Adapter Classes:
- `ClientAdapter`: Wraps existing AsyncSalesforceModelsClient
- `MultiClientAdapter`: Provides backend-specific clients for route_and_normalise

## Model Capabilities Configuration

### Default Model Mappings:

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

### Custom Configuration Example:

**JSON (Environment Variable)**:
```bash
export MODEL_CAPABILITIES_JSON='{
  "custom-model-name": {
    "openai_compatible": false,
    "anthropic_bedrock": true,
    "requires_normalization": true,
    "backend_type": "anthropic_bedrock"
  }
}'
```

**YAML File (config/models.yml)**:
```yaml
custom-model-name:
  openai_compatible: false
  anthropic_bedrock: true
  requires_normalization: true
  backend_type: anthropic_bedrock
```

## Deployment & Testing

### Enable New Architecture:
```bash
export OPENAI_FRONTDOOR_ENABLED=1
python src/async_endpoint_server.py
```

### Run Tests:
```bash
python test_openai_frontdoor.py
```

### Backward Compatibility:
- Legacy architecture remains active by default (`OPENAI_FRONTDOOR_ENABLED=0`)
- New architecture falls back to legacy on errors
- All existing functionality preserved

## Key Benefits

### 1. Universal OpenAI Compatibility
- **Before**: UA-based tool filtering (`N8N compat: ignoring tools`)
- **After**: Universal tool preservation with capability-based routing

### 2. Simplified Architecture
- **Before**: Complex UA detection and tool filtering logic
- **After**: Clean capability-based routing with normalization

### 3. Future-Proof Design
- **Backend Agnostic**: Easy to add new LLM backends
- **Configuration Driven**: No code changes needed for new models
- **Standardized Interface**: OpenAI v1 specification compliance

### 4. Performance Optimizations
- **Direct Passthrough**: OpenAI-native models bypass normalization
- **Caching**: Model capabilities cached for performance
- **Async Throughout**: Maintains async optimization benefits

## Migration Path

### Phase 1: Testing (Current)
- New architecture available via `OPENAI_FRONTDOOR_ENABLED=1`
- Comprehensive test suite validates functionality
- Legacy architecture remains default

### Phase 2: Gradual Rollout
- Enable new architecture for specific models or clients
- Monitor performance and compatibility
- Gather feedback from users

### Phase 3: Full Migration
- Make new architecture default (`OPENAI_FRONTDOOR_ENABLED=1` default)
- Deprecate legacy UA-based filtering
- Remove legacy code paths

## Files Modified

### Created:
- `/src/model_capabilities.py` - Model capability registry
- `/src/openai_spec_adapter.py` - Backend adapter framework
- `/test_openai_frontdoor.py` - Comprehensive test suite
- `/OPENAI_FRONTDOOR_IMPLEMENTATION.md` - This documentation

### Modified:
- `/src/async_endpoint_server.py` - Integrated new architecture, removed UA-based filtering

## Environment Variables

### New Architecture Control:
- `OPENAI_FRONTDOOR_ENABLED=1` - Enable new architecture (default: 0)

### Model Configuration:
- `MODEL_CAPABILITIES_JSON="{...}"` - Override model capabilities (JSON string)
- `MODEL_CAPABILITIES_FILE="path/to/config"` - Custom config file path

### Removed:
- `N8N_COMPAT_PRESERVE_TOOLS` - No longer needed (tools always preserved)
- UA-based tool filtering logic - Replaced with capability-based routing

## Conclusion

The OpenAI Front-Door & Backend Adapters architecture successfully transforms the sf-model-api from a UA-based tool filtering system to a universal OpenAI v1 specification compliant gateway. This provides:

- **Universal Compatibility**: All clients receive properly formatted OpenAI responses
- **Tool Preservation**: Tools are always preserved and properly formatted
- **Performance**: Direct passthrough for OpenAI-native models
- **Extensibility**: Easy to add new backends and models
- **Maintainability**: Clean, configuration-driven architecture

The implementation is production-ready with comprehensive testing, backward compatibility, and a clear migration path.