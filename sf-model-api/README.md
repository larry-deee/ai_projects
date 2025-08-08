# Salesforce Models API Gateway

A production-ready OpenAI-compatible API gateway that provides seamless access to Salesforce's Einstein Trust Layer Models API. This gateway enables organizations to leverage their Salesforce AI investments across their entire technology stack with full compatibility for existing LLM applications and workflows.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Salesforce org with Einstein Trust Layer access
- Connected App configured with proper OAuth scopes
- Private key file for JWT authentication

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-org/models-api.git
cd models-api
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure authentication:**
```bash
# Create config file from template
cp config.json.example config.json

# Edit config.json with your Salesforce credentials
# OR set environment variables:
export SALESFORCE_CONSUMER_KEY="your_connected_app_key"
export SALESFORCE_USERNAME="your_username@company.com"
export SALESFORCE_PRIVATE_KEY_FILE="/path/to/server.key"
export SALESFORCE_INSTANCE_URL="https://your-instance.my.salesforce.com"
```

4. **Start the server:**
```bash
# Development - Flask Server (Legacy)
python llm_endpoint_server.py

# Development - ASGI Server (Recommended for Local Development)
uvicorn src.async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11

# Production
gunicorn -c gunicorn_config.py llm_endpoint_server:app
```

5. **Test the installation:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
```

## 🎯 Key Features

- ✅ **100% OpenAI API Compatible** - Universal OpenAI v1 specification compliance with all model backends
- ✅ **Backend Adapters Architecture** - Intelligent routing and normalization for OpenAI, Anthropic, and Gemini models
- ✅ **Complete Tool Calling** - Full OpenAI function calling with automatic tool-call repair shim
- ✅ **n8n Compatibility Mode** - Full tool preservation with seamless integration for all models
- ✅ **Model Capabilities Registry** - Configuration-driven model routing based on capabilities
- ✅ **Enterprise Authentication** - OAuth 2.0 Client Credentials Flow with token pre-warming and aggressive management
- ✅ **Thread-Safe Architecture** - Scalable design with multi-layer token caching
- ✅ **Smart Timeout Management** - Dynamic timeouts based on request characteristics
- ✅ **Streaming Support** - Real-time response streaming with proper OpenAI chunk formatting and SSE heartbeats
- ✅ **Production Ready** - Comprehensive logging, monitoring, and deployment automation
- ✅ **Multi-Model Access** - Support for Claude, GPT-4, and Gemini models through Salesforce

## 📁 Project Structure

```
sf-model-api/
├── src/                          # Core application code
│   ├── llm_endpoint_server.py    # Main Flask application with OpenAI endpoints
│   ├── async_endpoint_server.py  # Async Quart application (recommended)
│   ├── salesforce_models_client.py # Core Salesforce API client with OAuth 2.0
│   ├── streaming_architecture.py # Advanced streaming response system
│   ├── tool_handler.py          # Tool calling orchestration and execution
│   ├── tool_schemas.py          # Pydantic models for tool validation
│   ├── unified_response_formatter.py # Response format standardization
│   ├── model_capabilities.py     # Model capability registry and routing
│   ├── openai_spec_adapter.py   # Backend adapter framework for OpenAI compliance
│   └── openai_tool_fix.py       # Tool-call repair shim for universal compatibility
├── tests/                       # Comprehensive test suite
│   ├── test_streaming_*.py      # Streaming functionality tests
│   ├── test_tool_calling.py     # Tool calling tests
│   ├── test_api_compliance_*.py # API compliance tests
│   ├── test_openai_frontdoor.py # OpenAI front-door architecture tests
│   └── test_tool_repair_shim.py # Tool-call repair tests
├── docs/                        # Comprehensive documentation
│   ├── ARCHITECTURE.md          # System architecture and components
│   ├── COMPATIBILITY.md         # Client integration guide
│   ├── TESTING.md               # Testing procedures and commands
│   └── reports/                 # QA validation reports
├── start_async_service.sh       # Async server startup script (recommended)
├── start_llm_service.sh         # Legacy sync server startup script
├── streaming_regression_tests.sh # Streaming validation tests
├── config.json                  # Server configuration
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
└── README.md                    # This file
```

## 🔧 Configuration

### Environment Variables (Recommended)

```bash
# Required Configuration
export SALESFORCE_CONSUMER_KEY="your_connected_app_consumer_key"
export SALESFORCE_USERNAME="your_username@company.com"
export SALESFORCE_INSTANCE_URL="https://your-instance.my.salesforce.com"

# Optional Configuration
export SALESFORCE_PRIVATE_KEY_FILE="/path/to/server.key"
export SALESFORCE_API_VERSION="v64.0"
export ENVIRONMENT="development"
export SF_RESPONSE_DEBUG="false"

