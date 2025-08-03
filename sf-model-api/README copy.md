# Salesforce Models API Gateway

OpenAI-compatible API gateway for Salesforce Einstein Trust Layer Models API. Provides access to Claude, GPT-4, and Gemini models through standard OpenAI endpoints.

## Quick Start

### Prerequisites
- Salesforce Connected App with OAuth scopes
- Einstein/Models API enabled in your Salesforce org

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
Create `config.json` from the example:
```bash
cp config/config.json.example config.json
# Edit with your Salesforce credentials
```

### Usage

#### Option 1: Using the startup script (Recommended)
```bash
# Development mode
./start_llm_service.sh

# Production mode
ENVIRONMENT=production ./start_llm_service.sh

# Other commands
./start_llm_service.sh stop     # Stop production service
./start_llm_service.sh status   # Check service status
./start_llm_service.sh restart  # Restart service
```

#### Option 2: Direct Python execution
```bash
# Start server directly
python src/llm_endpoint_server.py

# Test connection
curl http://localhost:8000/health

# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "claude-3-haiku", "messages": [{"role": "user", "content": "Hello"}]}'
```

## OpenAI Client Integration
```python
import openai

client = openai.OpenAI(
    api_key="any-key",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="claude-3-haiku",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Features
- OpenAI API compatibility
- Tool calling support
- Streaming responses
- Multiple model support (Claude, GPT-4, Gemini)
- OAuth 2.0 authentication

## Files
- `start_llm_service.sh` - Production-ready startup script with environment management
- `gunicorn_config.py` - Gunicorn server configuration for production deployment
- `src/llm_endpoint_server.py` - Main Flask server
- `src/salesforce_models_client.py` - Salesforce API client
- `src/tool_handler.py` - Tool calling logic
- `src/cli.py` - Command line interface
- `config/config.json.example` - Configuration template