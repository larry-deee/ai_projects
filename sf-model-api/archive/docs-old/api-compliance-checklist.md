# API Compliance Checklist

## OpenAI API Compliance Requirements

### Chat Completions Response Format

#### Required Fields ✅/❌

**Root Level Fields:**
- [ ] `id` (string): Unique identifier (format: "chatcmpl-{timestamp}")
- [ ] `object` (string): Must be "chat.completion" 
- [ ] `created` (integer): Unix timestamp of creation
- [ ] `model` (string): Model identifier used for completion
- [ ] `choices` (array): Array of completion choices (minimum 1)
- [ ] `usage` (object): Token usage statistics

**Optional Root Fields:**
- [ ] `system_fingerprint` (string): System configuration fingerprint

#### Choices Array Requirements

**Each Choice Object:**
- [ ] `index` (integer): Choice index (starts at 0)
- [ ] `message` (object): The generated message
- [ ] `finish_reason` (string): Completion termination reason
- [ ] `logprobs` (object|null): Log probabilities (if requested)

#### Message Object Requirements

**Standard Message:**
- [ ] `role` (string): Must be "assistant"
- [ ] `content` (string|null): The message content

**Tool Calling Message:**
- [ ] `role` (string): Must be "assistant" 
- [ ] `content` (string|null): Text content (can be null if only tool calls)
- [ ] `tool_calls` (array): Array of tool call objects

#### Tool Call Object Requirements

**Each Tool Call:**
- [ ] `id` (string): Unique call identifier
- [ ] `type` (string): Must be "function"  
- [ ] `function` (object): Function call details
  - [ ] `name` (string): Function name
  - [ ] `arguments` (string): JSON string of arguments

#### Finish Reason Values

**Valid Values:**
- [ ] `"stop"`: Natural stopping point or stop sequence
- [ ] `"length"`: Reached max_tokens limit
- [ ] `"tool_calls"`: Model called tool(s)
- [ ] `"content_filter"`: Content filtered by safety systems
- [ ] `null`: Response incomplete/in progress

#### Usage Object Requirements

**Token Counts:**
- [ ] `prompt_tokens` (integer): Input tokens consumed
- [ ] `completion_tokens` (integer): Output tokens generated  
- [ ] `total_tokens` (integer): Total tokens (prompt + completion)

**Optional Usage Fields:**
- [ ] `completion_tokens_details` (object): Breakdown of completion tokens
- [ ] `prompt_tokens_details` (object): Breakdown of prompt tokens

### Streaming Response Format

#### Server-Sent Events Compliance

**Event Format:**
- [ ] Each chunk prefixed with "data: "
- [ ] Each chunk terminated with "\n\n"
- [ ] Final event must be "data: [DONE]\n\n"

#### Streaming Chunk Structure

**Chunk Object:**
- [ ] `id` (string): Same ID for entire stream
- [ ] `object` (string): Must be "chat.completion.chunk"
- [ ] `created` (integer): Same timestamp for entire stream
- [ ] `model` (string): Model identifier
- [ ] `choices` (array): Array of choice deltas

#### Choice Delta Requirements

**Delta Object:**
- [ ] `index` (integer): Choice index
- [ ] `delta` (object): Incremental content
- [ ] `finish_reason` (string|null): Set only in final chunk

**Delta Content Types:**
- [ ] `role` (string): Assistant role (first chunk only)
- [ ] `content` (string): Incremental text content
- [ ] `tool_calls` (array): Incremental tool call data

### Error Response Format

#### Error Object Structure

**Root Error Response:**
- [ ] `error` (object): Error details container

**Error Details:**
- [ ] `message` (string): Human-readable error description
- [ ] `type` (string): Error category classification
- [ ] `code` (string|null): Specific error code
- [ ] `param` (string|null): Parameter that caused error

#### Standard Error Types

**Authentication Errors:**
- [ ] Type: "invalid_request_error"
- [ ] Code: "invalid_api_key"
- [ ] HTTP Status: 401