# OpenAI Front-Door Architecture
export OPENAI_FRONTDOOR_ENABLED="1"        # Enable new architecture (recommended)
export MODEL_CAPABILITIES_JSON="{...}"     # Optional: Override model capabilities via JSON
export MODEL_CAPABILITIES_FILE="config/models.yml"  # Optional: Model config file path

# Compatibility Options
export N8N_COMPAT_MODE="1"              # Set to "0" to disable n8n compatibility mode
export N8N_COMPAT_PRESERVE_TOOLS="1"   # Preserve tools for n8n clients (recommended)
export OPENAI_NATIVE_TOOL_PASSTHROUGH="1" # Direct passthrough for OpenAI models
export VERBOSE_TOOL_LOGS="0"           # Set to "1" for detailed tool calling logs
```

### Configuration File

Create `config.json` from `config.json.example`:

```json
{
  "consumer_key": "your_key",
  "username": "user@company.com",
  "private_key_file": "/path/to/server.key",
  "instance_url": "https://your-instance.my.salesforce.com",
  "api_version": "v64.0"
}
```

## 📚 API Usage

### OpenAI-Compatible Endpoints

The server provides universal OpenAI v1 specification-compatible endpoints on `http://localhost:8000`:

- `GET /health` - Health check endpoint
- `GET /v1/models` - List available models in OpenAI format
- `POST /v1/chat/completions` - Chat completion with universal tool calling support
- `POST /v1/completions` - Text completion (legacy compatibility)

All responses conform to OpenAI v1 specification regardless of the backend model provider (OpenAI, Anthropic, or Gemini).

### Basic Usage

```python
import openai

client = openai.OpenAI(
    api_key="any-key",  # Not used for local API
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ]
)
print(response.choices[0].message.content)
```

### Tool Calling

```python
response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[
        {"role": "user", "content": "Calculate 15 + 27 * 3"}
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            }
        }
    }],
    tool_choice="auto"
)
```

### Streaming with SSE Heartbeats

```python
from openai import OpenAI
import json

client = OpenAI(
    api_key="any-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[{"role": "user", "content": "Write a long story about a space explorer"}],
    stream=True
)

# Stream will include heartbeats every ~15s to prevent connection timeouts
for chunk in response:
    if chunk.choices:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
```

**Note**: When both `stream=True` and `tools` are specified, streaming is automatically downgraded to non-streaming mode for compatibility with tool calling. The response will include an `X-Stream-Downgraded: true` header.

## 🧪 Testing

For comprehensive testing information, see [docs/TESTING.md](docs/TESTING.md)

```bash
# Quick smoke test
curl http://localhost:8000/health

# Run streaming regression tests
./streaming_regression_tests.sh

# Test basic chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}]}'
```

### Key Verification Points

- **Tool Calling + Stream**: When both `stream=true` and `tools` are specified, streaming automatically downgrades to non-streaming mode (`X-Stream-Downgraded: true` header)
- **Heartbeats**: SSE heartbeats (`:ka`) are sent every ~15s to prevent connection timeouts
- **Latency Headers**: All responses include `X-Proxy-Latency-Ms` header

See the full testing guide for detailed procedures and validation steps.

## 🚀 Deployment

### Local Development

```bash
# ASGI Server (Recommended for Local Development)
uvicorn src.async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11

# Flask Server (Legacy)
python llm_endpoint_server.py
```

#### Debug Headers

Local development includes debug headers for easier troubleshooting:

- `X-Stream-Downgraded: true|false` - Indicates if streaming was downgraded to non-streaming for tool calls
- `X-Proxy-Latency-Ms: <int>` - Server processing time in milliseconds

These headers are automatically added to all responses in development mode.

### Streaming Behavior

