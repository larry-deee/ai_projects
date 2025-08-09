#!/usr/bin/env python3
"""
Model Management Tests for Anthropic Compatibility Layer
=======================================================

Tests for the model mapping and verification components ensuring:
- Proper configuration loading from anthropic_models.map.json
- Model verification with backend integration
- Thread-safe caching behavior with TTL
- Proper ID conversion between Anthropic and Salesforce
- Fallback configuration for missing files
"""

import os
import json
import time
import pytest
import asyncio
from typing import Dict, Any, List
import tempfile

@pytest.mark.asyncio
async def test_load_anthropic_model_config():
    """Test loading Anthropic model configuration."""
    from src.compat_async.model_map import load_anthropic_model_config
    
    # Load config
    config = await load_anthropic_model_config()
    
    # Verify config structure
    assert isinstance(config, list)
    assert len(config) > 0
    
    # Verify config entries
    for entry in config:
        assert "anthropic_id" in entry
        assert "sf_model" in entry
        assert "max_tokens" in entry
        assert "supports_streaming" in entry
        assert "display_name" in entry

@pytest.mark.asyncio
async def test_load_anthropic_model_config_fallback():
    """Test fallback behavior when config file is not found."""
    from src.compat_async.model_map import load_anthropic_model_config, _get_default_model_config
    
    # Store original config paths to restore later
    original_config_paths = list(__import__('src.compat_async.model_map').compat_async.model_map.config_paths)
    
    try:
        # Replace config paths with nonexistent paths to trigger fallback
        __import__('src.compat_async.model_map').compat_async.model_map.config_paths = [
            '/nonexistent/path/1',
            '/nonexistent/path/2'
        ]
        
        # Load config (should use fallback)
        config = await load_anthropic_model_config()
        
        # Verify it matches default config
        default_config = _get_default_model_config()
        assert len(config) == len(default_config)
        
        for i, entry in enumerate(config):
            assert entry["anthropic_id"] == default_config[i]["anthropic_id"]
            assert entry["sf_model"] == default_config[i]["sf_model"]
    finally:
        # Restore original config paths
        __import__('src.compat_async.model_map').compat_async.model_map.config_paths = original_config_paths

@pytest.mark.asyncio
async def test_verify_model_async(mock_model_capabilities):
    """Test async model verification."""
    from src.compat_async.model_map import verify_model_async, clear_model_cache
    
    # Clear cache before testing
    await clear_model_cache()
    
    # Verify a valid model
    result = await verify_model_async("claude-3-5-sonnet-latest")
    assert result is True
    
    # Verify an invalid model
    result = await verify_model_async("nonexistent-model")
    assert result is False

@pytest.mark.asyncio
async def test_model_verification_caching(mock_model_capabilities):
    """Test caching behavior of model verification."""
    from src.compat_async.model_map import verify_model_async, clear_model_cache, _model_verification_cache
    
    # Clear cache before testing
    await clear_model_cache()
    
    # First verification should not be cached
    assert "claude-3-5-sonnet-latest" not in _model_verification_cache
    
    # Perform verification
    result1 = await verify_model_async("claude-3-5-sonnet-latest")
    assert result1 is True
    
    # Now it should be cached
    assert "claude-3-5-sonnet-latest" in _model_verification_cache
    
    # Mock the load_anthropic_model_config function to verify it's not called again
    original_load_config = __import__('src.compat_async.model_map').compat_async.model_map.load_anthropic_model_config
    
    mock_called = False
    
    async def mock_load_config():
        nonlocal mock_called
        mock_called = True
        return await original_load_config()
    
    try:
        # Replace with mock
        __import__('src.compat_async.model_map').compat_async.model_map.load_anthropic_model_config = mock_load_config
        
        # Second verification should use cache
        result2 = await verify_model_async("claude-3-5-sonnet-latest")
        assert result2 is True
        
        # The mock should not have been called
        assert not mock_called
    finally:
        # Restore original function
        __import__('src.compat_async.model_map').compat_async.model_map.load_anthropic_model_config = original_load_config

@pytest.mark.asyncio
async def test_get_verified_anthropic_models(mock_model_capabilities):
    """Test getting verified Anthropic models."""
    from src.compat_async.model_map import get_verified_anthropic_models, clear_model_cache
    
    # Clear cache before testing
    await clear_model_cache()
    
    # Get verified models
    models = await get_verified_anthropic_models()
    
    # Verify structure
    assert isinstance(models, list)
    assert len(models) > 0
    
    # Verify model format
    for model in models:
        assert "id" in model
        assert "type" in model
        assert model["type"] == "model"
        assert "display_name" in model
        assert "created_at" in model
        assert "capabilities" in model
        assert isinstance(model["capabilities"], list)

@pytest.mark.asyncio
async def test_get_verified_anthropic_models_caching(mock_model_capabilities):
    """Test caching behavior of get_verified_anthropic_models."""
    from src.compat_async.model_map import get_verified_anthropic_models, clear_model_cache
    from src.compat_async.model_map import _verified_models_cache, _cache_timestamp
    
    # Clear cache before testing
    await clear_model_cache()
    
    # First call should populate cache
    models1 = await get_verified_anthropic_models()
    assert _verified_models_cache is not None
    assert _cache_timestamp > 0
    
    # Record cache state
    cache_timestamp = _cache_timestamp
    
    # Mock the verification function to verify it's not called again
    original_verify = __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async
    
    verification_count = 0
    
    async def mock_verify(model_id):
        nonlocal verification_count
        verification_count += 1
        return True
    
    try:
        # Replace with mock
        __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = mock_verify
        
        # Second call should use cache
        models2 = await get_verified_anthropic_models()
        
        # The mock should not have been called
        assert verification_count == 0
        
        # Cache timestamp should not have changed
        assert _cache_timestamp == cache_timestamp
    finally:
        # Restore original function
        __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = original_verify

