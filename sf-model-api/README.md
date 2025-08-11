# Salesforce Models API Gateway

A production-ready OpenAI-compatible API gateway that provides seamless access to Salesforce's Einstein Trust Layer Models with advanced tool calling capabilities.

## 📖 Quick Overview

### Purpose
This gateway enables organizations to leverage Salesforce AI investments across their entire technology stack with full compatibility for existing LLM applications and workflows.

### Key Features
- 🌐 **Universal API Compatibility**
  - 100% OpenAI API Specification Compliant
  - 100% Anthropic API Specification Compliant
- 🔀 **Intelligent Backend Adapters**
  - Support for Claude, GPT-4, Gemini models
  - Automatic model format normalization
- 🛠️ **Advanced Tool Calling**
  - Full OpenAI function calling
  - Automatic tool-call repair
  - n8n Workflow Compatibility
- 🔒 **Enterprise-Grade Authentication**
  - OAuth 2.0 Client Credentials Flow
  - Token Pre-warming
  - Thread-safe Design

## 📦 Prerequisites

- Python 3.8+
- Salesforce org with Einstein Trust Layer access
- Connected App with proper OAuth scopes
- Private key for JWT authentication

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/models-api.git
cd models-api
pip install -r requirements.txt
```

2. Configure authentication:
```bash
# Create secure config directory
mkdir -p .secure
cp config.json.example .secure/config.json

# Set environment variables
export SALESFORCE_CONSUMER_KEY="your_key"
export SALESFORCE_USERNAME="user@company.com"
export SALESFORCE_PRIVATE_KEY_FILE="/path/to/server.key"
```

3. Start the server:
```bash
# Local Development (Recommended)
uvicorn src.async_endpoint_server:app --host 127.0.0.1 --port 8000

# Production
gunicorn -c gunicorn_config.py llm_endpoint_server:app
```

## 📚 Documentation

Comprehensive documentation is available in multiple formats:

- [Architecture Overview](/docs/ARCHITECTURE.md)
- [API Reference](/docs/API_REFERENCE.md)
- [Configuration Guide](/docs/CONFIGURATION.md)
- [Compatibility Guide](/docs/COMPATIBILITY.md)
- [Testing Procedures](/docs/TESTING.md)

## 🔍 Example Usage

### OpenAI SDK
```python
from openai import OpenAI

client = OpenAI(
    api_key="any-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

### Anthropic SDK
```python
import anthropic

client = anthropic.Anthropic(
    api_key="any-key",
    base_url="http://localhost:8000/anthropic"
)

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    messages=[{"role": "user", "content": "Hello, world!"}],
    max_tokens=1000
)
```

## 🛡️ Security Best Practices

- Never commit sensitive credentials to version control
- Use environment variables for configuration
- Rotate certificates regularly
- Implement rate limiting in production

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

- Check [Troubleshooting](/docs/TROUBLESHOOTING.md)
- Review documentation in the `docs/` directory
- Test with `GET /health` endpoint
- Run `./streaming_regression_tests.sh`

---

**Note**: Ensure your Salesforce org has the necessary Einstein licensing and API access configured.