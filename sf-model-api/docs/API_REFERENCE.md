# API Reference

This document provides a comprehensive reference for all endpoints available in the Salesforce Models API Gateway, including both OpenAI-compatible and Anthropic-compatible routes.

## Table of Contents

1. [OpenAI-Compatible Endpoints](#openai-compatible-endpoints)
   - [Health Check](#health-check)
   - [List Models](#list-models-openai)
   - [Chat Completions](#chat-completions)
   - [Completions](#completions)
2. [Anthropic-Compatible Endpoints](#anthropic-compatible-endpoints)
   - [List Models](#list-models-anthropic)
   - [Create Message](#create-message)
   - [Count Tokens](#count-tokens)
3. [Authentication Requirements](#authentication-requirements)
4. [Error Codes and Handling](#error-codes-and-handling)
5. [Rate Limiting](#rate-limiting)
6. [Request/Response Headers](#requestresponse-headers)

## OpenAI-Compatible Endpoints

The OpenAI-compatible API endpoints provide universal OpenAI v1 specification compliance with intelligent backend adapters for different model providers.

### Health Check

Returns the health status of the server.

**Request:**

```
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": 1709386587,
  "version": "1.0.0"
}
```

### List Models (OpenAI)

Returns a list of available models in OpenAI format.

**Request:**

```
GET /v1/models
```

**Response:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "claude-3-haiku",
      "object": "model",
      "created": 1709386587,
      "owned_by": "salesforce"
    },
    {
      "id": "claude-3-sonnet",
      "object": "model",
      "created": 1709386587,
      "owned_by": "salesforce"
    },
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1709386587,
      "owned_by": "salesforce"
    }
  ]
}
```

### Chat Completions

Creates a chat completion with the specified model.

**Request:**

```
POST /v1/chat/completions
```

**Headers:**
```
Content-Type: application/json
```

**Body:**

```json
{
  "model": "claude-3-haiku",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you today?"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false,
  "tools": [
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
  ],
  "tool_choice": "auto"
}
```

**Parameters:**

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| model | string | The ID of the model to use | Yes |
| messages | array | An array of message objects | Yes |
| temperature | number | Controls randomness (0.0-1.0, default: 0.7) | No |
| max_tokens | number | Maximum number of tokens to generate (default: 1000) | No |
| stream | boolean | Whether to stream the response (default: false) | No |
| tools | array | Tool definitions for function calling | No |
| tool_choice | object or string | Tool choice preference | No |

**Non-streaming Response:**

```json
{
  "id": "chatcmpl-123abc",
  "object": "chat.completion",
  "created": 1709386587,
  "model": "claude-3-haiku",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking. I'm Claude, an AI assistant. How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 24,
    "completion_tokens": 21,
    "total_tokens": 45
  }
}
```

**Tool Calling Response:**

```json
{
  "id": "chatcmpl-123abc",
  "object": "chat.completion",
  "created": 1709386587,
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
              "arguments": "{\"location\":\"San Francisco, CA\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 45,
    "completion_tokens": 26,
    "total_tokens": 71
  }
}
```

**Streaming Response:**

When `stream=true`, the response will be sent as a series of Server-Sent Events (SSE):

```
data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1709386587,"model":"claude-3-haiku","choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1709386587,"model":"claude-3-haiku","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1709386587,"model":"claude-3-haiku","choices":[{"index":0,"delta":{"content":" I'm"},"finish_reason":null}]}

data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1709386587,"model":"claude-3-haiku","choices":[{"index":0,"delta":{"content":" Claude"},"finish_reason":null}]}

data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1709386587,"model":"claude-3-haiku","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**Note:** When both `stream=true` and `tools` are specified, streaming is automatically downgraded to non-streaming mode for compatibility with tool calling. The response will include an `X-Stream-Downgraded: true` header.

### Completions

Creates a completion with the specified model (legacy endpoint for compatibility).

**Request:**

```
POST /v1/completions
```

**Headers:**
```
Content-Type: application/json
```

**Body:**

```json
{
  "model": "claude-3-haiku",
  "prompt": "Once upon a time",
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**Parameters:**

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| model | string | The ID of the model to use | Yes |
| prompt | string | The prompt to complete | Yes |
| temperature | number | Controls randomness (0.0-1.0, default: 0.7) | No |
| max_tokens | number | Maximum number of tokens to generate (default: 1000) | No |
| stream | boolean | Whether to stream the response (default: false) | No |

**Response:**

```json
{
  "id": "cmpl-123abc",
  "object": "text_completion",
  "created": 1709386587,
  "model": "claude-3-haiku",
  "choices": [
    {
      "text": " there was a kingdom by the sea. In this kingdom lived a young princess with hair as golden as the sun.",
      "index": 0,
      "finish_reason": "length"
    }
  ],
  "usage": {
    "prompt_tokens": 4,
    "completion_tokens": 26,
    "total_tokens": 30
  }
}
```

## Anthropic-Compatible Endpoints

The Anthropic-compatible API endpoints provide exact compliance with Anthropic's API specification while integrating with Salesforce's Einstein Trust Layer Models.

### List Models (Anthropic)

Returns a list of available Anthropic models.

**Request:**

```
GET /anthropic/v1/models
```

**Headers:**
```
anthropic-version: 2023-06-01
```

**Response:**

```json
{
  "data": [
    {
      "id": "claude-3-haiku-20240307",
      "name": "Claude 3 Haiku",
      "description": "Fast and efficient Claude 3 Haiku model for quick responses",
      "max_tokens": 4096,
      "created": 1709806072,
      "object": "model"
    },
    {
      "id": "claude-3-sonnet-20240229",
      "name": "Claude 3 Sonnet",
      "description": "Balanced Claude 3 Sonnet model for general-purpose tasks",
      "max_tokens": 4096,
      "created": 1709201272,
      "object": "model"
    },
    {
      "id": "claude-3-opus-20240229",
      "name": "Claude 3 Opus",
      "description": "Most capable Claude 3 model for complex reasoning tasks",
      "max_tokens": 4096,
      "created": 1709201272,
      "object": "model"
    },
    {
      "id": "claude-3-5-sonnet-latest",
      "name": "Claude 3.5 Sonnet",
      "description": "Latest Claude 3.5 Sonnet model with enhanced reasoning capabilities",
      "max_tokens": 4096,
      "created": 1722589472,
      "object": "model"
    }
  ],
  "has_more": false,
  "first_id": "claude-3-haiku-20240307",
  "last_id": "claude-3-5-sonnet-latest"
}
```

### Create Message

Generates a message using the specified Claude model.

**Request:**

```
POST /anthropic/v1/messages
```

**Headers:**
```
Content-Type: application/json
anthropic-version: 2023-06-01
```

**Body:**

```json
{
  "model": "claude-3-haiku-20240307",
  "messages": [
    {
      "role": "user",
      "content": "Hello, Claude! How are you today?"
    }
  ],
  "max_tokens": 1000,
  "temperature": 0.7,
  "system": "You are a helpful AI assistant.",
  "stream": false
}
```

**Parameters:**

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| model | string | The ID of the model to use | Yes |
| messages | array | An array of message objects | Yes |
| max_tokens | number | Maximum number of tokens to generate (default: 1000) | No |
| temperature | number | Controls randomness (0.0-1.0, default: 0.7) | No |
| system | string | System message providing context or instructions | No |
| stream | boolean | Whether to stream the response (default: false) | No |
| tools | array | Tool definitions for function calling (if supported) | No |
| tool_choice | object or string | Tool choice preference (if supported) | No |

**Non-streaming Response:**

```json
{
  "id": "msg_01ABC123DEF456",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! I'm doing well, thank you for asking. I'm Claude, an AI assistant created by Anthropic. I'm here to help you with information, answer questions, assist with tasks, or just chat. How can I help you today?"
    }
  ],
  "model": "claude-3-haiku-20240307",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 23,
    "output_tokens": 48
  }
}
```

**Streaming Response:**

When `stream=true`, the response will be sent as a series of Server-Sent Events (SSE) following Anthropic's exact event sequence:

```
event: message_start
data: {"type": "message_start", "message": {"id": "msg_01ABC123DEF456", "type": "message", "role": "assistant", "content": [], "model": "claude-3-haiku-20240307", "stop_reason": null, "stop_sequence": null, "usage": {"input_tokens": 18}}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello! "}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "I'm "}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "doing "}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null, "usage": {"output_tokens": 31}}}

event: message_stop
data: {"type": "message_stop"}
```

### Count Tokens

Counts the number of tokens in a message.

**Request:**

```
POST /anthropic/v1/messages/count_tokens
```

**Headers:**
```
Content-Type: application/json
anthropic-version: 2023-06-01
```

**Body:**

```json
{
  "model": "claude-3-haiku-20240307",
  "messages": [
    {
      "role": "user",
      "content": "Hello, Claude! How are you today?"
    }
  ],
  "system": "You are a helpful AI assistant."
}
```

**Response:**

```json
{
  "input_tokens": 23
}
```

## Authentication Requirements

### OpenAI-Compatible Endpoints

For the OpenAI-compatible endpoints, authentication is handled internally through Salesforce OAuth. No client authentication is required for local deployments.

For production deployments, you may need to configure API key validation based on your security requirements.

### Anthropic-Compatible Endpoints

For the Anthropic-compatible endpoints, the following headers are required:

- `anthropic-version`: (Required) The Anthropic API version to use. Currently supported: `2023-06-01`

Authentication is handled internally through Salesforce OAuth. No client authentication is required for local deployments.

## Error Codes and Handling

### OpenAI-Compatible Error Format

```json
{
  "error": {
    "message": "Invalid model: invalid-model-name",
    "type": "invalid_request_error",
    "code": "invalid_model",
    "details": {
      "available_models": ["claude-3-haiku", "claude-3-sonnet", "gpt-4"]
    }
  }
}
```

### Anthropic-Compatible Error Format

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Missing required parameter: model"
  }
}
```

### Common HTTP Status Codes

| Status Code | Description | Example Scenarios |
|-------------|-------------|-------------------|
| 200 | OK | Successful request |
| 400 | Bad Request | Missing required parameters, invalid model |
| 401 | Unauthorized | Invalid or expired credentials |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limits exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Server temporarily unavailable |

## Rate Limiting

Rate limiting is managed through the Salesforce Einstein Trust Layer. Specific limits depend on your Salesforce org configuration and licensing.

If rate limits are exceeded, the API will return a 429 status code with an appropriate error message.

## Request/Response Headers

### Common Request Headers

| Header | Description | Required |
|--------|-------------|----------|
| Content-Type | Must be `application/json` for requests with a body | Yes |
| anthropic-version | Required for Anthropic endpoints. Example: `2023-06-01` | Yes (for Anthropic endpoints) |

### Common Response Headers

| Header | Description |
|--------|-------------|
| Content-Type | `application/json` for non-streaming responses, `text/event-stream` for streaming |
| X-Stream-Downgraded | `true` if streaming was downgraded to non-streaming (e.g., for tool calls) |
| X-Proxy-Latency-Ms | Server processing time in milliseconds |
| Cache-Control | Cache control directives (e.g., `no-cache, no-store, must-revalidate`) |
| Access-Control-Allow-Origin | CORS headers for browser clients |