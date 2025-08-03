# Salesforce Models API Gateway

A production-ready OpenAI-compatible API gateway that provides seamless access to Salesforce's Einstein Trust Layer Models API. This gateway enables organizations to leverage their Salesforce AI investments across their entire technology stack with full compatibility for existing LLM applications and workflows.

## Overview

This API gateway acts as a bridge between standard LLM applications and Salesforce's hosted AI models (Claude, GPT-4, Gemini), providing:

- **OpenAI API Compatibility**: 100% compatible with OpenAI's API specification
- **Enterprise-Ready**: Production-grade deployment with robust authentication and monitoring
- **Tool Calling Support**: Complete OpenAI function calling implementation with sandboxed execution
- **Multi-Model Access**: Support for Claude, GPT-4, and Gemini models through Salesforce
- **Intelligent Timeout Management**: Dynamic timeout calculation with graceful error handling

## Key Features

- ✅ **Full OpenAI Compatibility**: Works with OpenWebUI, n8n, LangChain, and standard OpenAI clients
- ✅ **Complete Tool Calling**: OpenAI function calling with built-in safe functions and passthrough mode
- ✅ **Enterprise Authentication**: OAuth 2.0 Client Credentials Flow with aggressive token management
- ✅ **Thread-Safe Design**: Scalable architecture with multi-layer token caching
- ✅ **Smart Timeout Management**: Dynamic timeouts based on request characteristics and model types
- ✅ **Production Ready**: Comprehensive logging, monitoring, and deployment automation
- ✅ **Enhanced Error Handling**: Actionable error messages with specific recommendations
- ✅ **Multi-Environment Support**: Optimized configurations for development and production

## Project Structure

```
models-api-github/
├── src/                          # Core source code
│   ├── llm_endpoint_server.py    # Main Flask application with OpenAI endpoints
│   ├── salesforce_models_client.py # Core Salesforce API client with OAuth 2.0
│   ├── tool_handler.py           # Tool calling orchestration and prompt engineering
│   ├── tool_schemas.py           # Pydantic models for tool validation
│   ├── tool_executor.py          # Sandboxed function execution engine
│   ├── cli.py                    # Command-line interface for testing
│   ├── streaming_architecture.py # Streaming response implementation
│   └── gunicorn_config.py        # Production server configuration
├── tests/                        # Comprehensive test suite
│   ├── test_tool_calling.py      # Tool calling functionality tests
│   ├── test_streaming_*.py       # Streaming architecture tests
│   ├── test_auth_*.py            # Authentication flow tests
│   └── test_*.py                 # Additional component tests
├── docs/                         # Complete documentation
│   ├── TOOL_CALLING_DOCUMENTATION.md
│   ├── TIMEOUT_FIX_REPORT.md
│   ├── OPENAI_COMPATIBILITY_FIXES.md
│   ├── ARCHITECTURE_ANALYSIS.md
│   └── *.md                      # Additional documentation
├── config/                       # Configuration examples
│   ├── config.json.example       # Configuration template
│   └── config.json.template      # Alternative template
├── scripts/                      # Deployment and setup scripts
│   ├── quick_install.sh          # Quick installation script
│   ├── setup_portable.py         # Portable setup utility
│   └── *.sh                      # Additional setup scripts
├── examples/                     # Usage examples and demos
│   ├── examples.py               # Basic usage examples
│   ├── integration_examples.py   # Integration examples
│   └── *.py                      # Additional examples
├── requirements.txt              # Python dependencies
├── LICENSE                       # MIT License
└── README.md                     # This file
```

## Quick Start

### 1. Prerequisites

Ensure you have Salesforce Einstein Trust Layer access configured:

- ✅ Salesforce Connected App with proper OAuth scopes
- ✅ Environment variables configured for authentication
- ✅ Private key file for JWT authentication (if using JWT flow)
- ✅ Einstein/Models API enabled in your Salesforce org
- ✅ Appropriate Einstein licensing for desired models

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/models-api-gateway.git
cd models-api-gateway

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `config.json` from the example in `config/`:

```bash
# Copy configuration template
cp config/config.json.example config.json

# Edit with your Salesforce credentials
nano config.json
```

Example configuration:
```json
{
  "consumer_key": "your_salesforce_consumer_key_here",
  "username": "your_username@company.com",
  "private_key_file": "/path/to/your/server.key",
  "instance_url": "https://your-instance.my.salesforce.com",
  "api_version": "v64.0",
  "default_model": "claude-3-haiku",
  "default_max_tokens": 1000,
  "default_temperature": 0.7
}
```

Or use environment variables:
```bash
export SALESFORCE_CONSUMER_KEY="your_consumer_key"
export SALESFORCE_USERNAME="your_username@company.com"
export SALESFORCE_PRIVATE_KEY_FILE="/path/to/server.key"
export SALESFORCE_INSTANCE_URL="https://your-instance.my.salesforce.com"
export SALESFORCE_API_VERSION="v64.0"
```

### 4. Test the Installation

```bash
# Start the development server
python src/llm_endpoint_server.py

# Test with curl in another terminal:
curl http://localhost:8000/health

# List available models
curl http://localhost:8000/v1/models
```

### 5. Production Deployment

```bash
# Start with Gunicorn (recommended for production)
gunicorn -c src/gunicorn_config.py src.llm_endpoint_server:app
```

## Usage Examples

### OpenAI-Compatible Usage

The gateway works with any OpenAI-compatible client:

```python
import openai

# Configure OpenAI client to use the gateway
client = openai.OpenAI(
    api_key="any-key",  # Not used for local API
    base_url="http://localhost:8000/v1"
)

# Basic chat completion
response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[
        {"role": "user", "content": "Write a professional email subject line"}
    ]
)
print(response.choices[0].message.content)
```

### Tool Calling with Built-in Functions

```python
import openai

client = openai.OpenAI(base_url="http://localhost:8000/v1")

# Use built-in calculator function
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

# The response will include the calculation result
print(response.choices[0].message.content)
```

### CLI Usage

```bash
# List available models
python src/cli.py models

# Generate text
python src/cli.py generate "Explain quantum computing" --model claude-3-haiku

# Interactive chat mode
python src/cli.py chat
```

## Available Models

The gateway supports multiple models through Salesforce's Einstein Trust Layer:

### Claude Models (Anthropic)
- `claude-3-haiku` - Fastest model, ideal for simple tasks and high-volume usage
- `claude-3-sonnet` - Balanced performance, good for complex tasks
- `claude-3-opus` - Most capable model, best for complex reasoning and analysis
- `claude-4-sonnet` - Latest generation with enhanced capabilities

### OpenAI Models 
- `gpt-4` - Versatile model for complex tasks
- `gpt-3.5-turbo` - Faster model for simpler tasks

### Google Models
- `gemini-pro` - General purpose model
- `gemini-pro-vision` - Multimodal model with image support

*Note: Available models depend on your Salesforce org configuration and Einstein licensing. Use `GET /v1/models` to see your available models.*

## OpenAI-Compatible Endpoints

The server provides OpenAI-compatible endpoints on `http://localhost:8000`:

- `GET /health` - Health check endpoint
- `GET /v1/models` - List available models in OpenAI format
- `POST /v1/chat/completions` - Chat completion with tool calling support
- `POST /v1/completions` - Text completion (legacy compatibility)
- `GET /` - Service information and status

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python tests/test_tool_calling.py        # Tool calling functionality
python tests/test_streaming_integration.py  # Streaming responses
python tests/test_auth_flow.py           # Authentication flow
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Tool Calling Documentation](docs/TOOL_CALLING_DOCUMENTATION.md)** - Complete tool calling implementation guide
- **[Timeout Fix Report](docs/TIMEOUT_FIX_REPORT.md)** - Timeout management fixes and configuration
- **[OpenAI Compatibility Fixes](docs/OPENAI_COMPATIBILITY_FIXES.md)** - OpenAI API compatibility improvements
- **[Architecture Analysis](docs/ARCHITECTURE_ANALYSIS.md)** - Comprehensive architectural overview

## Integration Examples

### Open WebUI Integration

```bash
# Configure Open WebUI to use the gateway
OpenAI API Base URL: http://localhost:8000/v1
API Key: any-key (not validated)
```

### n8n Integration

```json
// HTTP Request node in n8n
{
    "method": "POST",
    "url": "http://localhost:8000/v1/chat/completions",
    "headers": {
        "Content-Type": "application/json"
    },
    "body": {
        "model": "claude-3-haiku",
        "messages": [
            {"role": "user", "content": "Process this data: {{$json.input}}"}
        ]
    }
}
```

## Security Best Practices

- 🔒 **Never commit private keys or credentials** to version control
- 🔒 **Use environment variables** for all sensitive configuration
- 🔒 **Rotate certificates regularly** (every 90 days recommended)
- 🔒 **Restrict file permissions** on private key files (`chmod 600`)
- 🔒 **Monitor token usage** and cache access patterns
- 🔒 **Enable CORS** only for trusted domains in web applications
- 🔒 **Implement rate limiting** for public-facing deployments

## Troubleshooting

### Authentication Issues

**Problem**: "Failed to obtain access token"
**Solution**: 
1. Verify all required environment variables are set correctly
2. Check that private key file exists and has proper permissions (`chmod 600 server.key`)
3. Confirm your Connected App is active and properly configured in Salesforce
4. Ensure Connected App has OAuth scopes: `api`, `einstein_gpt_api`, `sfap_api`

### Timeout Issues

**Problem**: Requests timeout after several minutes
**Solution**:
1. Check timeout configuration in `src/gunicorn_config.py`
2. Use faster models for large prompts (`claude-3-haiku`)
3. Review prompt size and consider splitting very large requests (>30k characters)
4. Enable debug logging: `export SF_RESPONSE_DEBUG=true`

### Tool Calling Issues

**Problem**: Tool calls not executed or return errors
**Solution**:
1. Check tool definitions follow OpenAI specification format
2. Verify function names are valid (letters, numbers, underscores, hyphens)
3. Ensure required parameters are properly defined
4. Review execution logs: `export SF_RESPONSE_DEBUG=true`

## Performance Considerations

- **Typical Latency**: Models API calls typically take 2-5 seconds
- **Rate Limits**: Respect Salesforce API limits (varies by org and licensing)
- **Concurrent Requests**: Thread-safe design supports multiple concurrent requests
- **Connection Pooling**: HTTP connections are efficiently reused
- **Dynamic Timeouts**: Automatically calculated based on prompt size and model
- **Memory Usage**: Thread-local design prevents memory bloat

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:

1. Check the documentation in the `docs/` directory
2. Review existing issues on GitHub
3. Create a new issue with detailed information
4. Test with simple curl commands first to isolate problems

## Acknowledgments

- Built for integration with Salesforce Einstein Trust Layer
- OpenAI API compatibility ensures broad ecosystem support
- Designed for enterprise production deployments
