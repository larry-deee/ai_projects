#!/usr/bin/env python3
"""
Model Mapping and Verification System
=====================================

Async model mapping and verification utilities for Anthropic compatibility layer.
Provides configuration-driven model verification with integration to existing
model_capabilities system and AsyncSalesforceModelsClient verification.

Key Features:
- Configuration loading from anthropic_models.map.json
- Async model verification using Salesforce backend
- Caching of verified model IDs for performance
- Integration with existing model_capabilities system

Usage:
    from compat_async.model_map import get_verified_anthropic_models, verify_model_async
    
    models = await get_verified_anthropic_models()
    is_available = await verify_model_async("claude-3-5-sonnet-latest")
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model_capabilities import caps_for, get_backend_type

logger = logging.getLogger(__name__)

# Cache for verified models (thread-safe with asyncio.Lock)
_verified_models_cache: Optional[List[Dict[str, Any]]] = None
_model_verification_cache: Dict[str, bool] = {}
_cache_lock = asyncio.Lock()
_cache_timestamp = 0
_cache_ttl = 300  # 5 minutes cache TTL

async def load_anthropic_model_config() -> List[Dict[str, Any]]:
    """
    Load Anthropic model configuration from anthropic_models.map.json.
    
    Loads the configuration file that maps Anthropic model IDs to Salesforce
    model IDs with capability metadata.
    
    Returns:
        List[Dict]: List of model configuration entries
        
    Raises:
        FileNotFoundError: If configuration file is not found
        json.JSONDecodeError: If configuration file is invalid JSON
    """
    # Check for config file in multiple locations
    config_paths = [
        "config/anthropic_models.map.json",
        "../config/anthropic_models.map.json",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                    "config/anthropic_models.map.json")
    ]
    
    config_path = None
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            break
    
    if not config_path:
        # Fallback: create default configuration in memory
        logger.warning("⚠️ anthropic_models.map.json not found, using default configuration")
        return _get_default_model_config()
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"✅ Loaded Anthropic model config from: {config_path}")
        return config
        
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"❌ Failed to load Anthropic model config: {e}")
        return _get_default_model_config()

def _get_default_model_config() -> List[Dict[str, Any]]:
    """
    Get default Anthropic model configuration.
    
    Provides fallback configuration if anthropic_models.map.json is not available.
    
    Returns:
        List[Dict]: Default model configuration
    """
    return [
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
        },
        {
            "anthropic_id": "claude-3-sonnet-20240229",
            "sf_model": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
            "max_tokens": 4096,
            "supports_streaming": True,
            "display_name": "Claude 3 Sonnet"
        },
        {
            "anthropic_id": "claude-3-opus-20240229", 
            "sf_model": "sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet",
            "max_tokens": 4096,
            "supports_streaming": True,
            "display_name": "Claude 3 Opus"
        }
    ]

async def verify_model_async(anthropic_model_id: str) -> bool:
    """
    Verify if an Anthropic model ID is available through Salesforce backend.
    
    Uses caching to avoid repeated verification calls and integrates with
    the existing model_capabilities system for backend verification.
    
    Args:
        anthropic_model_id: Anthropic model ID to verify
        
    Returns:
        bool: True if model is available, False otherwise
    """
    async with _cache_lock:
        # Check cache first
        if anthropic_model_id in _model_verification_cache:
            return _model_verification_cache[anthropic_model_id]
    
    try:
        # Load model configuration
        model_config = await load_anthropic_model_config()
        
        # Find model in configuration
        model_entry = None
        for entry in model_config:
            if entry.get("anthropic_id") == anthropic_model_id:
                model_entry = entry
                break
        
        if not model_entry:
            logger.debug(f"❌ Anthropic model not found in config: {anthropic_model_id}")
            async with _cache_lock:
                _model_verification_cache[anthropic_model_id] = False
            return False
        
        # Check if Salesforce model is available
        sf_model = model_entry.get("sf_model")
        if not sf_model:
            logger.debug(f"❌ No Salesforce model mapped for: {anthropic_model_id}")
            async with _cache_lock:
                _model_verification_cache[anthropic_model_id] = False
            return False
        
        # Use model_capabilities to verify availability
        try:
            capabilities = caps_for(sf_model)
            backend_type = get_backend_type(sf_model)
            
            # Model is available if it has capabilities
            is_available = bool(capabilities and backend_type)
            
            if is_available:
                logger.debug(f"✅ Verified Anthropic model: {anthropic_model_id} → {sf_model}")
            else:
                logger.debug(f"❌ Salesforce model not available: {sf_model}")
            
        except Exception as e:
            logger.debug(f"❌ Model verification failed for {sf_model}: {e}")
            is_available = False
        
        # Cache result
        async with _cache_lock:
            _model_verification_cache[anthropic_model_id] = is_available
        
        return is_available
        
    except Exception as e:
        logger.error(f"❌ Error verifying model {anthropic_model_id}: {e}")
        async with _cache_lock:
            _model_verification_cache[anthropic_model_id] = False
        return False

async def get_verified_anthropic_models() -> List[Dict[str, Any]]:
    """
    Get list of verified Anthropic models available through Salesforce backend.
    
    Returns only models that have been verified as available through the
    Salesforce backend integration. Uses caching for performance.
    
    Returns:
        List[Dict]: List of verified Anthropic models in API format
    """
    global _verified_models_cache, _cache_timestamp
    
    current_time = time.time()
    
    # Check cache validity
    async with _cache_lock:
        if (_verified_models_cache is not None and 
            current_time - _cache_timestamp < _cache_ttl):
            return _verified_models_cache
    
    try:
        # Load model configuration
        model_config = await load_anthropic_model_config()
        
        # Verify each model asynchronously
        verified_models = []
        verification_tasks = []
        
        for entry in model_config:
            anthropic_id = entry.get("anthropic_id")
            if anthropic_id:
                verification_tasks.append(verify_model_async(anthropic_id))
        
        # Wait for all verifications to complete
        verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)
        
        # Build verified models list
        for entry, is_verified in zip(model_config, verification_results):
            # Handle exceptions from verification
            if isinstance(is_verified, Exception):
                logger.error(f"❌ Verification error for {entry.get('anthropic_id')}: {is_verified}")
                continue
                
            if is_verified:
                # Format model in Anthropic API format
                anthropic_model = {
                    "id": entry["anthropic_id"],
                    "type": "model",
                    "display_name": entry.get("display_name", entry["anthropic_id"]),
                    "created_at": "2024-01-01T00:00:00Z",  # Placeholder timestamp
                    "capabilities": ["messages", "streaming"]
                }
                
                # Add token limits if specified
                if "max_tokens" in entry:
                    anthropic_model["max_tokens"] = entry["max_tokens"]
                
                verified_models.append(anthropic_model)
        
        # Update cache
        async with _cache_lock:
            _verified_models_cache = verified_models
            _cache_timestamp = current_time
        
        logger.info(f"✅ Verified {len(verified_models)} Anthropic models")
        return verified_models
        
    except Exception as e:
        logger.error(f"❌ Error getting verified models: {e}")
        # Return empty list on error
        return []

async def get_sf_model_for_anthropic(anthropic_model_id: str) -> Optional[str]:
    """
    Get Salesforce model ID for an Anthropic model ID.
    
    Args:
        anthropic_model_id: Anthropic model ID
        
    Returns:
        Optional[str]: Salesforce model ID if found, None otherwise
    """
    try:
        model_config = await load_anthropic_model_config()
        
        for entry in model_config:
            if entry.get("anthropic_id") == anthropic_model_id:
                return entry.get("sf_model")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting SF model for {anthropic_model_id}: {e}")
        return None

async def clear_model_cache() -> None:
    """
    Clear the model verification cache.
    
    Useful for testing or when model availability changes.
    """
    global _verified_models_cache, _cache_timestamp
    
    async with _cache_lock:
        _verified_models_cache = None
        _cache_timestamp = 0
        _model_verification_cache.clear()
    
    logger.info("🧹 Model cache cleared")