**Rate Limit Errors:**
- [ ] Type: "requests_exceeded_error" 
- [ ] Code: "rate_limit_exceeded"
- [ ] HTTP Status: 429

**Server Errors:**
- [ ] Type: "server_error"
- [ ] Code: "internal_error"  
- [ ] HTTP Status: 500

## Anthropic API Compliance Requirements

### Messages Response Format

#### Required Root Fields

**Message Response:**
- [ ] `id` (string): Unique message identifier (format: "msg_{timestamp}")
- [ ] `type` (string): Must be "message"
- [ ] `role` (string): Must be "assistant"
- [ ] `content` (array): Array of content blocks
- [ ] `model` (string): Model identifier
- [ ] `stop_reason` (string): Completion termination reason
- [ ] `stop_sequence` (string|null): Stop sequence that terminated generation
- [ ] `usage` (object): Token usage information

#### Content Block Requirements

**Text Content Block:**
- [ ] `type` (string): Must be "text"
- [ ] `text` (string): The text content

**Tool Use Content Block:**
- [ ] `type` (string): Must be "tool_use"
- [ ] `id` (string): Unique tool call identifier
- [ ] `name` (string): Tool function name
- [ ] `input` (object): Tool call parameters

#### Stop Reason Values

**Valid Values:**
- [ ] `"end_turn"`: Natural conversation end
- [ ] `"max_tokens"`: Reached maximum token limit
- [ ] `"stop_sequence"`: Hit specified stop sequence
- [ ] `"tool_use"`: Model made tool call(s)

#### Usage Object Requirements

**Token Counts:**
- [ ] `input_tokens` (integer): Input tokens processed
- [ ] `output_tokens` (integer): Output tokens generated

### Streaming Response Format

#### Event Types

**Message Start:**
- [ ] Event: "message_start"
- [ ] Data: Complete message object with empty content

**Content Block Start:**
- [ ] Event: "content_block_start" 
- [ ] Data: Content block with index and type

**Content Block Delta:**
- [ ] Event: "content_block_delta"
- [ ] Data: Incremental content updates

**Content Block Stop:**
- [ ] Event: "content_block_stop"
- [ ] Data: Content block completion notification

**Message Delta:**
- [ ] Event: "message_delta"
- [ ] Data: Message-level updates (usage, stop_reason)

**Message Stop:**
- [ ] Event: "message_stop"
- [ ] Data: Stream completion notification

### Error Response Format

#### Error Object Structure

**Root Error Response:**
- [ ] `type` (string): Must be "error"
- [ ] `error` (object): Error details

**Error Details:**
- [ ] `type` (string): Error type classification
- [ ] `message` (string): Human-readable description

## Implementation Validation

### Current Sync Server Status

**OpenAI Compliance:**
- ❌ Response ID format inconsistent
- ✅ Basic response structure correct
- ❌ Missing tool_calls support in message object
- ❌ Hardcoded finish_reason to "stop"
- ✅ Usage object structure correct
- ❌ Error response format non-standard

**Anthropic Compliance:**
- ✅ Has dedicated /v1/messages endpoint
- ✅ Basic message structure correct
- ❌ Content block array implementation incomplete
- ❌ Stop reason logic not implemented

### Current Async Server Status  

**OpenAI Compliance:**
- ✅ Response ID includes hash for uniqueness
- ✅ Basic response structure correct
- ✅ Tool_calls support implemented
- ✅ Dynamic finish_reason logic
- ✅ Usage object extraction comprehensive
- ❌ Error response format inconsistent

**Anthropic Compliance:**
- ❌ No /v1/messages endpoint
- ❌ No Anthropic format support

### Testing Checklist

#### Unit Tests Required

**Response Format Tests:**
- [ ] Test OpenAI response structure validation
- [ ] Test Anthropic response structure validation  
- [ ] Test tool calling response format
- [ ] Test error response format compliance
- [ ] Test streaming chunk format validation

**Content Extraction Tests:**
- [ ] Test unified response text extraction
- [ ] Test usage information extraction
- [ ] Test tool calls extraction
- [ ] Test error handling in extraction

