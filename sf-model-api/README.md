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

2. **Configure authentication** (Choose ONE method):

## 🔧 Configuration Methods & Precedence

**Configuration is loaded in this order (highest priority first):**
1. **Environment Variables** (Highest Priority)
2. **`.env` file** (Medium Priority) 
3. **`.secure/config.json` file** (Lowest Priority)

### **Method 1: Environment Variables (Recommended for Production)**
```bash
# Set directly in your environment
export SALESFORCE_CONSUMER_KEY="your_key"
export SALESFORCE_CONSUMER_SECRET="your_secret"
export SALESFORCE_USERNAME="user@company.com"
export SALESFORCE_INSTANCE_URL="https://your-instance.my.salesforce.com"
```

### **Method 2: .env File (Recommended for Development)**
```bash
# Copy template and customize
cp .env.example .env
# Edit .env with your credentials
# No need to source - automatically loaded by start scripts
```

### **Method 3: JSON Config File (Alternative)**
```bash
# Create secure config directory and file
mkdir -p .secure
cp config.json.example .secure/config.json
# Edit .secure/config.json with your credentials
```

**💡 Pro Tip:** Use `.env` for development and environment variables for production deployment.

3. Start the server:

```bash
# Recommended: High-performance async server (production-ready)
./scripts/start_async_service.sh

# Alternative: Standard server  
./scripts/start_llm_service.sh

# Development mode with specific environment
ENVIRONMENT=development ./scripts/start_async_service.sh

# Production deployment
ENVIRONMENT=production ./scripts/start_async_service.sh

# View comprehensive help and all environment variables
./scripts/start_async_service.sh --help

# Manual start options (if needed)
uvicorn src.async_endpoint_server:app --host 127.0.0.1 --port 8000
```

**Key Environment Variables:**

**🔧 Server Configuration:**
- `HOST`: Server bind address (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)  
- `WORKERS`: Number of gunicorn workers (default: 4)
- `ENVIRONMENT`: 'development' or 'production' (default: development)

**🔐 Authentication (Required):**
- `SALESFORCE_CONSUMER_KEY`: Your Salesforce Connected App key
- `SALESFORCE_CONSUMER_SECRET`: Your Salesforce Connected App secret
- `SALESFORCE_USERNAME`: Your Salesforce username
- `SALESFORCE_INSTANCE_URL`: Your Salesforce instance URL

**⚙️ Compatibility & Features:**
- `N8N_COMPAT_MODE`: Enable n8n/OpenAI.js compatibility (default: 1)
- `OPENAI_NATIVE_TOOL_PASSTHROUGH`: Enable OpenAI native tool passthrough (default: 1)
- `VERBOSE_TOOL_LOGS`: Enable detailed tool calling logs (default: 0)
- `SF_RESPONSE_DEBUG`: Enable detailed response logging (default: false)

**🎯 Performance & Optimization:**
- `N8N_COMPAT_PRESERVE_TOOLS`: Preserve tools for n8n clients (default: 1)
- `NATIVE_ANTHROPIC_ENABLED`: Enable legacy Anthropic router (default: false)
- `OPENAI_FRONTDOOR_ENABLED`: Enable OpenAI front-door architecture (default: 0)

*See `.env.example` for a complete configuration template with all options.*

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