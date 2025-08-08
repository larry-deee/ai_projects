# OpenAI Front-Door & Backend Adapters Architecture

## Summary
This PR transforms sf-model-api from UA-based tool filtering to universal OpenAI v1 specification compliance with intelligent backend adapters. It provides seamless tool calling support across all model providers (OpenAI, Anthropic, Gemini) while maintaining optimal performance through direct passthrough for OpenAI-native models.

## Key Changes
- 🎯 **Universal OpenAI Compatibility**: All responses now conform to OpenAI v1 specification
- 🔧 **Backend Adapters**: Intelligent normalization for Anthropic/Gemini → OpenAI format
- 🛠 **Tool-Call Repair**: Eliminates "Tool call missing function name" errors
- ⚡ **Performance Optimized**: Direct passthrough for OpenAI-native models
- 🔄 **Configuration-Driven**: Model capabilities via environment variables or files
- 🧰 **n8n Integration**: Full tool calling support for all models in n8n workflows

## Technical Implementation

### 1. Model Capabilities Registry (`src/model_capabilities.py`)
- Centralized capability definition system for model routing
- Environment variable and file-based configuration
- Thread-safe lazy loading and caching
- Default mappings for common models with intelligent fallback

### 2. OpenAI Specification Adapter (`src/openai_spec_adapter.py`)
- Universal backend adapter system for response normalization
- Model-specific adapters for Anthropic, Gemini, and OpenAI
- Preserves tools for all clients regardless of User-Agent

### 3. Tool-Call Repair (`src/openai_tool_fix.py`)
- Fixes missing `function.name` fields using tool definitions
- Ensures `function.arguments` are properly formatted
- Handles malformed tool call structures gracefully
- Thread-safe operations with performance optimizations

## Testing
- ✅ **Backend Adapters**: All adapters validated (OpenAI, Anthropic, Gemini)
- ✅ **Tool-Call Repair**: Prevents all function name errors
- ✅ **Universal OpenAI Compliance**: All responses conform to OpenAI v1 spec
- ✅ **n8n Compatibility**: Works with n8n workflows and OpenAI node
- ✅ **Performance**: Minimal overhead for OpenAI-native models

## Migration
The new architecture is disabled by default and can be enabled with:
```bash
export OPENAI_FRONTDOOR_ENABLED=1
```

No changes are needed to existing API calls or client applications. All functionality is preserved with enhanced compatibility.

## Rollback
If needed, the system can be rolled back to the previous architecture:
```bash
export OPENAI_FRONTDOOR_ENABLED=0
# or
git checkout pre-openai-frontdoor-<timestamp>
```

## Documentation
- Updated README.md with new architecture description
- Updated ARCHITECTURE.md with detailed implementation guide
- Updated COMPATIBILITY.md with integration information
- Added CHANGELOG.md entry
- Created detailed implementation documentation

## Files Modified
- **Created**:
  - `src/model_capabilities.py` - Model capability registry
  - `src/openai_spec_adapter.py` - Backend adapter framework
  - `src/openai_tool_fix.py` - Tool-call repair shim
  - `test_openai_frontdoor.py` - Comprehensive test suite
  - `test_tool_repair_shim.py` - Tool-call repair tests
  - `test_integration_tool_repair.py` - Integration tests
  - `CHANGELOG.md` - Comprehensive changelog

- **Modified**:
  - `src/async_endpoint_server.py` - Integration with new architecture
  - `README.md` - Updated features and documentation
  - `docs/ARCHITECTURE.md` - Added OpenAI Front-Door documentation
  - `docs/COMPATIBILITY.md` - Updated integration guide