# Configuration Guide

This document provides comprehensive information about configuring the Salesforce Models API Gateway, including environment variables, configuration files, and settings for both OpenAI and Anthropic compatibility.

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Configuration Files](#configuration-files)
3. [OpenAI Compatibility Configuration](#openai-compatibility-configuration)
4. [Anthropic Compatibility Configuration](#anthropic-compatibility-configuration)
5. [Performance Tuning](#performance-tuning)
6. [Feature Flags](#feature-flags)
7. [Logging Configuration](#logging-configuration)

## Environment Variables

Environment variables provide a flexible way to configure the gateway without modifying configuration files. These can be set in your operating system, container environment, or deployment platform.

### Core Configuration

```bash
# Required Configuration
export SALESFORCE_CONSUMER_KEY="your_connected_app_consumer_key"
export SALESFORCE_USERNAME="your_username@company.com"
export SALESFORCE_INSTANCE_URL="https://your-instance.my.salesforce.com"

# Optional Configuration
export SALESFORCE_PRIVATE_KEY_FILE="/path/to/server.key"
export SALESFORCE_API_VERSION="v64.0"
export ENVIRONMENT="development"  # Options: development, production
export SF_RESPONSE_DEBUG="false"  # Set to "true" for detailed API response logging
```

### Anthropic Compatibility Configuration

```bash
# Enable Anthropic-compatible endpoints
export NATIVE_ANTHROPIC_ENABLED="1"  # Set to "0" to disable Anthropic endpoints

# Configure Anthropic model mapping file
export ANTHROPIC_MODEL_MAP="config/anthropic_models.map.json"

# Anthropic token validation strictness
export ANTHROPIC_VERSION_STRICT="1"  # Strict anthropic-version header validation
```

### OpenAI Front-Door Architecture

```bash
# Enable OpenAI Front-Door Architecture
export OPENAI_FRONTDOOR_ENABLED="1"  # Set to "0" to disable OpenAI Front-Door

# Model capabilities configuration
export MODEL_CAPABILITIES_JSON="{...}"  # JSON string with model capabilities
export MODEL_CAPABILITIES_FILE="config/models.yml"  # Path to model capabilities file
```

### Compatibility Options

```bash
# n8n Compatibility
export N8N_COMPAT_MODE="1"  # Set to "0" to disable n8n compatibility mode
export N8N_COMPAT_PRESERVE_TOOLS="1"  # Preserve tools for n8n clients

# Native tool passthrough
export OPENAI_NATIVE_TOOL_PASSTHROUGH="1"  # Direct passthrough for OpenAI models

# Logging verbosity
export VERBOSE_TOOL_LOGS="0"  # Set to "1" for detailed tool calling logs
```

### Performance Configuration

```bash
# Async performance settings
export CONNECTION_POOL_SIZE="20"  # Number of persistent connections in pool
export ASYNC_TIMEOUT_MS="300000"  # Async timeout in milliseconds (5 minutes)
export HEARTBEAT_INTERVAL_SEC="15"  # SSE heartbeat interval in seconds
export PROCESS_WORKERS="4"  # Number of worker processes for Gunicorn
```

## Configuration Files

The gateway uses several configuration files for different aspects of the system.

### Main Configuration (config.json)

The primary configuration file `config.json` contains Salesforce authentication details:

```json
{
  "consumer_key": "your_key",
  "username": "user@company.com",
  "private_key_file": "/path/to/server.key",
  "instance_url": "https://your-instance.my.salesforce.com",
  "api_version": "v64.0"
}
```

This file can be created from `config.json.example` in the project root.

### Anthropic Model Mapping (config/anthropic_models.map.json)

This file maps Anthropic model IDs to Salesforce model names:

```json
[
  {
    "anthropic_id": "claude-3-5-sonnet-latest",
    "sf_model": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
    "max_tokens": 4096,
    "supports_streaming": true,
    "display_name": "Claude 3.5 Sonnet",
    "description": "Latest Claude 3.5 Sonnet model with enhanced reasoning capabilities"
  },
  {
    "anthropic_id": "claude-3-haiku-20240307",
    "sf_model": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
    "max_tokens": 4096,
    "supports_streaming": true,
    "display_name": "Claude 3 Haiku",
    "description": "Fast and efficient Claude 3 Haiku model for quick responses"
  }
]
```

Each mapping includes:
- `anthropic_id`: The Anthropic model ID used in API requests
- `sf_model`: The corresponding Salesforce Einstein model name
- `max_tokens`: Maximum token limit for the model
- `supports_streaming`: Whether the model supports streaming responses
- `display_name`: Display name for the model
- `description`: Human-readable description of the model

### Model Capabilities Configuration (config/models.yml)

Configuration for model capabilities and backend routing:

```yaml
# OpenAI-Compatible models
gpt-4:
  openai_compatible: true
  backend_type: "openai_native"
  passthrough_tools: true

# Anthropic/Bedrock models
claude-3-sonnet:
  openai_compatible: false
  anthropic_bedrock: true
  backend_type: "anthropic_bedrock"
  requires_normalization: true
  
# Gemini models
gemini-pro:
  vertex_gemini: true
  backend_type: "vertex_gemini"
  requires_normalization: true
```

## OpenAI Compatibility Configuration

The OpenAI Front-Door architecture provides universal OpenAI v1 specification compliance with intelligent backend adapters.

### Model Capabilities Registry

The model capabilities registry is used to determine how requests should be routed based on model characteristics:

```python
from model_capabilities import caps_for, get_backend_type

# Check capabilities of a model
caps = caps_for("claude-3-sonnet")
# Returns: {'openai_compatible': false, 'anthropic_bedrock': true, ...}

# Get the backend type for routing
backend = get_backend_type("gpt-4")
# Returns: 'openai_native'
```

### Backend Types

The system supports various model backend types:

- `openai_native`: Direct passthrough for OpenAI-compatible models
- `anthropic_bedrock`: Normalization required for Anthropic/Bedrock models
- `vertex_gemini`: Normalization required for Google Vertex/Gemini models
- `generic`: Default fallback for unknown models

### Tool Behavior Configuration

Configure tool behavior with these environment variables:

```bash
# Tool configuration
export N8N_COMPAT_PRESERVE_TOOLS="1"  # Preserve tools for all clients (recommended)
export OPENAI_NATIVE_TOOL_PASSTHROUGH="1"  # Direct passthrough for OpenAI models
export TOOL_REPAIR_ENABLED="1"  # Enable tool-call repair shim
```

## Anthropic Compatibility Configuration

The Anthropic-compatible endpoints provide exact compliance with Anthropic's API specification.

### Enabling Anthropic Endpoints

```bash
# Enable Anthropic-compatible endpoints
export NATIVE_ANTHROPIC_ENABLED="1"  # Set to "0" to disable
```

### Model Mapping Configuration

The model mapping file is configured with:

```bash
# Configure Anthropic model mapping file
export ANTHROPIC_MODEL_MAP="config/anthropic_models.map.json"
```

### Anthropic Version Header Validation

Configure the strictness of `anthropic-version` header validation:

```bash
# Anthropic token validation strictness
export ANTHROPIC_VERSION_STRICT="1"  # Strict validation
```

When set to `1`, requests without a valid `anthropic-version` header will be rejected with a 400 error.

### Default Supported Versions

The current implementation supports these Anthropic API versions:

- `2023-06-01`

Future versions can be added by updating the `require_anthropic_headers` function in `anthropic_mapper.py`.

## Performance Tuning

The following configuration options can be adjusted to optimize performance:

### Connection Pooling

```bash
# Connection pool size (default: 20)
export CONNECTION_POOL_SIZE="20"
```

Increasing the connection pool size can improve throughput for high-concurrency workloads, but may increase memory usage.

### Async Timeout

```bash
# Async timeout in milliseconds (default: 300000 - 5 minutes)
export ASYNC_TIMEOUT_MS="300000"
```

Adjust based on expected response times for your models and request complexity.

### SSE Heartbeats

```bash
# SSE heartbeat interval in seconds (default: 15)
export HEARTBEAT_INTERVAL_SEC="15"
```

Server-Sent Events (SSE) heartbeats prevent connection timeouts during streaming responses.

### Worker Processes

```bash
# Number of worker processes for Gunicorn (default: CPU count)
export PROCESS_WORKERS="4"
```

For production deployments, set to 2-4× the number of CPU cores available.

### Memory Management

```bash
# Maximum conversation history size
export MAX_CONVERSATION_MESSAGES="50"
```

Limits the number of messages stored in conversation history to prevent memory leaks.

## Feature Flags

Feature flags enable or disable specific functionality:

### Core Features

```bash
# OpenAI Front-Door Architecture
export OPENAI_FRONTDOOR_ENABLED="1"  # Enable/disable

# Anthropic API Compatibility
export NATIVE_ANTHROPIC_ENABLED="1"  # Enable/disable
```

### Compatibility Features

```bash
# n8n Compatibility
export N8N_COMPAT_MODE="1"  # Enable/disable n8n compatibility mode

# Tool Calling Features
export N8N_COMPAT_PRESERVE_TOOLS="1"  # Preserve tools for n8n clients
export OPENAI_NATIVE_TOOL_PASSTHROUGH="1"  # Direct passthrough for OpenAI models
export TOOL_REPAIR_ENABLED="1"  # Enable tool-call repair shim
```

## Logging Configuration

Configure logging behavior with these settings:

```bash
# Logging levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_LEVEL="WARNING"  # Default log level

# Component-specific logging
export SF_RESPONSE_DEBUG="false"  # Set to "true" for API response logging
export VERBOSE_TOOL_LOGS="0"  # Set to "1" for detailed tool calling logs
```

### Development Mode Logging

In development mode, additional debug headers are added to responses:

```bash
# Enable development mode
export ENVIRONMENT="development"
```

This adds headers like `X-Stream-Downgraded` and `X-Proxy-Latency-Ms` to responses for easier troubleshooting.