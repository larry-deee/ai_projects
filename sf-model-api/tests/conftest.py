#!/usr/bin/env python3
"""
Pytest Configuration and Fixtures for Anthropic Compatibility Test Suite
=======================================================================

Provides shared fixtures for all test modules including:
- Mock async client for Salesforce backend
- Mock headers for Anthropic API compatibility
- Mock request data for various test scenarios
- Mock response data from Salesforce backend
- Utilities for comparing Anthropic API responses
"""

import os
import sys
import json
import pytest
import asyncio
from typing import Dict, Any, List, Optional
from quart import Quart
from werkzeug.datastructures import Headers

# Add src directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the modules we need to test
from src.routers.anthropic_compat_async import create_anthropic_compat_router, AnthropicCompatAsyncRouter
from src.compat_async.anthropic_mapper import (
    require_anthropic_headers, 
    map_messages_to_sf_async,
    map_sf_to_anthropic,
    sse_iter_from_sf_generation
)
from src.compat_async.model_map import (
    load_anthropic_model_config,
    verify_model_async,
    get_verified_anthropic_models,
    get_sf_model_for_anthropic,
    clear_model_cache
)
from src.compat_async.tokenizers import (
    count_tokens_async,
    validate_token_limits
)

# Create a directory for test data if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'test_data'), exist_ok=True)

# ===== Mock Data Fixtures =====

@pytest.fixture
def mock_anthropic_headers():
    """Return mock Anthropic API headers."""
    return Headers({
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
    })

@pytest.fixture
def mock_invalid_anthropic_headers():
    """Return invalid Anthropic API headers (missing version)."""
    return Headers({
        'content-type': 'application/json'
    })

@pytest.fixture
def mock_anthropic_messages():
    """Return mock Anthropic messages with content blocks."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello, how are you today?"}
            ]
        }
    ]

@pytest.fixture
def mock_anthropic_messages_complex():
    """Return mock Anthropic messages with multiple messages and content blocks."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello, how are you today?"}
            ]
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I'm doing well! How can I help you?"}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Tell me about the weather."}
            ]
        }
    ]

@pytest.fixture
def mock_anthropic_tools():
    """Return mock Anthropic tool definitions."""
    return [
        {
            "name": "get_weather",
            "description": "Get the current weather in a location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to get weather for"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit"
                    }
                },
                "required": ["location"]
            }
        }
    ]

@pytest.fixture
def mock_sf_response():
    """Return mock Salesforce backend response."""
    return {
        "generations": [{"text": "Hello! I'm an AI assistant. How can I help you today?"}],
        "usage": {"inputTokenCount": 10, "outputTokenCount": 12}
    }

@pytest.fixture
def mock_sf_response_with_tools():
    """Return mock Salesforce backend response with tool calls."""
    return {
        "generations": [
            {
                "text": "",
                "tool_calls": [
                    {
                        "name": "get_weather",
                        "arguments": json.dumps({
                            "location": "San Francisco",
                            "unit": "celsius"
                        })
                    }
                ]
            }
        ],
        "usage": {"inputTokenCount": 15, "outputTokenCount": 20}
    }

# ===== Mock Clients and Services =====

class MockAsyncSalesforceModelsClient:
    """Mock implementation of AsyncSalesforceModelsClient for testing."""
    
    async def _async_chat_completion(self, **kwargs):
        """Mock chat completion API call."""
        await asyncio.sleep(0.01)  # Simulate network delay
        
        if 'tools' in kwargs:
            return {
                "generations": [
                    {
                        "text": "",
                        "tool_calls": [
                            {
                                "name": "get_weather",
                                "arguments": json.dumps({
                                    "location": "San Francisco",
                                    "unit": "celsius"
                                })
                            }
                        ]
                    }
                ],
                "usage": {"inputTokenCount": 15, "outputTokenCount": 20}
            }
        else:
            return {
                "generations": [{"text": "Hello! I'm an AI assistant. How can I help you today?"}],
                "usage": {"inputTokenCount": 10, "outputTokenCount": 12}
            }

@pytest.fixture
def mock_async_client():
    """Return mock AsyncSalesforceModelsClient."""
    return MockAsyncSalesforceModelsClient()

@pytest.fixture
async def mock_get_async_client(monkeypatch, mock_async_client):
    """Patch get_async_client to return mock client."""
    async def mock_get_client():
        return mock_async_client
    
    monkeypatch.setattr("src.routers.anthropic_compat_async.get_async_client", mock_get_client)
    return mock_get_client

@pytest.fixture
async def mock_model_capabilities(monkeypatch):
    """Mock model_capabilities functions."""
    def mock_caps_for(model_id):
        return {"supports_streaming": True, "max_tokens": 4096}
    
    def mock_get_backend_type(model_id):
        return "bedrock"
    
    monkeypatch.setattr("src.compat_async.model_map.caps_for", mock_caps_for)
    monkeypatch.setattr("src.compat_async.model_map.get_backend_type", mock_get_backend_type)

# ===== Test App and Client =====

@pytest.fixture
async def test_app(mock_get_async_client, mock_model_capabilities):
    """Create test Quart application with Anthropic router."""
    app = Quart(__name__)
    
    # Register the Anthropic router blueprint
    anthropic_bp = create_anthropic_compat_router('/v1')
    app.register_blueprint(anthropic_bp, url_prefix='/anthropic')
    
    return app

@pytest.fixture
async def test_client(test_app):
    """Return a test client for the test application."""
    return test_app.test_client()

# ===== Test Utilities =====

def create_anthropic_model_config_file():
    """Create a temporary Anthropic model config file for testing."""
    config_dir = os.path.join(os.path.dirname(__file__), '../config')
    os.makedirs(config_dir, exist_ok=True)
    
    config_file = os.path.join(config_dir, 'anthropic_models.map.json')
    
    # Only create if it doesn't exist
    if not os.path.exists(config_file):
        config_data = [
            {
                "anthropic_id": "claude-3-5-sonnet-latest",
                "sf_model": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
                "max_tokens": 4096,
                "supports_streaming": True,
                "display_name": "Claude 3.5 Sonnet"
            },
            {
                "anthropic_id": "claude-3-haiku-20240307",
                "sf_model": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku", 
                "max_tokens": 4096,
                "supports_streaming": True,
                "display_name": "Claude 3 Haiku"
            }
        ]
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

@pytest.fixture(scope="session", autouse=True)
def setup_model_config():
    """Setup model config file before tests run."""
    create_anthropic_model_config_file()
    yield
    # No cleanup needed, we can leave the config file in place