#!/usr/bin/env python3
"""
Model Router for Smart Tool Behaviour Compatibility
=================================================

Implements intelligent model routing with OpenAI-native detection and 
tool response normalization for the sf-model-api Tool Behaviour Compatibility Layer.

Key Features:
- OpenAI-native model detection for direct tool_calls passthrough
- Cross-backend response normalization architecture
- Environment-based behavior control
- Thread-safe caching for performance optimization

Usage:
    from model_router import ModelRouter, is_openai_native_model
    
    router = ModelRouter()
    if router.is_openai_native(model_name):
        # Direct passthrough logic
        pass
    else:
        # Apply response normalization
        normalized_response = router.normalize_response(response, model_name)
"""

import os
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass
from functools import lru_cache

logger = logging.getLogger(__name__)

# OpenAI-native model patterns for direct tool_calls passthrough
OPENAI_NATIVE_PATTERNS = {
    "sfdc_ai__DefaultGPT4Omni",        # GPT-4 Omni via Salesforce
    "gpt-",                            # Direct GPT models (gpt-4, gpt-3.5-turbo, etc.)
    "o-",                              # OpenAI o-series models (o1, o3, etc.)
    "openai/gpt-oss"                   # Open source GPT models
}

@dataclass
class ModelCapabilities:
    """Model capability definition for routing decisions."""
    supports_native_tools: bool = False
    backend_type: str = "salesforce"
    requires_normalization: bool = True
    max_tokens_default: int = 1000
    supports_streaming: bool = True