@pytest.mark.asyncio
async def test_cache_ttl_expiration(mock_model_capabilities):
    """Test TTL-based cache expiration."""
    from src.compat_async.model_map import (
        get_verified_anthropic_models, clear_model_cache,
        _verified_models_cache, _cache_timestamp, _cache_ttl
    )
    
    # Clear cache before testing
    await clear_model_cache()
    
    # Use a short cache TTL for testing
    original_ttl = _cache_ttl
    __import__('src.compat_async.model_map').compat_async.model_map._cache_ttl = 0.1  # 100ms TTL
    
    try:
        # First call should populate cache
        models1 = await get_verified_anthropic_models()
        
        # Wait for TTL to expire
        await asyncio.sleep(0.2)  # 200ms > 100ms TTL
        
        # Mock the load_anthropic_model_config function to verify it's called again
        original_load_config = __import__('src.compat_async.model_map').compat_async.model_map.load_anthropic_model_config
        
        config_loaded = False
        
        async def mock_load_config():
            nonlocal config_loaded
            config_loaded = True
            return await original_load_config()
        
        try:
            # Replace with mock
            __import__('src.compat_async.model_map').compat_async.model_map.load_anthropic_model_config = mock_load_config
            
            # Call again after TTL expiration
            models2 = await get_verified_anthropic_models()
            
            # The mock should have been called
            assert config_loaded is True
        finally:
            # Restore original function
            __import__('src.compat_async.model_map').compat_async.model_map.load_anthropic_model_config = original_load_config
    finally:
        # Restore original TTL
        __import__('src.compat_async.model_map').compat_async.model_map._cache_ttl = original_ttl

@pytest.mark.asyncio
async def test_get_sf_model_for_anthropic():
    """Test mapping from Anthropic model ID to Salesforce model ID."""
    from src.compat_async.model_map import get_sf_model_for_anthropic
    
    # Test valid model mapping
    sf_model = await get_sf_model_for_anthropic("claude-3-5-sonnet-latest")
    assert sf_model is not None
    assert "sfdc_ai__" in sf_model
    
    # Test invalid model mapping
    sf_model = await get_sf_model_for_anthropic("nonexistent-model")
    assert sf_model is None

@pytest.mark.asyncio
async def test_clear_model_cache():
    """Test clearing the model verification cache."""
    from src.compat_async.model_map import (
        verify_model_async, get_verified_anthropic_models, clear_model_cache,
        _verified_models_cache, _cache_timestamp, _model_verification_cache
    )
    
    # Populate cache
    await verify_model_async("claude-3-5-sonnet-latest")
    await get_verified_anthropic_models()
    
    # Verify cache is populated
    assert _verified_models_cache is not None
    assert _cache_timestamp > 0
    assert len(_model_verification_cache) > 0
    
    # Clear cache
    await clear_model_cache()
    
    # Verify cache is cleared
    assert _verified_models_cache is None
    assert _cache_timestamp == 0
    assert len(_model_verification_cache) == 0

@pytest.mark.asyncio
async def test_custom_model_config():
    """Test loading custom model configuration from file."""
    from src.compat_async.model_map import load_anthropic_model_config, clear_model_cache
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        # Write custom config
        custom_config = [
            {
                "anthropic_id": "custom-model-1",
                "sf_model": "sfdc_ai__CustomModel1",
                "max_tokens": 8192,
                "supports_streaming": True,
                "display_name": "Custom Test Model"
            }
        ]
        json.dump(custom_config, tmp_file)
        tmp_path = tmp_file.name
    
    try:
        # Store original config paths
        original_config_paths = list(__import__('src.compat_async.model_map').compat_async.model_map.config_paths)
        
        # Replace with our temp file
        __import__('src.compat_async.model_map').compat_async.model_map.config_paths = [tmp_path]
        
        # Clear cache
        await clear_model_cache()
        
        # Load config
        config = await load_anthropic_model_config()
        
        # Verify custom config is loaded
        assert len(config) == 1
        assert config[0]["anthropic_id"] == "custom-model-1"
        assert config[0]["sf_model"] == "sfdc_ai__CustomModel1"
    finally:
        # Restore original config paths
        __import__('src.compat_async.model_map').compat_async.model_map.config_paths = original_config_paths
        
        # Remove temporary file
        os.unlink(tmp_path)

@pytest.mark.asyncio
async def test_concurrent_model_verification(mock_model_capabilities):
    """Test concurrent model verification with proper locking."""
    from src.compat_async.model_map import verify_model_async, clear_model_cache
    
    # Clear cache before testing
    await clear_model_cache()
    
    # Create a list of models to verify concurrently
    models = ["claude-3-5-sonnet-latest", "claude-3-haiku-20240307", "claude-3-opus-20240229"]
    
    # Create and gather multiple verification tasks
    tasks = [verify_model_async(model) for model in models]
    results = await asyncio.gather(*tasks)
    
    # All results should be True
    assert all(results)