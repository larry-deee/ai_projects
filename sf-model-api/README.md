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
# Development
python llm_endpoint_server.py

# Production
gunicorn -c gunicorn_config.py llm_endpoint_server:app
```

5. **Test the installation:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
```

## 🎯 Key Features

- ✅ **100% OpenAI API Compatible** - Works with OpenWebUI, n8n, LangChain, and standard OpenAI clients
- ✅ **Complete Tool Calling** - Full OpenAI function calling with built-in safe functions and passthrough mode
- ✅ **Enterprise Authentication** - OAuth 2.0 Client Credentials Flow with aggressive token management
- ✅ **Thread-Safe Architecture** - Scalable design with multi-layer token caching
- ✅ **Smart Timeout Management** - Dynamic timeouts based on request characteristics
- ✅ **Streaming Support** - Real-time response streaming with proper OpenAI chunk formatting
- ✅ **Production Ready** - Comprehensive logging, monitoring, and deployment automation
- ✅ **Multi-Model Access** - Support for Claude, GPT-4, and Gemini models through Salesforce

## 📁 Project Structure

```
models-api/
├── src/                          # Core application code
│   ├── llm_endpoint_server.py    # Main Flask application with OpenAI endpoints
│   ├── salesforce_models_client.py # Core Salesforce API client with OAuth 2.0
│   ├── streaming_architecture.py # Advanced streaming response system
│   ├── tool_handler.py          # Tool calling orchestration and execution
│   ├── tool_schemas.py          # Pydantic models for tool validation
│   ├── tool_executor.py         # Sandboxed function execution engine
│   └── cli.py                   # Command-line interface for testing
├── config/                      # Configuration files
│   ├── config.json.example      # Example configuration
│   ├── config.json.template     # Configuration template
│   └── gunicorn_config.py       # Production server configuration
├── tests/                       # Comprehensive test suite
│   ├── test_auth_*.py           # Authentication tests
│   ├── test_streaming_*.py      # Streaming functionality tests
│   ├── test_tool_calling.py     # Tool calling tests
│   ├── test_llm_endpoint.py     # Core endpoint tests
│   └── test_performance_*.py    # Performance and optimization tests
├── examples/                    # Usage examples and integrations
│   ├── integration_examples.py  # Various integration patterns
│   ├── example_enhanced_tool_streaming.py # Advanced streaming examples
│   └── examples.py              # Basic usage examples
├── scripts/                     # Deployment and utility scripts
│   ├── quick_install.sh         # Quick installation script
│   ├── start_llm_service.sh     # Service startup script
│   └── setup_validator.py       # Environment validation
├── docs/                        # Comprehensive documentation
│   ├── ARCHITECTURE_ANALYSIS.md # Architectural overview
│   ├── TOOL_CALLING_DOCUMENTATION.md # Tool calling guide
│   ├── STREAMING_IMPLEMENTATION_GUIDE.md # Streaming setup
│   └── PERFORMANCE_OPTIMIZATION.md # Performance tuning
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
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

The server provides OpenAI-compatible endpoints on `http://localhost:8000`:

- `GET /health` - Health check endpoint
- `GET /v1/models` - List available models in OpenAI format
- `POST /v1/chat/completions` - Chat completion with tool calling support
- `POST /v1/completions` - Text completion (legacy compatibility)

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

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Test specific functionality
python test_llm_endpoint.py
python test_tool_calling.py
python test_streaming_architecture.py

# Performance tests
python test_caching_performance.py
python test_phase1_optimizations.py
```

## 🚀 Deployment

### Development

```bash
python llm_endpoint_server.py
```

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

The gateway supports multiple models through Salesforce's Einstein Trust Layer:

### Claude Models (Anthropic)
- `claude-3-haiku` - Fastest model, ideal for simple tasks
- `claude-3-sonnet` - Balanced performance for complex tasks
- `claude-3-opus` - Most capable model for reasoning
- `claude-4-sonnet` - Latest generation with enhanced capabilities

### OpenAI Models
- `gpt-4` - Versatile model for complex tasks
- `gpt-3.5-turbo` - Faster model for simpler tasks

### Google Models
- `gemini-pro` - General purpose model
- `gemini-pro-vision` - Multimodal model with image support

*Note: Available models depend on your Salesforce org configuration and Einstein licensing.*

## 🛠️ Troubleshooting

### Authentication Issues

**Problem**: "Failed to obtain access token"

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

### Tool Calling Issues

**Problem**: Tool calls not executed properly

**Solution**:
1. Verify tool definitions follow OpenAI specification
2. Check function names are valid (letters, numbers, underscores, hyphens)
3. Ensure required parameters are properly defined

## 🏗️ Integration Examples

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
    "messages": [{"role": "user", "content": "Process this data"}]
  }
}
```

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

- **Model Selection**: Use `claude-3-haiku` for fastest responses
- **Prompt Engineering**: Concise prompts improve response times
- **Token Caching**: Authentication tokens are cached aggressively
- **Connection Pooling**: HTTP connections are efficiently reused
- **Dynamic Timeouts**: Automatically calculated based on request size

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
2. Review the comprehensive documentation in the `docs/` directory
3. Test with `GET /health` endpoint first
4. Enable debug logging for detailed error information

---

**Note**: This project provides a bridge between OpenAI-compatible applications and Salesforce's Einstein Trust Layer. Ensure your Salesforce org has the necessary Einstein licensing and API access configured.
