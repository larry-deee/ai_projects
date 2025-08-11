#!/usr/bin/env python3
"""
Unified Configuration Management System
======================================

Centralized configuration management for the Salesforce Models API Gateway.
Provides a single point of configuration loading with efficient caching,
environment variable overrides, and comprehensive validation.

Key Features:
- Primary configuration source: config.json
- Environment variable overrides for all settings
- Intelligent path resolution across deployment scenarios
- Efficient in-memory caching with configurable TTL
- Model mapping configuration management
- Token optimization and lazy loading
- Comprehensive validation and error handling
- Thread-safe operations for concurrent access

Usage:
    from config_manager import ConfigManager
    
    config = ConfigManager()
    
    # Get Salesforce credentials
    credentials = await config.get_salesforce_config()
    
    # Get model mappings
    models = await config.get_model_mappings()
    
    # Get tool calling settings
    tool_config = await config.get_tool_calling_config()
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import threading
from dataclasses import dataclass, field
from copy import deepcopy

logger = logging.getLogger(__name__)

@dataclass
class ConfigCache:
    """Configuration cache with TTL support."""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    ttl: float = 300.0  # 5 minutes default TTL
    
    def is_expired(self) -> bool:
        """Check if cache has expired."""
        return time.time() - self.timestamp > self.ttl
    
    def refresh_timestamp(self):
        """Update the cache timestamp."""
        self.timestamp = time.time()


class ConfigManager:
    """
    Unified configuration management system.
    
    Provides centralized configuration loading with caching, environment overrides,
    and comprehensive validation. Thread-safe and optimized for performance.
    """
    
    def __init__(self, config_file: Optional[str] = None, cache_ttl: float = 300.0):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to config.json file
            cache_ttl: Cache TTL in seconds (default: 5 minutes)
        """
        self.config_file = config_file
        self.cache_ttl = cache_ttl
        
        # Thread-safe caching
        self._cache_lock = threading.RLock()
        self._async_cache_lock = asyncio.Lock()
        self._main_config_cache = ConfigCache(ttl=cache_ttl)
        self._model_config_cache = ConfigCache(ttl=cache_ttl)
        
        # Configuration paths and environment mappings
        self._config_paths = [
            ".secure/config.json",
            "../.secure/config.json",
            "config.json",
            "../config.json", 
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".secure", "config.json"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
        ]
        
        self._model_config_paths = [
            "config/anthropic_models.map.json",
            "../config/anthropic_models.map.json",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                        "config/anthropic_models.map.json")
        ]
        
        # Environment variable mappings
        self._env_mappings = {
            'consumer_key': 'SALESFORCE_CONSUMER_KEY',
            'consumer_secret': 'SALESFORCE_CONSUMER_SECRET', 
            'username': 'SALESFORCE_USERNAME',
            'instance_url': 'SALESFORCE_INSTANCE_URL',
            'api_version': 'SALESFORCE_API_VERSION',
            'token_file': 'SALESFORCE_MODELS_TOKEN_FILE'
        }
        
        logger.debug("ConfigManager initialized with cache TTL: %.1fs", cache_ttl)
    
    def _resolve_config_path(self, paths: List[str], config_type: str = "main") -> Optional[str]:
        """
        Resolve configuration file path from multiple possible locations.
        
        Args:
            paths: List of possible config file paths
            config_type: Type of config for logging (main, model, etc.)
            
        Returns:
            Resolved path if found, None otherwise
        """
        if self.config_file and config_type == "main":
            # Use explicitly provided config file
            if os.path.exists(self.config_file):
                return os.path.abspath(self.config_file)
            else:
                logger.warning(f"Explicitly provided config file not found: {self.config_file}")
        
        # Search standard locations
        for path in paths:
            if os.path.exists(path):
                resolved_path = os.path.abspath(path)
                logger.debug(f"✅ Found {config_type} config: {resolved_path}")
                return resolved_path
        
        logger.debug(f"❌ No {config_type} config file found in: {paths}")
        return None
    
    def _load_json_config(self, file_path: str) -> Dict[str, Any]:
        """
        Load and parse JSON configuration file.
        
        Args:
            file_path: Path to JSON configuration file
            
        Returns:
            Parsed configuration dictionary
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
            IOError: If file cannot be read
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.debug(f"✅ Loaded config from: {file_path}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {file_path}: {e}")
            raise
        except IOError as e:
            logger.error(f"❌ Cannot read config file {file_path}: {e}")
            raise
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Base configuration dictionary
            
        Returns:
            Configuration with environment overrides applied
        """
        config_with_overrides = deepcopy(config)
        
        # Apply direct environment mappings
        for config_key, env_var in self._env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                config_with_overrides[config_key] = env_value
                logger.debug(f"✅ Applied env override: {config_key} = {env_var}")
        
        # Apply nested configuration overrides
        self._apply_nested_env_overrides(config_with_overrides)
        
        return config_with_overrides
    
    def _apply_nested_env_overrides(self, config: Dict[str, Any]):
        """Apply environment overrides for nested configuration sections."""
        
        # Tool calling configuration overrides
        if 'tool_calling' in config:
            tool_config = config['tool_calling']
            
            # TOOL_CALLING_ALLOW_DANGEROUS_FUNCTIONS
            dangerous_env = os.environ.get('TOOL_CALLING_ALLOW_DANGEROUS_FUNCTIONS')
            if dangerous_env is not None:
                tool_config['allow_dangerous_functions'] = dangerous_env.lower() in ('true', '1', 'yes')
                
            # TOOL_CALLING_STRICT_VALIDATION
            strict_env = os.environ.get('TOOL_CALLING_STRICT_VALIDATION')
            if strict_env is not None:
                tool_config['strict_parameter_validation'] = strict_env.lower() in ('true', '1', 'yes')
                
            # TOOL_CALLING_MAX_CONCURRENT
            max_concurrent_env = os.environ.get('TOOL_CALLING_MAX_CONCURRENT')
            if max_concurrent_env is not None:
                try:
                    tool_config['max_concurrent_calls'] = int(max_concurrent_env)
                except ValueError:
                    logger.warning(f"Invalid TOOL_CALLING_MAX_CONCURRENT value: {max_concurrent_env}")
                    
            # TOOL_CALLING_TIMEOUT
            timeout_env = os.environ.get('TOOL_CALLING_TIMEOUT')
            if timeout_env is not None:
                try:
                    tool_config['timeout'] = float(timeout_env)
                except ValueError:
                    logger.warning(f"Invalid TOOL_CALLING_TIMEOUT value: {timeout_env}")
        
        # Server configuration overrides
        server_overrides = {
            'HOST': ('host', str),
            'PORT': ('port', int),
            'DEBUG': ('debug', lambda x: x.lower() in ('true', '1', 'yes')),
            'ENVIRONMENT': ('environment', str),
            'MAX_WORKER_MEMORY': ('max_worker_memory', int),
            'VERBOSE_TOOL_LOGS': ('verbose_tool_logs', lambda x: x.lower() in ('true', '1', 'yes'))
        }
        
        for env_var, (config_key, converter) in server_overrides.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    config[config_key] = converter(env_value)
                    logger.debug(f"✅ Applied server override: {config_key} = {env_var}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid {env_var} value '{env_value}': {e}")
    
    def _get_default_main_config(self) -> Dict[str, Any]:
        """
        Get default main configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            'consumer_key': os.environ.get('SALESFORCE_CONSUMER_KEY', ''),
            'consumer_secret': os.environ.get('SALESFORCE_CONSUMER_SECRET', ''),
            'username': os.environ.get('SALESFORCE_USERNAME', ''),
            'instance_url': os.environ.get('SALESFORCE_INSTANCE_URL', ''),
            'api_version': os.environ.get('SALESFORCE_API_VERSION', 'v64.0'),
            'token_file': os.environ.get('SALESFORCE_MODELS_TOKEN_FILE', 'salesforce_models_token.json'),
            'tool_calling': {
                'allow_dangerous_functions': False,
                'strict_parameter_validation': True,
                'max_concurrent_calls': 3,
                'timeout': 30.0
            },
            'server': {
                'host': '0.0.0.0',
                'port': 8000,
                'debug': False,
                'environment': 'development'
            }
        }
    
    def _get_default_model_config(self) -> Dict[str, Any]:
        """
        Get default model mapping configuration.
        
        Returns:
            Default model configuration dictionary
        """
        return {
            "version": "1.0",
            "description": "Default Anthropic model mapping configuration",
            "models": [
                {
                    "id": "claude-3-5-sonnet-latest",
                    "object": "model",
                    "created": 1719792000,
                    "owned_by": "anthropic",
                    "display_name": "Claude 3.5 Sonnet",
                    "description": "Latest and most advanced Claude model",
                    "salesforce_model_id": "sfdc_ai__DefaultBedrockAnthropicClaude37Sonnet",
                    "max_tokens": 4096,
                    "input_tokens": 200000,
                    "capabilities": {
                        "text_generation": True,
                        "tool_calling": True,
                        "streaming": True,
                        "function_calling": True
                    }
                },
                {
                    "id": "claude-3-haiku-20240307",
                    "object": "model",
                    "created": 1709769600,
                    "owned_by": "anthropic",
                    "display_name": "Claude 3 Haiku",
                    "description": "Fast and efficient model for everyday tasks",
                    "salesforce_model_id": "sfdc_ai__DefaultBedrockAnthropicClaude3Haiku",
                    "max_tokens": 4096,
                    "input_tokens": 200000,
                    "capabilities": {
                        "text_generation": True,
                        "tool_calling": True,
                        "streaming": True,
                        "function_calling": True
                    }
                }
            ]
        }
    
    def _validate_main_config(self, config: Dict[str, Any]) -> None:
        """
        Validate main configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        required_fields = ['consumer_key', 'consumer_secret', 'instance_url']
        missing_fields = []
        
        for field in required_fields:
            if not config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            # Check if environment variables are available
            env_available = []
            for field in missing_fields:
                env_var = self._env_mappings.get(field)
                if env_var and os.environ.get(env_var):
                    env_available.append(field)
            
            # Remove fields that are available via environment
            missing_fields = [f for f in missing_fields if f not in env_available]
            
            if missing_fields:
                raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get main configuration with caching and environment overrides.
        
        Returns:
            Complete configuration dictionary
            
        Raises:
            ValueError: If required configuration is missing
        """
        with self._cache_lock:
            # Check cache validity - only use cache if it has data and is not expired
            if self._main_config_cache.data and not self._main_config_cache.is_expired():
                logger.debug("✅ Using cached main configuration")
                return deepcopy(self._main_config_cache.data)
            
            # Load configuration
            config_path = self._resolve_config_path(self._config_paths, "main")
            
            if config_path:
                try:
                    config = self._load_json_config(config_path)
                    logger.info(f"✅ Loaded main config from: {config_path}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"⚠️ Failed to load config file, using defaults: {e}")
                    config = self._get_default_main_config()
            else:
                logger.info("ℹ️ No config file found, using environment/defaults")
                config = self._get_default_main_config()
            
            # Apply environment overrides
            config = self._apply_env_overrides(config)
            
            # Validate configuration
            try:
                self._validate_main_config(config)
            except ValueError as e:
                logger.warning(f"⚠️ Config validation failed: {e}")
                # Don't cache invalid config, but still return it for debugging
                return config
            
            # Update cache
            self._main_config_cache.data = config
            self._main_config_cache.refresh_timestamp()
            
            logger.debug("✅ Main configuration loaded and cached")
            return deepcopy(config)
    
    async def get_config_async(self) -> Dict[str, Any]:
        """
        Async version of get_config() for use in async contexts.
        
        Returns:
            Complete configuration dictionary
        """
        async with self._async_cache_lock:
            # For the main config, we can use the sync version since file I/O
            # is typically fast and we want to maintain consistency
            return self.get_config()
    
    def get_model_mappings(self) -> Dict[str, Any]:
        """
        Get model mapping configuration with caching.
        
        Returns:
            Model mapping configuration dictionary
        """
        with self._cache_lock:
            # Check cache validity - only use cache if it has data and is not expired
            if self._model_config_cache.data and not self._model_config_cache.is_expired():
                logger.debug("✅ Using cached model configuration")
                return deepcopy(self._model_config_cache.data)
            
            # Load model configuration
            config_path = self._resolve_config_path(self._model_config_paths, "model")
            
            if config_path:
                try:
                    config = self._load_json_config(config_path)
                    logger.info(f"✅ Loaded model config from: {config_path}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"⚠️ Failed to load model config, using defaults: {e}")
                    config = self._get_default_model_config()
            else:
                logger.info("ℹ️ No model config file found, using defaults")
                config = self._get_default_model_config()
            
            # Update cache
            self._model_config_cache.data = config
            self._model_config_cache.refresh_timestamp()
            
            logger.debug("✅ Model configuration loaded and cached")
            return deepcopy(config)
    
    async def get_model_mappings_async(self) -> Dict[str, Any]:
        """
        Async version of get_model_mappings().
        
        Returns:
            Model mapping configuration dictionary
        """
        async with self._async_cache_lock:
            return self.get_model_mappings()
    
    def get_salesforce_config(self) -> Dict[str, Any]:
        """
        Get Salesforce-specific configuration.
        
        Returns:
            Salesforce configuration dictionary
        """
        config = self.get_config()
        return {
            'consumer_key': config['consumer_key'],
            'consumer_secret': config['consumer_secret'],
            'username': config.get('username', ''),
            'instance_url': config['instance_url'],
            'api_version': config.get('api_version', 'v64.0'),
            'token_file': config.get('token_file', 'salesforce_models_token.json')
        }
    
    async def get_salesforce_config_async(self) -> Dict[str, Any]:
        """
        Async version of get_salesforce_config().
        
        Returns:
            Salesforce configuration dictionary
        """
        config = await self.get_config_async()
        return {
            'consumer_key': config['consumer_key'],
            'consumer_secret': config['consumer_secret'],
            'username': config.get('username', ''),
            'instance_url': config['instance_url'],
            'api_version': config.get('api_version', 'v64.0'),
            'token_file': config.get('token_file', 'salesforce_models_token.json')
        }
    
    def get_tool_calling_config(self) -> Dict[str, Any]:
        """
        Get tool calling configuration.
        
        Returns:
            Tool calling configuration dictionary
        """
        config = self.get_config()
        return config.get('tool_calling', {
            'allow_dangerous_functions': False,
            'strict_parameter_validation': True,
            'max_concurrent_calls': 3,
            'timeout': 30.0
        })
    
    async def get_tool_calling_config_async(self) -> Dict[str, Any]:
        """
        Async version of get_tool_calling_config().
        
        Returns:
            Tool calling configuration dictionary
        """
        config = await self.get_config_async()
        return config.get('tool_calling', {
            'allow_dangerous_functions': False,
            'strict_parameter_validation': True,
            'max_concurrent_calls': 3,
            'timeout': 30.0
        })
    
    def get_server_config(self) -> Dict[str, Any]:
        """
        Get server configuration with environment overrides.
        
        Returns:
            Server configuration dictionary
        """
        config = self.get_config()
        
        # Server config with environment overrides
        server_config = {
            'host': os.environ.get('HOST', config.get('host', '0.0.0.0')),
            'port': int(os.environ.get('PORT', config.get('port', 8000))),
            'debug': os.environ.get('DEBUG', str(config.get('debug', False))).lower() in ('true', '1', 'yes'),
            'environment': os.environ.get('ENVIRONMENT', config.get('environment', 'development')),
            'max_worker_memory': int(os.environ.get('MAX_WORKER_MEMORY', config.get('max_worker_memory', 512))),
            'verbose_tool_logs': os.environ.get('VERBOSE_TOOL_LOGS', '0') == '1'
        }
        
        return server_config
    
    def clear_cache(self) -> None:
        """Clear all configuration caches."""
        with self._cache_lock:
            self._main_config_cache.data.clear()
            self._main_config_cache.refresh_timestamp()
            self._model_config_cache.data.clear()
            self._model_config_cache.refresh_timestamp()
            logger.info("🧹 Configuration cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.
        
        Returns:
            Cache statistics dictionary
        """
        with self._cache_lock:
            return {
                'main_config': {
                    'cached': bool(self._main_config_cache.data),
                    'expired': self._main_config_cache.is_expired(),
                    'timestamp': self._main_config_cache.timestamp,
                    'ttl': self._main_config_cache.ttl
                },
                'model_config': {
                    'cached': bool(self._model_config_cache.data),
                    'expired': self._model_config_cache.is_expired(),
                    'timestamp': self._model_config_cache.timestamp,
                    'ttl': self._model_config_cache.ttl
                }
            }


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None
_global_config_lock = threading.Lock()

