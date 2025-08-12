# Testing & Validation Guide

## Table of Contents
1. [Local Development Testing](#local-development-testing)
2. [Curl Smoke Tests](#curl-smoke-tests)
3. [Regression Test Suite Usage](#regression-test-suite-usage)
4. [Performance Testing](#performance-testing)
5. [Compatibility Testing](#compatibility-testing)
6. [Manual Verification Steps](#manual-verification-steps)

## Local Development Testing

### Server Startup

Before running any tests, make sure the server is running:

```bash
# ASGI Server (Recommended for Local Development)
./start_async_service.sh

# Or using uvicorn directly
uvicorn src.async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11

# Flask Server (Legacy)
python llm_endpoint_server.py
```

### Python Unit Tests

**Note:** The `/tests/` directory is available for local development but excluded from the git repository.

### For Developers (Local Testing):
```bash
# Run comprehensive test suite (requires local tests/ directory)
python -m pytest tests/ -v
```

### For Users (Quick Verification):
```bash
# Basic functionality test with curl
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}]}'

# Performance tests
python test_caching_performance.py
python test_phase1_optimizations.py

# SSE Format Compliance Test
python test_sse_format.py
```

### Environment Validation

Verify the environment and configuration:

```bash
# Validate configuration
python -c "
from src.salesforce_models_client import SalesforceModelsClient
client = SalesforceModelsClient()
print('✅ Configuration valid' if client._validate_config() else '❌ Configuration invalid')
"

# Check token status
python -c "
import json, time, os
if os.path.exists('salesforce_models_token.json'):
    data = json.load(open('salesforce_models_token.json'))
    expires_at = data.get('expires_at', 0)
    current_time = time.time()
    mins_left = (expires_at - current_time) / 60
    print(f'Token expires in {mins_left:.1f} minutes')
"
```

## Curl Smoke Tests

Use these curl commands to quickly verify key functionality:

### Basic Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok","version":"1.0.0","environment":"development"}
```

### List Models

```bash
curl http://localhost:8000/v1/models
```

Expected response format:
```json
{
  "object": "list",
  "data": [
    {
      "id": "claude-3-haiku",
      "object": "model",
      "created": 1677610602,
      "owned_by": "anthropic"
    },
    ...
  ]
}
```

### Basic Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Expected headers:
- `Content-Type: application/json`
- `X-Proxy-Latency-Ms: <number>`

### Streaming Test

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Write a short story"}],
    "stream": true
  }'
```

Expected format:
```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk"...

:ka

data: {"id":"chatcmpl-123","object":"chat.completion.chunk"...
```

### Tool Calling Test

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculator",
        "description": "Basic calculator",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      }
    }]
  }'
```

### Stream Downgrade Test

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "stream": true,
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculator",
        "description": "Basic calculator",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      }
    }]
  }' -D -
```

Expected headers:
- `X-Stream-Downgraded: true`
- `X-Proxy-Latency-Ms: <number>`

## Regression Test Suite Usage

The QA team has created regression tests for streaming behavior in `streaming_regression_tests.sh`. This script runs a series of tests to validate the streaming functionality.

### Running Regression Tests

```bash
./streaming_regression_tests.sh
```

This script will run the following tests:

1. **Tool Calling Stream Downgrade**: Validates that tool calls with streaming enabled correctly trigger stream downgrade
2. **OpenAI Streaming Format**: Checks that streaming responses follow the correct SSE format
3. **Anthropic Streaming Format**: Verifies Anthropic-compatible streaming
4. **Non-Streaming Standard Request**: Validates basic non-streaming responses
5. **Server Health Check**: Confirms server is operational

### Test Success Criteria

- **Tool Calling Test**: Must include `X-Stream-Downgraded: true` header
- **OpenAI Streaming**: Response chunks must start with "data:" prefix
- **Anthropic Streaming**: Response must include "event:" prefixes
- **Non-Streaming**: Must include `X-Proxy-Latency-Ms` header
- **Health Check**: Must return HTTP 200

### Automated Test Output

The test script will generate a report in `test_results_<timestamp>.log` with detailed test results and any failures.

## Performance Testing

### Token Cache Performance

```bash
# Run token cache performance test
python src/token_performance_analysis.py

# Check token cache hit rate
python -c "
from src.salesforce_models_client import SalesforceModelsClient
client = SalesforceModelsClient()
print(f'Token Cache Hit Rate: {client.token_cache_hit_rate:.2f}')
"
```

### Connection Pool Testing

```bash
# Test connection pool performance
python src/connection_pool_test.py --concurrent-requests=10

# Check connection pool status
curl http://localhost:8000/v1/performance/metrics | grep connection_pool
```

Expected results:
- **Avg Response Time**: Should be under 400ms for async server
- **P95 Response Time**: Should be under 1000ms for async server
- **Connection Reuse Rate**: Should be above 80%

### Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 -T application/json -p test_payload.json \
  http://localhost:8000/v1/chat/completions
```

Recommended test criteria:
- **Concurrency**: Test with 10-20 concurrent requests
- **Total Requests**: At least 100 requests per test run
- **Success Rate**: Should be >99%

## Compatibility Testing

### OpenAI SDK Test

```bash
python -c "
import openai
client = openai.OpenAI(base_url='http://localhost:8000/v1', api_key='any-key')
response = client.chat.completions.create(
    model='claude-3-haiku',
    messages=[{'role': 'user', 'content': 'Hello'}]
)
print(response.choices[0].message.content)
"
```

### LangChain Integration

```bash
python -c "
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model='claude-3-sonnet',
    openai_api_base='http://localhost:8000/v1',
    openai_api_key='any-key'
)
print(llm.invoke('What is LangChain?'))
"
```

### Streaming with Heartbeats Test

```python
# Test script for SSE heartbeats
import time
from openai import OpenAI

client = OpenAI(
    api_key="any-key",
    base_url="http://localhost:8000/v1"
)

start_time = time.time()
last_chunk_time = start_time
heartbeats_received = 0

print("Starting streaming test (will run for 60 seconds)...")
response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[{"role": "user", "content": "Write a very long story about space exploration"}],
    stream=True
)

