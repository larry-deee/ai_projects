#!/usr/bin/env python3
"""
Anthropic Native Pass-Through Adapter
=====================================

Hardened native pass-through adapter for Anthropic API that provides:
- Zero schema transformation (preserves native Anthropic request/response format)
- Hardened httpx client with security restrictions
- SSE streaming with verbatim relay
- Proper header management and correlation ID preservation
- Error pass-through with original HTTP status codes
- Tool calls in native Anthropic format without normalization

Architecture Principles:
- Native pass-through with minimal transformation
- Security-first client configuration (no redirects, timeouts)
- Verbatim SSE event relay from upstream
- Header filtering and correlation preservation
- Graceful lifecycle management with resource cleanup

Usage:
    adapter = AnthropicNativeAdapter()
    await adapter.initialize()
    
    # Native pass-through request
    response = await adapter.messages(request_data, headers)
    
    # Cleanup
    await adapter.shutdown()
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Union, List
from contextlib import asynccontextmanager

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

class AnthropicNativeAdapter:
    """
    Hardened native pass-through adapter for Anthropic API.
    
    This adapter provides a secure, high-performance proxy to the Anthropic API
    while preserving native request/response formats and implementing proper
    security boundaries.
    """
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 anthropic_version: Optional[str] = None,
                 timeout: float = 60.0,
                 max_connections: int = 200,
                 max_keepalive: int = 100,
                 keepalive_expiry: float = 30.0,
                 chunk_size: int = 8192):
        """
        Initialize the Anthropic native adapter.
        
        Args:
            base_url: Anthropic API base URL (defaults to env var or standard URL)
            api_key: Anthropic API key (defaults to env var)
            anthropic_version: API version header (defaults to env var or 2023-06-01)
            timeout: Request timeout in seconds
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for AnthropicNativeAdapter. "
                "Install with: pip install httpx"
            )
            
        # Configuration with environment variable fallbacks
        self.base_url = base_url or os.getenv('ANTHROPIC_BASE_URL', 'https://api.anthropic.com')
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.anthropic_version = anthropic_version or os.getenv('ANTHROPIC_VERSION', '2023-06-01')
        self.timeout = float(os.getenv('ANTHROPIC_TIMEOUT', str(timeout)))
        self.max_connections = int(os.getenv('ANTHROPIC_MAX_CONNECTIONS', str(max_connections)))
        self.max_keepalive = int(os.getenv('ANTHROPIC_MAX_KEEPALIVE', str(max_keepalive)))
        self.keepalive_expiry = float(os.getenv('ANTHROPIC_KEEPALIVE_EXPIRY', str(keepalive_expiry)))
        self.chunk_size = int(os.getenv('ANTHROPIC_CHUNK_SIZE', str(chunk_size)))
        
        # Validate required configuration
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        # Validate configuration values
        if self.timeout <= 0:
            raise ValueError(f"ANTHROPIC_TIMEOUT must be positive, got {self.timeout}")
        
        if self.max_connections <= 0:
            raise ValueError(f"ANTHROPIC_MAX_CONNECTIONS must be positive, got {self.max_connections}")
        
        if self.max_keepalive <= 0:
            raise ValueError(f"ANTHROPIC_MAX_KEEPALIVE must be positive, got {self.max_keepalive}")
        
        if self.max_keepalive > self.max_connections:
            logger.warning(f"⚠️  ANTHROPIC_MAX_KEEPALIVE ({self.max_keepalive}) is greater than "
                          f"ANTHROPIC_MAX_CONNECTIONS ({self.max_connections}). "
                          f"Adjusting keepalive to {self.max_connections}")
            self.max_keepalive = self.max_connections
        
        # Validate base URL format
        if not self.base_url.startswith(('http://', 'https://')):
            raise ValueError(f"ANTHROPIC_BASE_URL must start with http:// or https://, got {self.base_url}")
        
        # Client state and performance monitoring
        self._client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        self._lock = asyncio.Lock()
        self._connection_pool_stats = {'hits': 0, 'misses': 0, 'timeouts': 0}
        self._request_count = 0
        self._cached_headers = None  # Cache for frequently used headers
        
        logger.info(f"🔧 AnthropicNativeAdapter configured: base_url={self.base_url}")
    
    async def initialize(self) -> None:
        """
        Initialize the httpx client with hardened security configuration.
        
        Security features:
        - No redirect following for security
        - Strict timeouts to prevent hanging
        - Connection limits to prevent resource exhaustion
        - Proper SSL verification
        """
        async with self._lock:
            if self._initialized:
                return
                
            # Optimized httpx client configuration for production workloads
            limits = httpx.Limits(
                max_keepalive_connections=self.max_keepalive,
                max_connections=self.max_connections,
                keepalive_expiry=self.keepalive_expiry
            )
            
            # Adaptive timeout configuration optimized for streaming
            timeout_config = httpx.Timeout(
                connect=5.0,      # Faster connection timeout
                read=None,        # No read timeout for streaming (handled at higher level)
                write=15.0,       # Reasonable write timeout
                pool=2.0          # Faster pool timeout
            )
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout_config,
                limits=limits,
                follow_redirects=False,  # Security: no redirect following
                verify=True,  # Always verify SSL certificates
                http2=True,  # Enable HTTP/2 for better multiplexing
                headers=self._get_default_headers()
            )
            
            self._initialized = True
            logger.info("🚀 AnthropicNativeAdapter initialized with hardened httpx client")
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the httpx client with connection draining and cleanup.
        """
        async with self._lock:
            if self._client:
                try:
                    # Allow pending requests to complete (connection draining)
                    await asyncio.sleep(0.1)
                    
                    # Log final performance statistics
                    logger.info(f"📊 Final connection stats: {self._connection_pool_stats}")
                    logger.info(f"📊 Total requests processed: {self._request_count}")
                    
                    await self._client.aclose()
                    logger.info("🔒 AnthropicNativeAdapter client shutdown complete")
                except Exception as e:
                    logger.warning(f"⚠️  Error during client shutdown: {e}")
                finally:
                    self._client = None
                    self._initialized = False
                    self._cached_headers = None
    
    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default headers for Anthropic API requests with caching for performance.
        
        Returns:
            Dict: Headers with authentication and version information
        """
        if self._cached_headers is None:
            self._cached_headers = {
                'x-api-key': self.api_key,
                'anthropic-version': self.anthropic_version,
                'content-type': 'application/json',
                'user-agent': 'sf-model-api-anthropic-native/1.0'
            }
        return self._cached_headers.copy()  # Return copy to prevent mutation
    
    def _prepare_headers(self, request_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Prepare headers for upstream request with optimized filtering.
        
        Preserves:
        - anthropic-beta headers for feature flags
        - x-api-key (from configuration)
        - anthropic-version (from configuration)
        - content-type for requests
        
        Filters out:
        - hop-by-hop headers
        - host headers
        - connection-related headers
        
        Args:
            request_headers: Incoming request headers
            
        Returns:
            Dict: Filtered headers for upstream request
        """
        headers = self._get_default_headers()
        
        if request_headers:
            # Optimized header filtering with single pass
            for key, value in request_headers.items():
                if key.lower().startswith('anthropic-beta'):
                    headers[key] = value
        
        return headers
    
    def _filter_response_headers(self, response_headers: httpx.Headers) -> Dict[str, str]:
        """
        Filter response headers for client, preserving important Anthropic headers.
        
        Preserves:
        - anthropic-request-id for correlation
        - content-type for response parsing
        - cache-control for streaming
        - connection headers for SSE
        - rate limit headers for client awareness
        
        Filters out:
        - server implementation details
        - internal routing headers
        - hop-by-hop headers
        
        Args:
            response_headers: Upstream response headers
            
        Returns:
            Dict: Filtered headers for client response
        """
        # Headers to preserve from upstream
        allowed_headers = {
            'content-type',
            'cache-control', 
            'connection',
            'anthropic-request-id',
            'x-ratelimit-requests-limit',
            'x-ratelimit-requests-remaining',
            'x-ratelimit-requests-reset',
            'x-ratelimit-tokens-limit',
            'x-ratelimit-tokens-remaining',
            'x-ratelimit-tokens-reset'
        }
        
        # Headers to explicitly drop (hop-by-hop)
        hop_by_hop_headers = {
            'transfer-encoding',
            'content-encoding', 
            'server',
            'alt-svc',
            'date',
            'content-length'
        }
        
        filtered = {}
        for key, value in response_headers.items():
            key_lower = key.lower()
            if key_lower in allowed_headers and key_lower not in hop_by_hop_headers:
                filtered[key] = value
        
        return filtered
    
    async def messages(self, 
                      request_data: Dict[str, Any], 
                      request_headers: Optional[Dict[str, str]] = None,
                      stream: bool = False) -> Union[Dict[str, Any], AsyncGenerator[bytes, None]]:
        """
        Native pass-through to Anthropic messages API.
        
        This method provides zero-transformation proxying to the Anthropic API,
        preserving native request/response formats including tool calls.
        
        Args:
            request_data: Native Anthropic request payload
            request_headers: Optional request headers
            stream: Whether to stream the response
            
        Returns:
            Union[Dict, AsyncGenerator]: Native Anthropic response or byte stream for SSE
            
        Raises:
            httpx.HTTPStatusError: For upstream API errors (preserves status codes)
            httpx.RequestError: For connection errors
        """
        if not self._initialized:
            await self.initialize()
        
        # Increment request counter for monitoring
        self._request_count += 1
        
        headers = self._prepare_headers(request_headers)
        
        # Enable streaming if requested
        if stream:
            headers['accept'] = 'text/event-stream'
            headers['cache-control'] = 'no-cache'
            headers['connection'] = 'keep-alive'
        
        try:
            if stream:
                return self._stream_messages(request_data, headers)
            else:
                response = await self._client.post(
                    '/v1/messages',
                    json=request_data,
                    headers=headers
                )
                
                # Preserve original HTTP status code for error pass-through
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            # Track error in performance statistics
            self._connection_pool_stats['misses'] += 1
            # Log error details but preserve original error for FastAPI handling
            logger.warning(f"⚠️  Anthropic API HTTP error {e.response.status_code}: {e}")
            if hasattr(e.response, 'text'):
                try:
                    error_text = e.response.text
                    if error_text:
                        logger.debug(f"Error response body: {error_text[:500]}")
                except Exception:
                    pass
            raise
        except httpx.TimeoutException as e:
            # Track timeout in performance statistics
            self._connection_pool_stats['timeouts'] += 1
            logger.error(f"❌ Timeout error to Anthropic API: {e}")
            raise
        except httpx.RequestError as e:
            # Track connection error in performance statistics
            self._connection_pool_stats['misses'] += 1
            logger.error(f"❌ Connection error to Anthropic API: {e}")
            raise
        else:
            # Track successful connection reuse
            self._connection_pool_stats['hits'] += 1
    
    async def count_tokens(self, 
                          request_data: Dict[str, Any], 
                          request_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Native pass-through to Anthropic count tokens API.
        
        Args:
            request_data: Native Anthropic count tokens request payload
            request_headers: Optional request headers
            
        Returns:
            Dict: Native Anthropic count tokens response
            
        Raises:
            httpx.HTTPStatusError: For upstream API errors (preserves status codes)
            httpx.RequestError: For connection errors
        """
        if not self._initialized:
            await self.initialize()
        
        headers = self._prepare_headers(request_headers)
        
        try:
            response = await self._client.post(
                '/v1/messages/count_tokens',
                json=request_data,
                headers=headers
            )
            
            # Preserve original HTTP status code for error pass-through
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️  Anthropic API HTTP error {e.response.status_code}: {e}")
            if hasattr(e.response, 'text'):
                try:
                    error_text = e.response.text
                    if error_text:
                        logger.debug(f"Error response body: {error_text[:500]}")
                except Exception:
                    pass
            raise
        except httpx.TimeoutException as e:
            logger.error(f"❌ Timeout error to Anthropic API: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ Connection error to Anthropic API: {e}")
            raise
    
    async def list_models(self, 
                         request_headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Native pass-through to Anthropic models API.
        
        Args:
            request_headers: Optional request headers
            
        Returns:
            Dict: Native Anthropic models response
            
        Raises:
            httpx.HTTPStatusError: For upstream API errors (preserves status codes)
            httpx.RequestError: For connection errors
        """
        if not self._initialized:
            await self.initialize()
        
        headers = self._prepare_headers(request_headers)
        
        try:
            response = await self._client.get(
                '/v1/models',
                headers=headers
            )
            
            # Preserve original HTTP status code for error pass-through
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"⚠️  Anthropic API HTTP error {e.response.status_code}: {e}")
            if hasattr(e.response, 'text'):
                try:
                    error_text = e.response.text
                    if error_text:
                        logger.debug(f"Error response body: {error_text[:500]}")
                except Exception:
                    pass
            raise
        except httpx.TimeoutException as e:
            logger.error(f"❌ Timeout error to Anthropic API: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"❌ Connection error to Anthropic API: {e}")
            raise
    
    async def _stream_messages(self, 
                              request_data: Dict[str, Any], 
                              headers: Dict[str, str]) -> AsyncGenerator[bytes, None]:
        """
        Stream messages with verbatim SSE relay from Anthropic API.
        
        This method provides byte-for-byte SSE streaming without buffering
        or event transformation, ensuring real-time streaming performance.
        
        Args:
            request_data: Native Anthropic request payload
            headers: Prepared request headers
            
        Yields:
            bytes: Raw SSE events from Anthropic API
        """
        try:
            async with self._client.stream(
                'POST',
                '/v1/messages',
                json=request_data,
                headers=headers
            ) as response:
                # Pass through error status codes
                response.raise_for_status()
                
                # High-performance streaming with optimized chunk size
                async for chunk in response.aiter_raw(chunk_size=self.chunk_size):
                    if chunk:  # Only yield non-empty chunks
                        yield chunk
                    
        except httpx.HTTPStatusError as e:
            # Stream error as SSE event for client handling
            error_data = {
                'type': 'error',
                'error': {
                    'type': 'api_error',
                    'message': str(e)
                }
            }
            error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
            yield error_event.encode('utf-8')
        except httpx.TimeoutException as e:
            # Stream timeout error as SSE event
            error_data = {
                'type': 'error',
                'error': {
                    'type': 'timeout_error',
                    'message': f'Request timeout: {str(e)}'
                }
            }
            error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
            yield error_event.encode('utf-8')
        except httpx.RequestError as e:
            # Stream connection error as SSE event
            error_data = {
                'type': 'error',
                'error': {
                    'type': 'connection_error',
                    'message': f'Connection error: {str(e)}'
                }
            }
            error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
            yield error_event.encode('utf-8')
    
    @asynccontextmanager
    async def lifespan(self):
        """
        Async context manager for proper resource lifecycle.
        
        Usage:
            async with adapter.lifespan():
                # Use adapter
                response = await adapter.messages(data)
        """
        try:
            await self.initialize()
            yield self
        finally:
            await self.shutdown()
    
    def __del__(self):
        """
        Cleanup resources on garbage collection.
        """
        if self._client and not self._client.is_closed:
            logger.warning("⚠️  AnthropicNativeAdapter not properly shutdown - resources may leak")
            # Try to schedule cleanup, but don't block
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.shutdown())
            except RuntimeError:
                # No running loop, can't schedule cleanup
                pass


# Singleton instance for application-wide use
_global_adapter: Optional[AnthropicNativeAdapter] = None
_adapter_lock = asyncio.Lock()

async def get_anthropic_adapter() -> AnthropicNativeAdapter:
    """
    Get or create the global AnthropicNativeAdapter instance.
    
    Returns:
        AnthropicNativeAdapter: Initialized singleton adapter
    """
    global _global_adapter
    
    async with _adapter_lock:
        if _global_adapter is None:
            _global_adapter = AnthropicNativeAdapter()
            await _global_adapter.initialize()
        
        return _global_adapter

async def shutdown_anthropic_adapter() -> None:
    """
    Shutdown the global AnthropicNativeAdapter instance.
    """
    global _global_adapter
    
    async with _adapter_lock:
        if _global_adapter:
            await _global_adapter.shutdown()
            _global_adapter = None


# Performance monitoring and metrics functions
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics from the global adapter instance.
    
    Returns:
        Dict: Performance statistics and connection pool metrics
    """
    global _global_adapter
    
    if _global_adapter is None:
        return {
            'status': 'not_initialized',
            'error': 'Adapter not initialized'
        }
    
    client_info = {}
    if _global_adapter._client:
        # Get connection pool information from httpx client
        try:
            pool_stats = _global_adapter._client._mounts.get('https://', {})
            if hasattr(pool_stats, '_pool'):
                client_info = {
                    'pool_connections': len(getattr(pool_stats._pool, '_connections', [])),
                    'is_closed': _global_adapter._client.is_closed
                }
        except Exception:
            client_info = {'error': 'Unable to retrieve client info'}
    
    return {
        'status': 'active',
        'initialized': _global_adapter._initialized,
        'request_count': _global_adapter._request_count,
        'connection_stats': _global_adapter._connection_pool_stats,
        'client_info': client_info,
        'configuration': {
            'base_url': _global_adapter.base_url,
            'timeout': _global_adapter.timeout,
            'max_connections': _global_adapter.max_connections,
            'max_keepalive': _global_adapter.max_keepalive,
            'keepalive_expiry': _global_adapter.keepalive_expiry,
            'chunk_size': _global_adapter.chunk_size
        }
    }


async def reset_performance_metrics() -> Dict[str, Any]:
    """
    Reset performance metrics for the global adapter instance.
    
    Returns:
        Dict: Status of the reset operation
    """
    global _global_adapter
    
    if _global_adapter is None:
        return {
            'status': 'error',
            'message': 'Adapter not initialized'
        }
    
    _global_adapter._connection_pool_stats = {'hits': 0, 'misses': 0, 'timeouts': 0}
    _global_adapter._request_count = 0
    
    return {
        'status': 'success',
        'message': 'Performance metrics reset successfully'
    }