# Claude Code Integration Guide

## Problem Summary

The original API routing issues were caused by Claude Code attempting to use **Anthropic-style endpoints** (`/v1/messages`) while the gateway only provided **OpenAI-style endpoints** (`/v1/chat/completions`).

### Original Error Analysis

1. `POST /v1/v1/messages - 404` → Double path issue (likely configuration error)
2. `POST /v1/messages - 404` → Missing Anthropic endpoint 
3. `GET /v1/chat/completions - 405` → Endpoint only accepted POST
4. `GET /v1/messages - 404` → Missing endpoint

## Solutions Implemented

### ✅ 1. Added Anthropic Messages Endpoint

**New endpoint:** `POST /v1/messages`

- Accepts Anthropic-style message format
- Converts internally to Salesforce format  
- Returns Anthropic-compatible responses
- Supports streaming with Anthropic SSE format

**Key features:**
- Handles `content` as both string and array (content blocks)
- Processes `system` parameter correctly
- Maps models between Anthropic and Salesforce names
- Provides proper error handling

### ✅ 2. Enhanced Chat Completions Endpoint

**Updated endpoint:** `GET|POST /v1/chat/completions`

- Added GET method support for endpoint documentation
- Returns API documentation when accessed via GET
- Maintains full POST functionality for actual completions

### ✅ 3. Updated Service Documentation

- Root endpoint (`/`) now shows both OpenAI and Anthropic compatibility
- Lists all available endpoints including `/v1/messages`
- Startup messages include Claude Code configuration examples

### ✅ 4. Added Endpoint Testing

**New test script:** `test_endpoints.py`

- Tests all endpoint combinations that caused original errors
- Validates expected status codes vs. actual
- Provides clear pass/fail reporting

## Claude Code Configuration

### Method 1: Direct Configuration (Recommended)

```bash
# Set Claude Code to use your gateway
export ANTHROPIC_API_URL=http://localhost:8000
export ANTHROPIC_API_KEY=dummy  # Not used but may be required

# Then use Claude Code normally
claude-code "Hello, how are you?"
```

### Method 2: Configuration File

If Claude Code supports configuration files, add:

```json
{
    "api_url": "http://localhost:8000",
    "endpoints": {
        "messages": "/v1/messages"
    }
}
```

### Method 3: Runtime Override

Some Claude Code implementations allow runtime URL override:

```bash
claude-code --api-url http://localhost:8000 "Your message here"
```

## Testing and Validation

### 1. Test Basic Connectivity

```bash
# Test if gateway is running
curl http://localhost:8000/health

# Test Anthropic endpoint
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 2. Run Automated Tests

```bash
# Run the endpoint test suite
python test_endpoints.py
```

### 3. Test Claude Code Integration

```bash
# Test actual Claude Code connection
claude-code "Test message to verify integration"
```

## Troubleshooting Common Issues

### Issue: Still getting 404 errors

**Solution:** Ensure the gateway is running on port 8000:

```bash
cd /Users/Dev/models-api-v2
python src/llm_endpoint_server.py
```

### Issue: GET requests return 405

**Expected behavior:** 
- `GET /v1/chat/completions` → Returns documentation (200)
- `GET /v1/messages` → Method not allowed (405)
- Only POST is supported for actual completions

### Issue: Wrong response format

**Check:** Ensure Claude Code is hitting `/v1/messages` not `/v1/chat/completions`
- `/v1/messages` returns Anthropic format
- `/v1/chat/completions` returns OpenAI format

### Issue: Authentication errors

**Solution:** The gateway handles Salesforce authentication internally. Claude Code doesn't need valid Anthropic API keys.

## Supported Endpoints Summary

| Endpoint | Methods | Purpose | Client Compatibility |
|----------|---------|---------|---------------------|
| `/v1/messages` | POST | Anthropic messages | Claude Code, Anthropic SDK |
| `/v1/chat/completions` | GET, POST | OpenAI chat completions | OpenAI SDK, OpenWebUI |
| `/v1/completions` | POST | Legacy text completions | Legacy OpenAI clients |
| `/v1/models` | GET | List available models | All clients |
| `/health` | GET | Health check | Monitoring |
| `/` | GET | Service documentation | Browsers |

## Model Mapping

The gateway automatically maps between different model naming conventions:

| Claude Code Request | Salesforce Model |
|-------------------|------------------|
| `claude-3-haiku` | `sfdc_ai__DefaultBedrockAnthropicClaude3Haiku` |
| `claude-3-sonnet` | `sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet` |
| `claude-4-sonnet` | `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet` |

## Advanced Features

### Streaming Support

The `/v1/messages` endpoint supports Anthropic-style streaming:

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}], "stream": true}'
```

### Error Handling

The gateway provides detailed error responses with:
- HTTP status codes matching the error type
- Helpful error messages with suggestions
- Model and prompt information for debugging

### Performance Optimization

The gateway includes several performance optimizations:
- Token caching to reduce authentication overhead
- Response text extraction optimization
- Thread-safe request handling
- Proactive token refresh

## Implementation Details

### Request Flow for `/v1/messages`

1. Claude Code sends Anthropic-format request
2. Gateway converts to OpenAI message format
3. Gateway processes messages for Salesforce compatibility
4. Gateway calls Salesforce Models API
5. Gateway converts response to Anthropic format
6. Response sent back to Claude Code

### Backward Compatibility

All existing OpenAI-compatible integrations continue to work:
- OpenWebUI → `/v1/chat/completions`
- n8n → `/v1/chat/completions`
- LangChain → `/v1/chat/completions`

## Next Steps

1. **Test Integration**: Run `python test_endpoints.py` to verify all endpoints
2. **Configure Claude Code**: Set your API URL to `http://localhost:8000`
3. **Monitor Performance**: Watch logs for any authentication or performance issues
4. **Scale if Needed**: Consider using production gunicorn setup for heavy usage

The gateway now provides full dual compatibility with both OpenAI and Anthropic API formats while maintaining all existing functionality.