**Cross-Server Consistency Tests:**
- [ ] Test identical responses for identical inputs
- [ ] Test error format consistency
- [ ] Test streaming format consistency

#### Integration Tests Required

**Client Compatibility Tests:**
- [ ] Test with OpenAI Python SDK
- [ ] Test with OpenAI Node.js SDK
- [ ] Test with Anthropic Python SDK
- [ ] Test with curl commands
- [ ] Test with n8n integration
- [ ] Test with OpenWebUI
- [ ] Test with Claude Code CLI

**API Specification Validation:**
- [ ] Validate against OpenAI OpenAPI 3.0 schema
- [ ] Validate against Anthropic API documentation
- [ ] Test all error scenarios and status codes
- [ ] Test streaming compliance with SSE standards

### Performance Requirements

**Response Time Targets:**
- [ ] Non-streaming responses: < 5 seconds for standard requests
- [ ] Streaming first chunk: < 500ms
- [ ] Error responses: < 100ms

**Memory Usage:**
- [ ] Response formatting overhead: < 10% of total memory
- [ ] No memory leaks in streaming responses
- [ ] Efficient handling of large responses (>100KB)

## Compliance Validation Commands

### OpenAI API Testing

```bash
# Test basic chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Hello"}]
  }' | jq .

# Test streaming response
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku", 
    "messages": [{"role": "user", "content": "Count to 10"}],
    "stream": true
  }'

# Test tool calling
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "calculate",
        "description": "Perform arithmetic calculation",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      }
    }],
    "tool_choice": "auto"
  }' | jq .
```

### Anthropic API Testing

```bash
# Test messages endpoint
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }' | jq .

# Test streaming messages
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Count to 10"}],
    "max_tokens": 100,
    "stream": true
  }'
```

### Schema Validation

```python
# OpenAI response validation
import jsonschema
import json

openai_schema = {
    "type": "object",
    "required": ["id", "object", "created", "model", "choices", "usage"],
    "properties": {
        "id": {"type": "string", "pattern": "^chatcmpl-"},
        "object": {"const": "chat.completion"},
        "created": {"type": "integer"},
        "model": {"type": "string"},
        "choices": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["index", "message", "finish_reason"],
                "properties": {
                    "index": {"type": "integer"},
                    "message": {
                        "type": "object",
                        "required": ["role", "content"],
                        "properties": {
                            "role": {"const": "assistant"},
                            "content": {"type": ["string", "null"]},
                            "tool_calls": {"type": "array"}
                        }
                    },
                    "finish_reason": {
                        "enum": ["stop", "length", "tool_calls", "content_filter", null]
                    }
                }
            }
        },
        "usage": {
            "type": "object",
            "required": ["prompt_tokens", "completion_tokens", "total_tokens"],
            "properties": {
                "prompt_tokens": {"type": "integer"},
                "completion_tokens": {"type": "integer"}, 
                "total_tokens": {"type": "integer"}
            }
        }
    }
}

def validate_openai_response(response_json):
    try:
        jsonschema.validate(response_json, openai_schema)
        return True, "Valid OpenAI response format"
    except jsonschema.ValidationError as e:
        return False, f"Invalid format: {e.message}"
```

## Success Criteria

### Immediate Requirements

1. **100% Schema Compliance:** All responses must pass JSON schema validation
2. **Response Consistency:** Identical inputs produce identical outputs across servers
3. **Error Standardization:** All errors follow consistent format with helpful messages
4. **Client Compatibility:** No breaking changes to existing integrations

### Performance Requirements

1. **Response Time:** Format processing adds <50ms to response time
2. **Memory Usage:** Formatting uses <1MB additional memory per request
3. **Throughput:** No reduction in requests per second capability

### Quality Requirements

1. **Test Coverage:** 100% code coverage for response formatting modules
2. **Integration Testing:** All major client libraries work without modification
3. **Documentation:** Complete API documentation with examples
4. **Monitoring:** Response format compliance tracked in production metrics

This checklist provides comprehensive validation criteria for ensuring both servers achieve full OpenAI and Anthropic API compliance with standardized response formats.