try:
    for chunk in response:
        current_time = time.time()
        time_since_last = current_time - last_chunk_time
        
        # Log heartbeats and content
        if hasattr(chunk, '_raw_response'):
            raw_data = chunk._raw_response.text
            if ':ka' in raw_data:
                heartbeats_received += 1
                print(f"\n[{current_time - start_time:.1f}s] ❤️ Heartbeat received! ({heartbeats_received} total)")
            
        # Log content
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            last_chunk_time = current_time
            
        # Exit after 60 seconds
        if current_time - start_time > 60:
            print("\n\nTest complete after 60 seconds")
            print(f"Heartbeats received: {heartbeats_received}")
            break
            
except Exception as e:
    print(f"Error during streaming: {e}")

print(f"\nTotal test duration: {time.time() - start_time:.1f} seconds")
print(f"Heartbeat frequency: {heartbeats_received / ((time.time() - start_time) / 60):.1f} per minute")
```

## Manual Verification Steps

### 1. Server Startup Verification

- [ ] Server starts successfully with `./start_async_service.sh`
- [ ] No errors in startup logs
- [ ] `/health` endpoint returns `{"status":"ok"}`

### 2. Basic Functionality Verification

- [ ] `GET /v1/models` returns available models
- [ ] Basic chat completion works with claude-3-haiku model
- [ ] Response includes correct headers (Content-Type, X-Proxy-Latency-Ms)

### 3. Streaming Verification

- [ ] Streaming works with `stream=true` parameter
- [ ] SSE format is correct (begins with "data: ")
- [ ] Heartbeats are sent approximately every 15 seconds
- [ ] Stream properly terminates with `data: [DONE]`

### 4. Tool Calling Verification

- [ ] Tool calls work with basic calculator function
- [ ] Function arguments are correctly formatted
- [ ] Response follows OpenAI tool calls format
- [ ] Using both `stream=true` and `tools` results in stream downgrade

### 5. Debug Header Verification

- [ ] All responses include `X-Proxy-Latency-Ms` header
- [ ] Stream downgrade requests include `X-Stream-Downgraded: true` header

### 6. Error Handling Verification

- [ ] Invalid model returns appropriate error message
- [ ] Malformed requests return helpful error messages
- [ ] Timeout behavior is appropriate for long requests

### 7. Cross-Server Compatibility

- [ ] Responses from sync and async servers are equivalent
- [ ] Tool calling works on both server types
- [ ] Streaming works on both server types
- [ ] Error formats are consistent between servers