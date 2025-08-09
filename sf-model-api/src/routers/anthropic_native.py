#!/usr/bin/env python3
"""
Anthropic Native Router
=======================

Flask router implementation for native Anthropic API endpoints that provides:
- Native Anthropic endpoints under /anthropic path
- SSE streaming with proper headers and no buffering
- Error pass-through from upstream without proxy 500s
- Tool handling without OpenAI normalization
- Request/response in native Anthropic format

Endpoints:
- POST /anthropic/v1/messages - Native Anthropic messages API
- GET /anthropic/health - Health check endpoint

Architecture:
- Isolated under /anthropic path to avoid OpenAI front-door conflicts
- Direct integration with AnthropicNativeAdapter
- Proper SSE headers and streaming configuration
- Error preservation with original HTTP status codes

Usage:
    from routers.anthropic_native import AnthropicNativeRouter
    
    router = AnthropicNativeRouter()
    app.register_blueprint(router.create_blueprint())
"""

import json
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Generator, Tuple, Union
from flask import Blueprint, request, Response, jsonify
import threading

from adapters.anthropic_native import get_anthropic_adapter, AnthropicNativeAdapter, get_performance_metrics

logger = logging.getLogger(__name__)

class AnthropicNativeRouter:
    """
    Flask router for native Anthropic API endpoints.
    
    This router provides native pass-through functionality for Anthropic API
    while maintaining complete isolation from OpenAI front-door paths.
    """
    
    def __init__(self, url_prefix: str = '/anthropic'):
        """
        Initialize the Anthropic native router.
        
        Args:
            url_prefix: URL prefix for all Anthropic endpoints (default: /anthropic)
        """
        self.url_prefix = url_prefix
        self._adapter: Optional[AnthropicNativeAdapter] = None
        # Performance optimization: Pre-create thread pool for async operations
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='anthropic_async')
        self._loop_cache = threading.local()  # Thread-local event loop cache
        
        logger.info(f"🔧 AnthropicNativeRouter configured with prefix: {url_prefix}")
    
    def create_blueprint(self) -> Blueprint:
        """
        Create Flask blueprint with Anthropic native endpoints.
        
        Returns:
            Blueprint: Configured Flask blueprint
        """
        bp = Blueprint('anthropic_native', __name__, url_prefix=self.url_prefix)
        
        # Register endpoints
        bp.add_url_rule('/v1/messages', 'messages', self._messages_endpoint, methods=['POST'])
        bp.add_url_rule('/v1/messages/count_tokens', 'count_tokens', self._count_tokens_endpoint, methods=['POST'])
        bp.add_url_rule('/v1/models', 'models', self._models_endpoint, methods=['GET'])
        bp.add_url_rule('/health', 'health', self._health_endpoint, methods=['GET'])
        bp.add_url_rule('/metrics', 'metrics', self._metrics_endpoint, methods=['GET'])
        
        # Register error handlers
        bp.errorhandler(Exception)(self._error_handler)
        
        logger.info("📋 AnthropicNativeRouter blueprint created with endpoints")
        return bp
    
    async def _get_adapter(self) -> AnthropicNativeAdapter:
        """
        Get or create the AnthropicNativeAdapter instance.
        
        Returns:
            AnthropicNativeAdapter: Initialized adapter
        """
        if self._adapter is None:
            self._adapter = await get_anthropic_adapter()
        return self._adapter
    
    def _messages_endpoint(self) -> Union[Response, Tuple[Response, int]]:
        """
        Native Anthropic messages endpoint.
        
        Handles POST /anthropic/v1/messages with:
        - Native Anthropic request/response format
        - SSE streaming support with proper headers
        - Error pass-through with original status codes
        - Tool calls in native Anthropic format
        """
        try:
            # Validate request content type
            if not request.is_json:
                return jsonify({
                    'type': 'error',
                    'error': {
                        'type': 'invalid_request_error',
                        'message': 'Content-Type must be application/json'
                    }
                }), 400
            
            request_data = request.get_json()
            if not request_data:
                return jsonify({
                    'type': 'error',
                    'error': {
                        'type': 'invalid_request_error',
                        'message': 'Request body must contain valid JSON'
                    }
                }), 400
            
            # Check for streaming request
            stream_requested = request_data.get('stream', False)
            
                # Extract headers for upstream request
            request_headers = dict(request.headers)
            
            if stream_requested:
                # Handle SSE streaming response
                return self._handle_streaming_response(
                    request_data, request_headers
                )
            else:
                # Handle regular JSON response
                response_data = self._run_async(lambda: self._get_adapter_and_call_messages(
                    request_data, request_headers, stream=False
                ))
                return jsonify(response_data)
        
        except Exception as e:
            logger.error(f"❌ Error in messages endpoint: {e}")
            return self._create_error_response(str(e), 500)
    
    def _handle_streaming_response(self, 
                                  request_data: Dict[str, Any],
                                  request_headers: Dict[str, str]) -> Response:
        """
        Handle SSE streaming response with proper headers.
        
        Args:
            request_data: Native Anthropic request payload
            request_headers: Request headers
            
        Returns:
            Response: Flask streaming response with SSE headers
        """
        def generate_stream() -> Generator[bytes, None, None]:
            """Generator for SSE events from Anthropic API."""
            try:
                # Run async streaming in a separate thread
                for chunk in self._run_async_stream(
                    lambda: self._get_adapter_and_stream_messages(
                        request_data, request_headers
                    )
                ):
                    yield chunk
                    
            except Exception as e:
                logger.error(f"❌ Streaming error: {e}")
                # Send error as SSE event
                error_data = {
                    'type': 'error',
                    'error': {
                        'type': 'api_error',
                        'message': str(e)
                    }
                }
                error_event = f"event: error\ndata: {json.dumps(error_data)}\n\n"
                yield error_event.encode('utf-8')
        
        # Create streaming response with proper SSE headers
        response = Response(
            generate_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',  # Disable nginx buffering
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS'
            }
        )
        
        return response
    
    def _run_async(self, coro_func) -> Any:
        """
        Run an async coroutine function using optimized event loop management.
        
        Uses thread-local event loop caching to avoid creating new loops
        for every request, improving performance significantly.
        
        Args:
            coro_func: Function that returns a coroutine
            
        Returns:
            Result of the coroutine
        """
        # Use thread-local loop cache for better performance
        if not hasattr(self._loop_cache, 'loop'):
            self._loop_cache.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop_cache.loop)
        
        loop = self._loop_cache.loop
        try:
            return loop.run_until_complete(coro_func())
        except RuntimeError as e:
            if "cannot be called from a running event loop" in str(e):
                # Fallback to thread pool execution
                future = self._thread_pool.submit(
                    lambda: asyncio.run(coro_func())
                )
                return future.result(timeout=30)  # 30 second timeout
            raise
    
    def _run_async_stream(self, coro_func) -> Generator[bytes, None, None]:
        """
        Run an async streaming coroutine function with optimized loop management.
        
        Uses thread pool for streaming to avoid blocking the main thread
        and provides better streaming performance.
        
        Args:
            coro_func: Function that returns an async generator
            
        Yields:
            Items from the async generator with optimized chunking
        """
        def run_streaming_in_thread():
            """Run streaming in a separate thread with its own event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def collect_chunks():
                    chunks = []
                    async_gen = await coro_func()
                    try:
                        async for chunk in async_gen:
                            chunks.append(chunk)
                            # Yield in batches for better streaming performance
                            if len(chunks) >= 5:  # Batch size optimization
                                yield b''.join(chunks)
                                chunks = []
                        # Yield remaining chunks
                        if chunks:
                            yield b''.join(chunks)
                    except Exception as e:
                        logger.error(f"Streaming error: {e}")
                        raise
                
                # Run the streaming collection
                return loop.run_until_complete(collect_chunks())
            finally:
                loop.close()
        
        # Use thread pool for streaming to avoid blocking
        future = self._thread_pool.submit(run_streaming_in_thread)
        try:
            for chunk_batch in future.result(timeout=60):  # 60 second timeout for streaming
                yield chunk_batch
        except Exception as e:
            logger.error(f"Async streaming error: {e}")
            error_event = f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
            yield error_event.encode('utf-8')
    
    async def _get_adapter_and_call_messages(self, request_data: Dict[str, Any], 
                                           request_headers: Dict[str, str], 
                                           stream: bool = False) -> Dict[str, Any]:
        """
        Get adapter and call messages method.
        
        Args:
            request_data: Request payload
            request_headers: Request headers
            stream: Whether to stream response
            
        Returns:
            Response data
        """
        adapter = await self._get_adapter()
        return await adapter.messages(request_data, request_headers, stream=stream)
    
    async def _get_adapter_and_stream_messages(self, request_data: Dict[str, Any], 
                                             request_headers: Dict[str, str]):
        """
        Get adapter and stream messages.
        
        Args:
            request_data: Request payload
            request_headers: Request headers
            
        Returns:
            Async generator for streaming
        """
        adapter = await self._get_adapter()
        return await adapter.messages(request_data, request_headers, stream=True)
    
    def _health_endpoint(self) -> Union[Response, Tuple[Response, int]]:
        """
        Health check endpoint for Anthropic native router.
        
        Returns:
            Dict: Health status and configuration info
        """
        try:
            # Basic health check without calling external APIs
            return jsonify({
                'status': 'healthy',
                'service': 'anthropic-native-router',
                'version': '1.0.0',
                'endpoints': {
                    'messages': f"{self.url_prefix}/v1/messages",
                    'count_tokens': f"{self.url_prefix}/v1/messages/count_tokens",
                    'models': f"{self.url_prefix}/v1/models",
                    'health': f"{self.url_prefix}/health"
                }
            })
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 503
    
    def _error_handler(self, error: Exception) -> Tuple[Response, int]:
        """
        Global error handler for Anthropic native endpoints.
        
        Args:
            error: Exception that occurred
            
        Returns:
            Response: Error response in Anthropic format
        """
        logger.error(f"❌ AnthropicNativeRouter error: {error}")
        
        # Determine error type and status code
        if hasattr(error, 'code'):
            status_code = error.code
        else:
            status_code = 500
        
        return self._create_error_response(str(error), status_code)
    
    def _create_error_response(self, message: str, status_code: int = 500) -> Tuple[Response, int]:
        """
        Create standardized error response in Anthropic format.
        
        Args:
            message: Error message
            status_code: HTTP status code
            
        Returns:
            tuple: (error_response, status_code)
        """
        error_types = {
            400: 'invalid_request_error',
            401: 'authentication_error', 
            403: 'permission_error',
            404: 'not_found_error',
            429: 'rate_limit_error',
            500: 'api_error',
            502: 'api_error',
            503: 'overloaded_error'
        }
        
        error_response = {
            'type': 'error',
            'error': {
                'type': error_types.get(status_code, 'api_error'),
                'message': message
            }
        }
        
        return jsonify(error_response), status_code
    
    def _metrics_endpoint(self) -> Union[Response, Tuple[Response, int]]:
        """
        Performance metrics endpoint for monitoring adapter health and performance.
        
        Returns:
            Dict: Performance metrics including connection pool stats and request counts
        """
        try:
            # Get performance metrics asynchronously
            metrics = self._run_async(lambda: get_performance_metrics())
            
            # Add router-specific metrics
            router_metrics = {
                'router_status': 'healthy',
                'thread_pool_active': self._thread_pool._threads,
                'thread_pool_size': self._thread_pool._max_workers,
                'has_cached_loop': hasattr(self._loop_cache, 'loop')
            }
            
            # Combine adapter and router metrics
            response_data = {
                'timestamp': time.time(),
                'adapter_metrics': metrics,
                'router_metrics': router_metrics
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"❌ Metrics endpoint error: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }), 500
    
    def _count_tokens_endpoint(self) -> Union[Response, Tuple[Response, int]]:
        """
        Native Anthropic count tokens endpoint.
        
        Handles POST /anthropic/v1/messages/count_tokens with:
        - Native Anthropic request/response format
        - Error pass-through with original status codes
        """
        try:
            # Validate request content type
            if not request.is_json:
                return jsonify({
                    'type': 'error',
                    'error': {
                        'type': 'invalid_request_error',
                        'message': 'Content-Type must be application/json'
                    }
                }), 400
            
            request_data = request.get_json()
            if not request_data:
                return jsonify({
                    'type': 'error',
                    'error': {
                        'type': 'invalid_request_error',
                        'message': 'Request body must contain valid JSON'
                    }
                }), 400
            
            # Extract headers for upstream request
            request_headers = dict(request.headers)
            
            # Run async adapter call
            response_data = self._run_async(lambda: self._get_adapter_and_count_tokens(
                request_data, request_headers
            ))
            return jsonify(response_data)
                    
        except Exception as e:
            logger.error(f"❌ Error in count tokens endpoint: {e}")
            return self._create_error_response(str(e), 500)
    
    def _models_endpoint(self) -> Union[Response, Tuple[Response, int]]:
        """
        Native Anthropic models endpoint.
        
        Handles GET /anthropic/v1/models with:
        - Native Anthropic response format
        - Error pass-through with original status codes
        """
        try:
            # Extract headers for upstream request
            request_headers = dict(request.headers)
            
            # Run async adapter call
            response_data = self._run_async(lambda: self._get_adapter_and_list_models(
                request_headers
            ))
            return jsonify(response_data)
                    
        except Exception as e:
            logger.error(f"❌ Error in models endpoint: {e}")
            return self._create_error_response(str(e), 500)
    
    async def _get_adapter_and_count_tokens(self, request_data: Dict[str, Any], 
                                          request_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Get adapter and call count_tokens method.
        
        Args:
            request_data: Request payload
            request_headers: Request headers
            
        Returns:
            Response data
        """
        adapter = await self._get_adapter()
        return await adapter.count_tokens(request_data, request_headers)
    
    async def _get_adapter_and_list_models(self, request_headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Get adapter and call list_models method.
        
        Args:
            request_headers: Request headers
            
        Returns:
            Response data
        """
        adapter = await self._get_adapter()
        return await adapter.list_models(request_headers)


def create_anthropic_router(url_prefix: str = '/anthropic') -> Blueprint:
    """
    Factory function to create Anthropic native router blueprint.
    
    Args:
        url_prefix: URL prefix for Anthropic endpoints
        
    Returns:
        Blueprint: Configured Anthropic native blueprint
    """
    router = AnthropicNativeRouter(url_prefix)
    return router.create_blueprint()