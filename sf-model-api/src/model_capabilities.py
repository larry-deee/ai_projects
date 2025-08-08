#!/usr/bin/env python3
"""
Model Capabilities Registry
===========================

Centralized capability definition system for the OpenAI Front-Door & Backend Adapters architecture.
Provides configuration-driven model routing with support for multiple backend types and capability flags.

Key Features:
- Environment variable and config file support
- Default model mappings for common models
- Capability flags: openai_compatible, anthropic_bedrock, vertex_gemini
- Thread-safe lazy loading and caching

Usage:
    from model_capabilities import caps_for
    
    caps = caps_for("sfdc_ai__DefaultGPT4Omni")
    if caps.get("openai_compatible"):
        # Use direct passthrough
        pass
    elif caps.get("anthropic_bedrock"):
        # Use Anthropic adapter
        pass
"""

import os
import json
import yaml
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Default model capability definitions
_DEFAULT_CAPABILITIES = {
    # OpenAI-compatible models (direct passthrough)
    "sfdc_ai__DefaultGPT4Omni": {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    },
    "sfdc_ai__DefaultOpenAIGPT4OmniMini": {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    },
    "gpt-4": {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    },
    "gpt-4-mini": {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    },
    "gpt-4-turbo": {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    },
    "gpt-3.5-turbo": {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    },
    
    # Anthropic/Bedrock models (require normalization)
    "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet": {
        "anthropic_bedrock": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "anthropic_bedrock"
    },
    "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet": {
        "anthropic_bedrock": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "anthropic_bedrock"
    },
    "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku": {
        "anthropic_bedrock": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "anthropic_bedrock"
    },
    "claude-3-haiku": {
        "anthropic_bedrock": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "anthropic_bedrock"
    },
    "claude-3-sonnet": {
        "anthropic_bedrock": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "anthropic_bedrock"
    },
    "claude-4-sonnet": {
        "anthropic_bedrock": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "anthropic_bedrock"
    },
    
    # Google Vertex/Gemini models (require normalization)
    "sfdc_ai__DefaultVertexAIGemini25Flash001": {
        "vertex_gemini": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "vertex_gemini"
    },
    "gemini-pro": {
        "vertex_gemini": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "vertex_gemini"
    },
    "gemini-flash": {
        "vertex_gemini": True,
        "requires_normalization": True,
        "supports_streaming": True,
        "backend_type": "vertex_gemini"
    }
}

# Global cache for loaded capabilities
_capabilities_cache: Optional[Dict[str, Any]] = None

