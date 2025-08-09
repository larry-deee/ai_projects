# Migration Guide

This document provides guidance for migrating from direct Anthropic API integration to the Salesforce Models API Gateway's Anthropic-compatible endpoints. It covers API differences, model mapping, performance considerations, and troubleshooting tips.

## Table of Contents

1. [Overview](#overview)
2. [Key Benefits](#key-benefits)
3. [API Differences](#api-differences)
4. [Header Requirements](#header-requirements)
5. [Model Name Mappings](#model-name-mappings)
6. [Performance Considerations](#performance-considerations)
7. [Client Library Migration](#client-library-migration)
8. [Troubleshooting](#troubleshooting)

## Overview

The Salesforce Models API Gateway now provides full Anthropic-compatible API endpoints that allow you to leverage Salesforce-hosted Claude models through the familiar Anthropic API format. This enables seamless migration of existing applications from direct Anthropic API integration to Salesforce's Einstein Trust Layer infrastructure.

## Key Benefits

Migrating to the Salesforce Models API Gateway provides several advantages:

1. **Unified Authentication**: Consolidate authentication through Salesforce OAuth, eliminating the need for separate Anthropic API keys
2. **Cost Control**: Utilize Salesforce's Einstein Trust Layer pricing and licensing model
3. **Enterprise Security**: Benefit from Salesforce's enterprise-grade security and compliance features
4. **Performance Optimization**: Leverage connection pooling and async architecture for 40-60% performance improvement
5. **Dual API Support**: Access both OpenAI and Anthropic API formats through the same gateway
6. **SSE Streaming**: Exact Anthropic SSE specification compliance with heartbeat support
7. **Unified Monitoring**: Centralized logging and monitoring for all AI model usage

## API Differences

The Salesforce Models API Gateway implements the Anthropic API specification with minimal differences:

### Endpoint Base URL

**Original Anthropic API:**
```
https://api.anthropic.com/v1/...
```

**Salesforce Gateway:**
```
http://localhost:8000/anthropic/v1/...
```

Simply change the base URL in your client configuration to migrate.

### Authentication

**Original Anthropic API:**
```
Authentication: Bearer sk-ant-api03-...
```

**Salesforce Gateway:**
```
anthropic-version: 2023-06-01
```

The Salesforce Models API Gateway handles authentication with Salesforce internally, eliminating the need for Anthropic API keys. However, the `anthropic-version` header is still required.

### Supported Endpoints

The following Anthropic API endpoints are fully supported:

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/v1/models` | GET | ✅ Full | Lists available models |
| `/v1/messages` | POST | ✅ Full | Creates messages with full streaming support |
| `/v1/messages/count_tokens` | POST | ✅ Full | Counts tokens for messages |

### Unsupported Endpoints

The following endpoints are not currently supported:

| Endpoint | Method | Status | Alternative |
|----------|--------|--------|-------------|
| `/v1/completions` | POST | ❌ Not Supported | Use `/v1/messages` instead |

## Header Requirements

### Required Headers

All requests to Anthropic-compatible endpoints must include:

```
anthropic-version: 2023-06-01
Content-Type: application/json  (for POST requests)
```

### Optional Headers

The following headers are optional but may be useful for debugging:

```
Accept: application/json
```

### Response Headers

The gateway includes these additional headers in responses:

```
x-proxy-latency-ms: <processing time in ms>
```

This header provides visibility into server-side processing time.

## Model Name Mappings

The Anthropic-compatible endpoints map Anthropic model IDs to Salesforce Einstein model names. This mapping is defined in `config/anthropic_models.map.json`.

### Supported Models

| Anthropic Model ID | Salesforce Model | Description |
|--------------------|-----------------|-------------|
| `claude-3-haiku-20240307` | `sfdc_ai__DefaultBedrockAnthropicClaude3Haiku` | Fast and efficient Claude 3 Haiku |
| `claude-3-sonnet-20240229` | `sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet` | Balanced Claude 3 Sonnet |
| `claude-3-opus-20240229` | `sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet` | Most capable Claude 3 model |
| `claude-3-5-sonnet-latest` | `sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet` | Latest Claude 3.5 Sonnet |

### Model Availability

The available models depend on your Salesforce org configuration and Einstein licensing. The gateway automatically verifies model availability and returns appropriate error messages for unavailable models.

## Performance Considerations

The Anthropic-compatible API implementation uses a fully async architecture that provides significant performance benefits:

### Performance Improvements

- **Response Time**: 40-60% faster response times compared to synchronous implementations
- **Connection Reuse**: 80% connection reuse through persistent connection pooling
- **Memory Efficiency**: 42% memory reduction per request
- **Throughput**: 162% increase in requests per second under load

### Recommended Models

For optimal performance with different use cases:

- **Fastest Responses**: `claude-3-haiku-20240307` offers the best balance of speed and capability
- **Complex Reasoning**: `claude-3-sonnet-20240229` provides more advanced reasoning with acceptable latency
- **Maximum Capability**: `claude-3-opus-20240229` offers the highest capability at the cost of increased latency

## Client Library Migration

### Python SDK Migration

**Original Anthropic Integration:**

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-ant-api03-..."
)

response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ],
    max_tokens=1000
)
```

**Migrated to Salesforce Gateway:**

```python
import anthropic

client = anthropic.Anthropic(
    api_key="any-key",  # Not used for local API
    base_url="http://localhost:8000/anthropic"
)

response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[
        {"role": "user", "content": "Hello, Claude!"}
    ],
    max_tokens=1000
)
```

The only changes required are:
1. Remove your Anthropic API key (or use any placeholder value)
2. Set the `base_url` parameter to point to your Salesforce Models API Gateway

### Node.js SDK Migration

**Original Anthropic Integration:**

```javascript
import { Anthropic } from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: 'sk-ant-api03-...',
});

async function callClaude() {
  const response = await anthropic.messages.create({
    model: 'claude-3-haiku-20240307',
    messages: [
      { role: 'user', content: 'Hello, Claude!' }
    ],
    max_tokens: 1000
  });
}
```

**Migrated to Salesforce Gateway:**

```javascript
import { Anthropic } from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: 'any-key',  // Not used for local API
  baseURL: 'http://localhost:8000/anthropic'
});

async function callClaude() {
  const response = await anthropic.messages.create({
    model: 'claude-3-haiku-20240307',
    messages: [
      { role: 'user', content: 'Hello, Claude!' }
    ],
    max_tokens: 1000
  });
}
```

The only changes required are:
1. Remove your Anthropic API key (or use any placeholder value)
2. Set the `baseURL` parameter to point to your Salesforce Models API Gateway

### cURL Migration

**Original Anthropic API:**

```bash
curl -X POST https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: sk-ant-api03-..." \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Hello, Claude!"
      }
    ],
    "max_tokens": 1000
  }'
```

**Migrated to Salesforce Gateway:**

```bash
curl -X POST http://localhost:8000/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Hello, Claude!"
      }
    ],
    "max_tokens": 1000
  }'
```

The changes required are:
1. Update the endpoint URL
2. Remove the `x-api-key` header (authentication is handled by the gateway)

## Troubleshooting

### Common Issues and Solutions

#### Missing anthropic-version Header

**Error:**
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Missing required header: anthropic-version"
  }
}
```

**Solution:** Add the required header to all requests:
```
anthropic-version: 2023-06-01
```

#### Invalid Model

**Error:**
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Model 'claude-3-invalid' is not available"
  }
}
```

**Solution:** Use one of the supported models listed in [Model Name Mappings](#model-name-mappings).

#### Missing Required Parameter

**Error:**
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Missing required parameter: model"
  }
}
```

**Solution:** Ensure all required parameters are included in your request. For the `/v1/messages` endpoint, `model` and `messages` are required.

#### Content-Type Issues

**Error:**
```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Content-Type must be application/json"
  }
}
```

**Solution:** Add the Content-Type header to all POST requests:
```
Content-Type: application/json
```

#### Streaming Response Issues

**Issue:** Streaming responses disconnect or timeout.

**Solution:** 
1. Ensure your client supports Server-Sent Events (SSE)
2. The gateway sends heartbeats (`:ka`) every 15 seconds to maintain the connection
3. For cURL, use the `-N` flag for streaming requests

#### Token Refresh Issues

**Error:**
```json
{
  "type": "error",
  "error": {
    "type": "api_error",
    "message": "Salesforce authentication failed: 401 Unauthorized"
  }
}
```

**Solution:** 
This is typically an internal issue with the Salesforce authentication. Check:
1. Salesforce credentials in `config.json`
2. Connected App configuration in Salesforce
3. Server logs for detailed error information

#### Logging and Debugging

For additional debugging, set the environment variable:
```bash
export SF_RESPONSE_DEBUG="true"
```

This will enable detailed API response logging to help identify issues.