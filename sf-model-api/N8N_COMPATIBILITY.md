# n8n Compatibility Mode Implementation

## Overview

This implementation adds n8n-compatible mode with strict tool gating and safe fallbacks to the sf-model-api project. The changes ensure reliable behavior when the API is called from n8n workflows.

## Features Implemented

### 1. n8n Detection and Compatibility Mode

- **Enhanced User-Agent Detection**: Automatically detects n8n clients by checking for 'n8n' in the User-Agent header or 'openai/js' at the start of the User-Agent
- **Environment Variable Control**: `N8N_COMPAT_MODE` environment variable (default: enabled)
- **Forced Non-Tool Behavior**: When n8n is detected, incoming tools are ignored and tool_choice is set to "none"
- **Streaming Downgrade**: Automatically downgrades streaming to non-streaming for n8n compatibility
- **Token Pre-warming**: Server startup includes OAuth token pre-warming to eliminate first-request 401 errors

### 2. Strict Tool Entry Conditions

- **Tool Validation**: `_has_valid_tools()` helper function ensures tools are valid before entering tool path
- **Tool Choice Validation**: Respects tool_choice="none"/"disabled" settings
- **Dual Implementation**: Available in both `async_endpoint_server.py` and `tool_handler.py`

### 3. Safe Response Formatting

- **Null Content Protection**: Ensures response content is never null, always returns empty string as fallback
- **Empty Tool Calls Handling**: Omits tool_calls arrays when empty instead of returning empty arrays
- **Consistent Error Handling**: All response paths include null content protection
- **JSON Parsing Robustness**: Enhanced handling for code fences (```json) in model responses

### 4. Enhanced Logging

- **n8n Detection Logging**: Logs when n8n compatibility mode is triggered
- **VERBOSE_TOOL_LOGS**: Environment variable to control tool-related log verbosity
- **Debug Information**: Detailed logging for troubleshooting tool calling issues

## Code Changes

### async_endpoint_server.py

1. **Added `_has_valid_tools()` helper function** (lines 591-611)
2. **n8n detection logic** in `/v1/chat/completions` endpoint (lines 651-661)
3. **Strict tool entry conditions** (lines 666-674)
4. **Safe response formatting** with null content protection (lines 689-736)

### tool_handler.py

1. **Added `has_valid_tools()` utility function** (lines 41-62)
2. **VERBOSE_TOOL_LOGS implementation** (lines 933-938)
3. **Safe tool response formatting** (lines 1025-1050)
4. **Enhanced error response handling** (lines 1152-1160)

## Environment Variables

- `N8N_COMPAT_MODE`: Enable/disable n8n compatibility mode (default: "1" - enabled)
- `VERBOSE_TOOL_LOGS`: Enable verbose tool calling logs (default: "0" - disabled)

## Testing

Comprehensive tests are provided:

- **test_n8n_compatibility.py**: Unit tests for tool validation functions
- **test_n8n_integration.py**: Integration tests for full n8n compatibility workflow

Run tests with:
```bash
python test_n8n_compatibility.py
python test_n8n_integration.py
```

## Usage Examples

### n8n or openai/js Client Request (Auto-Detected)
```javascript
// n8n workflow - tools are automatically ignored
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "User-Agent: n8n/1.0" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "tools": [{"type": "function", "function": {"name": "ignored"}}]
  }'
```

### Environment-Based Control
```bash
# Force n8n mode for all clients
export N8N_COMPAT_MODE=1

# Disable n8n mode entirely  
export N8N_COMPAT_MODE=0

# Enable verbose tool logging
export VERBOSE_TOOL_LOGS=1
```

### Regular Client (Tool Calling Enabled)
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "User-Agent: MyApp/1.0" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "tools": [{"type": "function", "function": {"name": "get_weather"}}]
  }'
```

## Backwards Compatibility

- All existing functionality remains unchanged
- n8n mode is enabled by default but only activates when n8n User-Agent is detected
- Regular clients continue to use full tool calling functionality
- No breaking changes to API contracts or response formats

## Performance Impact

- Minimal performance overhead (single User-Agent string check)
- Tool validation adds microseconds to request processing
- Logging can be controlled via environment variables
- No impact on non-n8n clients

## Monitoring and Debugging

The implementation includes comprehensive logging:

```
🔧 N8N compatibility mode: ignoring tools and forcing non-tool behavior (UA: n8n/1.0, ENV: True)
🔧 N8N compatibility mode: downgrading streaming to non-streaming  
🔧 FIXED: Async tool processing for 0 tools with model claude-3-haiku
🔐 OAuth token pre-warmed successfully
```

Enable detailed tool logs:
```bash
export VERBOSE_TOOL_LOGS=1
```

## Enhanced Reliability Features

### Token Pre-warming

The server now pre-warms OAuth tokens during startup to eliminate first-request 401 errors:

- Automatically obtains an authentication token during server initialization
- Handles connection errors gracefully during startup
- Logs token status: `🔐 OAuth token pre-warmed successfully` or warning if failed
- Falls back to on-demand token refresh if pre-warming fails

### Extended Client Compatibility

- **openai/js Detection**: User agents starting with 'openai/js' are now treated as n8n-compatible clients
- **Improved JSON Handling**: Better handling of model responses that may contain code fences (```json)