def get_config_manager(config_file: Optional[str] = None, cache_ttl: float = 300.0) -> ConfigManager:
    """
    Get global configuration manager instance.
    
    Args:
        config_file: Optional path to config.json file
        cache_ttl: Cache TTL in seconds
        
    Returns:
        ConfigManager instance
    """
    global _global_config_manager
    
    with _global_config_lock:
        if _global_config_manager is None or config_file is not None:
            _global_config_manager = ConfigManager(config_file=config_file, cache_ttl=cache_ttl)
            logger.debug("✅ Global ConfigManager instance created")
        
        return _global_config_manager

def reset_global_config_manager() -> None:
    """Reset the global configuration manager instance (useful for testing)."""
    global _global_config_manager
    
    with _global_config_lock:
        _global_config_manager = None
        logger.debug("🔄 Global ConfigManager instance reset")


# Convenience functions for backward compatibility
def get_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get main configuration."""
    manager = get_config_manager(config_file)
    return manager.get_config()

async def get_config_async(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get main configuration asynchronously."""
    manager = get_config_manager(config_file)
    return await manager.get_config_async()

def get_salesforce_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get Salesforce configuration."""
    manager = get_config_manager(config_file)
    return manager.get_salesforce_config()

async def get_salesforce_config_async(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get Salesforce configuration asynchronously."""
    manager = get_config_manager(config_file)
    return await manager.get_salesforce_config_async()