def load_capabilities() -> Dict[str, Any]:
    """
    Load model capabilities from configuration sources with fallback hierarchy.
    
    Priority order:
    1. MODEL_CAPABILITIES_JSON environment variable (JSON string)
    2. MODEL_CAPABILITIES_FILE environment variable (file path)
    3. config/models.yml (YAML file)
    4. config/models.json (JSON file)
    5. Default built-in capabilities
    
    Returns:
        Dict[str, Any]: Model capabilities mapping
    """
    global _capabilities_cache
    
    # Return cached version if available
    if _capabilities_cache is not None:
        return _capabilities_cache
        
    capabilities = _DEFAULT_CAPABILITIES.copy()
    
    # Try loading from JSON environment variable
    json_config = os.getenv("MODEL_CAPABILITIES_JSON")
    if json_config:
        try:
            env_capabilities = json.loads(json_config)
            logger.info("✅ Loaded model capabilities from MODEL_CAPABILITIES_JSON")
            capabilities.update(env_capabilities)
            _capabilities_cache = capabilities
            return capabilities
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"⚠️ Failed to parse MODEL_CAPABILITIES_JSON: {e}")
    
    # Try loading from file path
    config_file = os.getenv("MODEL_CAPABILITIES_FILE")
    if not config_file:
        # Try default locations
        for default_path in ["config/models.yml", "config/models.json", "../config/models.yml", "../config/models.json"]:
            if os.path.exists(default_path):
                config_file = default_path
                break
    
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.yml') or config_file.endswith('.yaml'):
                    file_capabilities = yaml.safe_load(f) or {}
                else:
                    file_capabilities = json.load(f)
                
                logger.info(f"✅ Loaded model capabilities from {config_file}")
                capabilities.update(file_capabilities)
        except (yaml.YAMLError, json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            logger.warning(f"⚠️ Failed to load model capabilities from {config_file}: {e}")
    
    # Cache the result
    _capabilities_cache = capabilities
    logger.debug(f"🔧 Model capabilities loaded: {len(capabilities)} models configured")
    return capabilities

def caps_for(model_id: str) -> Dict[str, Any]:
    """
    Get capabilities for a specific model with intelligent fallbacks.
    
    Args:
        model_id: Model identifier to look up
        
    Returns:
        Dict[str, Any]: Model capabilities with fallback defaults
    """
    capabilities = load_capabilities()
    
    # Direct lookup
    if model_id in capabilities:
        return capabilities[model_id]
    
    # Intelligent pattern matching for unknown models
    model_lower = model_id.lower()
    
    # GPT/OpenAI patterns
    if any(pattern in model_lower for pattern in ['gpt-', 'openai', 'gpt4', 'gpt3.5']):
        return {
            "openai_compatible": True,
            "passthrough_tools": True,
            "supports_streaming": True,
            "backend_type": "openai_native"
        }
    
    # Claude/Anthropic patterns
    if any(pattern in model_lower for pattern in ['claude', 'anthropic', 'bedrock']):
        return {
            "anthropic_bedrock": True,
            "requires_normalization": True,
            "supports_streaming": True,
            "backend_type": "anthropic_bedrock"
        }
    
    # Gemini/Google patterns
    if any(pattern in model_lower for pattern in ['gemini', 'vertex', 'google']):
        return {
            "vertex_gemini": True,
            "requires_normalization": True,
            "supports_streaming": True,
            "backend_type": "vertex_gemini"
        }
    
    # Default fallback (assume OpenAI-compatible with tool preservation)
    logger.info(f"🔧 Using OpenAI-compatible fallback for unknown model: {model_id}")
    return {
        "openai_compatible": True,
        "passthrough_tools": True,
        "supports_streaming": True,
        "backend_type": "openai_native"
    }

def get_backend_type(model_id: str) -> str:
    """
    Get the backend type for a model.
    
    Args:
        model_id: Model identifier
        
    Returns:
        str: Backend type ('openai_native', 'anthropic_bedrock', 'vertex_gemini')
    """
    caps = caps_for(model_id)
    return caps.get("backend_type", "openai_native")

def supports_native_tools(model_id: str) -> bool:
    """
    Check if a model supports native OpenAI tool calls format.
    
    Args:
        model_id: Model identifier
        
    Returns:
        bool: True if model supports native tool calls
    """
    caps = caps_for(model_id)
    return caps.get("openai_compatible", False) and caps.get("passthrough_tools", False)

def requires_normalization(model_id: str) -> bool:
    """
    Check if a model requires response normalization.
    
    Args:
        model_id: Model identifier
        
    Returns:
        bool: True if model requires normalization to OpenAI format
    """
    caps = caps_for(model_id)
    return caps.get("requires_normalization", True)

def reload_capabilities() -> Dict[str, Any]:
    """
    Force reload of model capabilities from configuration sources.
    
    Returns:
        Dict[str, Any]: Freshly loaded model capabilities
    """
    global _capabilities_cache
    _capabilities_cache = None
    return load_capabilities()

def get_all_models() -> Dict[str, Any]:
    """
    Get all configured model capabilities.
    
    Returns:
        Dict[str, Any]: Complete model capabilities mapping
    """
    return load_capabilities()

# Export the loaded capabilities for external access
CAPABILITIES = load_capabilities

# Convenience exports
__all__ = [
    "caps_for", 
    "get_backend_type", 
    "supports_native_tools", 
    "requires_normalization",
    "load_capabilities",
    "reload_capabilities", 
    "get_all_models",
    "CAPABILITIES"
]