For detailed information on streaming behavior and client integration, see [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md#streaming-behavior--headers)

#### Key Features

- **SSE Heartbeats**: Sent every ~15 seconds to prevent connection timeouts
- **Stream Downgrade**: Automatic downgrade from streaming to non-streaming when using tool calling
- **Debug Headers**: All responses include performance and status headers

This behavior ensures compatibility with tools like n8n v1.105.4 and Claude Code.

### Behavior

The API gateway implements the OpenAI Front-Door architecture with intelligent backend adapters for different model providers:

- **OpenAI-Native Models**: Direct passthrough with optimal performance
- **Anthropic Models**: Claude format → OpenAI tool_calls normalization
- **Gemini Models**: Vertex AI format → OpenAI tool_calls normalization
- **Tool-Call Repair**: Automatic fix for "Tool call missing function name" errors

When `tools` are present in a request from an n8n client or openai/js client (detected via User-Agent) or when `N8N_COMPAT_MODE=1` is set, the gateway automatically:

- Returns non-streaming responses even when `stream=true` is requested
- Adds `x-stream-downgraded: true` header to indicate streaming was disabled
- Preserves tools for all clients and model backends
- Adds `x-proxy-latency-ms` header to all non-streaming responses for diagnostics

These adaptations ensure seamless integration with n8n workflows while maintaining full functionality for other clients. Regular clients continue to receive streaming responses (unless tools are present, which always requires stream downgrading). Set `N8N_COMPAT_MODE=0` to disable this behavior if needed.

### Production

```bash
# Using Gunicorn (recommended)
gunicorn -c gunicorn_config.py llm_endpoint_server:app

# Or using the startup script
./scripts/start_llm_service.sh
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8000

CMD ["gunicorn", "-c", "config/gunicorn_config.py", "src.llm_endpoint_server:app"]
```

## 🔍 Available Models

For full model details and configuration, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#model-access--configuration)

- **Claude Models**: `claude-3-haiku`, `claude-3-sonnet`, `claude-3-opus`, `claude-4-sonnet`
- **OpenAI Models**: `gpt-4`, `gpt-3.5-turbo`
- **Google Models**: `gemini-pro`, `gemini-pro-vision`

*Note: Available models depend on your Salesforce org configuration and Einstein licensing.*

## 🛠️ Troubleshooting

### Authentication Issues

**Problem**: "Failed to obtain access token" (rare with token pre-warming enabled)

**Solution**:
1. Verify environment variables are set correctly
2. Check private key file permissions (`chmod 600 server.key`)
3. Confirm Connected App configuration in Salesforce
4. Ensure OAuth scopes: `api`, `einstein_gpt_api`, `sfap_api`

### Timeout Issues

**Problem**: Requests timeout after several minutes

**Solution**:
1. Use faster models for large prompts (`claude-3-haiku`)
2. Check timeout configuration in `gunicorn_config.py`
3. Enable debug logging: `export SF_RESPONSE_DEBUG=true`
4. For streaming responses, SSE heartbeats should prevent timeouts

### Tool Calling Issues

**Problem**: Tool calls not executed properly

**Solution**:
1. Verify tool definitions follow OpenAI specification
2. Check function names are valid (letters, numbers, underscores, hyphens)
3. Ensure required parameters are properly defined
4. For streaming with tools, note that stream is automatically downgraded to non-streaming

### Streaming Issues

**Problem**: Streaming responses disconnect or timeout

**Solution**:
1. Check client connection timeout settings
2. SSE heartbeats (`:ka`) should maintain the connection
3. View `X-Stream-Downgraded` header to check if streaming was disabled
4. Check `X-Proxy-Latency-Ms` to identify server-side processing delays

## 🏗️ Integration Examples

For comprehensive integration guidelines, see [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)

### Open WebUI
```bash
OpenAI API Base URL: http://localhost:8000/v1
API Key: any-key
```

### n8n Workflow
```json
{
  "method": "POST",
  "url": "http://localhost:8000/v1/chat/completions",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "model": "claude-3-haiku",
    "messages": [{"role": "user", "content": "Process this data"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "extract_data",
        "description": "Extract structured data",
        "parameters": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"}
          }
        }
      }
    }]
  }
}
```

The n8n compatibility mode is automatically enabled for n8n and openai/js User-Agents, ensuring proper handling of tool requests and streaming behavior. Token pre-warming during server startup eliminates first-request authentication delays.

### LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="claude-3-sonnet",
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="any-key"
)
```

## 🔒 Security Best Practices

- 🔒 Never commit private keys or credentials to version control
- 🔒 Use environment variables for sensitive configuration
- 🔒 Rotate certificates regularly (every 90 days recommended)
- 🔒 Restrict server access in production environments
- 🔒 Monitor API usage to prevent abuse
- 🔒 Implement rate limiting for public-facing deployments

## 📈 Performance Optimization

For detailed performance characteristics and optimization guidance, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#performance-characteristics)

- **Async Server**: Up to 60% faster response times with async implementation
- **Token Caching**: Optimized authentication reduces overhead by 75%
- **Connection Pooling**: 80% TCP connection reuse rate
- **Memory Management**: Bounded conversation history prevents leaks
- **Optimized Extraction**: Efficient response parsing with 89% single-path success

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📞 Support

For issues and questions:

1. Check the [troubleshooting section](#🛠️-troubleshooting)
2. Review the comprehensive documentation in the `docs/` directory:
   - [Architecture Guide](docs/ARCHITECTURE.md)
   - [Compatibility Guide](docs/COMPATIBILITY.md)
   - [Testing Guide](docs/TESTING.md)
3. Test with `GET /health` endpoint first
4. Run `./streaming_regression_tests.sh` to verify core functionality

---

**Note**: This project provides a bridge between OpenAI-compatible applications and Salesforce's Einstein Trust Layer. Ensure your Salesforce org has the necessary Einstein licensing and API access configured.