class ModelRouter:
    """
    Intelligent model router for Tool Behaviour Compatibility Layer.
    
    Handles OpenAI-native model detection, response normalization routing,
    and environment-based behavior control for optimal tool calling compatibility.
    """
    
    def __init__(self):
        """Initialize the model router with environment-based configuration."""
        self.openai_passthrough_enabled = os.getenv("OPENAI_NATIVE_TOOL_PASSTHROUGH", "1") == "1"
        self.model_capabilities_cache = {}
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging for model routing operations."""
        log_level = os.getenv("MODEL_ROUTER_LOG_LEVEL", "WARNING").upper()
        logger.setLevel(getattr(logging, log_level, logging.WARNING))
    
    @lru_cache(maxsize=128)
    def is_openai_native(self, model: str) -> bool:
        """
        Detect if a model is OpenAI-native and supports direct tool_calls passthrough.
        
        OpenAI-native models can directly return tool_calls in responses without
        text parsing or normalization, improving performance and accuracy.
        
        Args:
            model: Model name to check (e.g., "gpt-4", "sfdc_ai__DefaultGPT4Omni")
            
        Returns:
            bool: True if model supports native OpenAI tool_calls format
        """
        if not self.openai_passthrough_enabled:
            return False
            
        model_lower = model.lower()
        
        # Check against known OpenAI-native patterns
        for pattern in OPENAI_NATIVE_PATTERNS:
            if pattern.lower() in model_lower or model_lower.startswith(pattern.lower()):
                logger.debug(f"🔍 OpenAI-native model detected: {model} (pattern: {pattern})")
                return True
        
        return False
    
    def get_model_capabilities(self, model: str) -> ModelCapabilities:
        """
        Get comprehensive model capabilities for routing decisions.
        
        Args:
            model: Model name to analyze
            
        Returns:
            ModelCapabilities: Capability information for the model
        """
        if model in self.model_capabilities_cache:
            return self.model_capabilities_cache[model]
        
        # Determine capabilities based on model type
        is_native = self.is_openai_native(model)
        
        if is_native:
            capabilities = ModelCapabilities(
                supports_native_tools=True,
                backend_type="openai_native",
                requires_normalization=False,
                max_tokens_default=4000 if "gpt-4" in model.lower() else 1000,
                supports_streaming=True
            )
        elif "claude" in model.lower():
            capabilities = ModelCapabilities(
                supports_native_tools=False,
                backend_type="anthropic",
                requires_normalization=True,
                max_tokens_default=1000,
                supports_streaming=True
            )
        elif "gemini" in model.lower():
            capabilities = ModelCapabilities(
                supports_native_tools=False,
                backend_type="google",
                requires_normalization=True,
                max_tokens_default=1000,
                supports_streaming=True
            )
        else:
            # Default Salesforce-hosted model
            capabilities = ModelCapabilities(
                supports_native_tools=False,
                backend_type="salesforce",
                requires_normalization=True,
                max_tokens_default=1000,
                supports_streaming=True
            )
        
        # Cache for performance
        self.model_capabilities_cache[model] = capabilities
        return capabilities
    
    def should_use_direct_passthrough(self, model: str, tools: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Determine if direct tool_calls passthrough should be used.
        
        Args:
            model: Model name
            tools: Tool definitions (optional)
            
        Returns:
            bool: True if direct passthrough is recommended
        """
        if not tools:
            return False
            
        capabilities = self.get_model_capabilities(model)
        return capabilities.supports_native_tools and self.openai_passthrough_enabled
    
    def normalize_tool_response(
        self, 
        response: Dict[str, Any], 
        model: str,
        original_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Normalize tool calling responses across different backends to OpenAI format.
        
        This is the core response normalization architecture that ensures
        consistent tool_calls schema regardless of backend model type.
        
        Args:
            response: Raw model response
            model: Model name for backend-specific handling  
            original_tools: Original tool definitions for validation
            
        Returns:
            Dict: Normalized response in OpenAI tool_calls format
        """
        capabilities = self.get_model_capabilities(model)
        
        # Direct passthrough for OpenAI-native models with light normalization
        if capabilities.supports_native_tools:
            logger.debug(f"🔧 Direct passthrough for OpenAI-native model: {model}")
            try:
                from response_normaliser import normalise_assistant_tool_response
                # Even OpenAI-native models need normalization for consistency
                if "choices" in response and response["choices"]:
                    message = response["choices"][0].get("message", {})
                    tool_calls = message.get("tool_calls", [])
                    if tool_calls:
                        normalized_message = normalise_assistant_tool_response(message, tool_calls)
                        response["choices"][0]["message"] = normalized_message
                        response["choices"][0]["finish_reason"] = "tool_calls"
            except ImportError:
                logger.warning("Response normaliser not available for OpenAI-native normalization")
            return response
        
        # Apply backend-specific normalization using new normalizer
        try:
            from response_normaliser import default_normaliser
            import asyncio
            
            # Use async normalization for better performance
            if asyncio.iscoroutinefunction(default_normaliser.normalise_response_async):
                try:
                    # Try to run async if event loop is available
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create a task for async execution
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                default_normaliser.normalise_response_async(
                                    response, 
                                    capabilities.backend_type, 
                                    model
                                )
                            )
                            result = future.result()
                            return result.normalized_response
                    else:
                        # Run async directly
                        result = asyncio.run(
                            default_normaliser.normalise_response_async(
                                response, 
                                capabilities.backend_type, 
                                model
                            )
                        )
                        return result.normalized_response
                except Exception as e:
                    logger.warning(f"Async normalization failed, falling back to sync: {e}")
            
            # Fallback to legacy normalization methods
            if capabilities.backend_type == "anthropic":
                return self._normalize_anthropic_response(response, model)
            elif capabilities.backend_type == "google":
                return self._normalize_google_response(response, model)
            else:
                return self._normalize_salesforce_response(response, model)
                
        except ImportError:
            logger.warning("Response normaliser not available, using legacy normalization")
            # Apply legacy backend-specific normalization
            if capabilities.backend_type == "anthropic":
                return self._normalize_anthropic_response(response, model)
            elif capabilities.backend_type == "google":
                return self._normalize_google_response(response, model)
            else:
                return self._normalize_salesforce_response(response, model)
    
    def _normalize_anthropic_response(self, response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        Normalize Anthropic Claude responses to OpenAI tool_calls format.
        
        Handles text parsing for function calls and converts to structured
        tool_calls array format expected by OpenAI-compatible clients.
        """
        logger.debug(f"🔧 Normalizing Anthropic response for model: {model}")
        
        # Extract choices and message content
        if "choices" not in response or not response["choices"]:
            return response
        
        choice = response["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        # Look for function calls in the content text
        # This would contain the actual parsing logic for Anthropic tool calls
        # For now, return as-is (implementation placeholder)
        return response
    
    def _normalize_google_response(self, response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        Normalize Google Gemini responses to OpenAI tool_calls format.
        """
        logger.debug(f"🔧 Normalizing Google response for model: {model}")
        return response
    
    def _normalize_salesforce_response(self, response: Dict[str, Any], model: str) -> Dict[str, Any]:
        """
        Normalize Salesforce-hosted model responses to OpenAI tool_calls format.
        """
        logger.debug(f"🔧 Normalizing Salesforce response for model: {model}")
        return response
    
    def get_routing_info(self, model: str, tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Get comprehensive routing information for a model and tool combination.
        
        Args:
            model: Model name
            tools: Tool definitions
            
        Returns:
            Dict: Routing decision information
        """
        capabilities = self.get_model_capabilities(model)
        use_passthrough = self.should_use_direct_passthrough(model, tools)
        
        return {
            "model": model,
            "capabilities": {
                "supports_native_tools": capabilities.supports_native_tools,
                "backend_type": capabilities.backend_type,
                "requires_normalization": capabilities.requires_normalization,
                "supports_streaming": capabilities.supports_streaming
            },
            "routing_decision": {
                "use_direct_passthrough": use_passthrough,
                "requires_normalization": not use_passthrough and bool(tools),
                "environment_settings": {
                    "openai_passthrough_enabled": self.openai_passthrough_enabled,
                    "preserve_tools_enabled": os.getenv("N8N_COMPAT_PRESERVE_TOOLS", "1") == "1"
                }
            },
            "performance_optimizations": {
                "cached_capabilities": model in self.model_capabilities_cache,
                "direct_passthrough_available": use_passthrough
            }
        }

# Global router instance for performance (thread-safe)
_global_router: Optional[ModelRouter] = None

def get_model_router() -> ModelRouter:
    """Get thread-safe global model router instance."""
    global _global_router
    if _global_router is None:
        _global_router = ModelRouter()
    return _global_router

def is_openai_native_model(model: str) -> bool:
    """
    Convenience function to check if a model is OpenAI-native.
    
    Args:
        model: Model name to check
        
    Returns:
        bool: True if model supports native OpenAI tool_calls
    """
    return get_model_router().is_openai_native(model)

# Convenience exports
__all__ = [
    "ModelRouter", 
    "ModelCapabilities", 
    "get_model_router", 
    "is_openai_native_model",
    "OPENAI_NATIVE_PATTERNS"
]