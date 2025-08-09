"""
Adapters Module
===============

Backend adapter implementations for different API providers.
"""

from .anthropic_native import AnthropicNativeAdapter

__all__ = ['AnthropicNativeAdapter']