#!/usr/bin/env python3
"""
Anthropic Compatibility Async Router
===================================

Quart-based async router providing Anthropic-compatible API endpoints that interface
with Salesforce backend infrastructure. Designed for enterprise-grade async performance
while maintaining exact API compatibility with Anthropic's message format.

Key Features:
- Async Quart Blueprint architecture with full async/await patterns
- Exact Anthropic API compliance: /v1/models, /v1/messages, /v1/messages/count_tokens
- SSE streaming with proper Anthropic event sequence (message_start → content_block_* → message_stop)
- Salesforce backend integration via AsyncSalesforceModelsClient
- Model mapping and verification with anthropic_models.map.json configuration
- Enterprise error handling with proper Anthropic error format
- Memory-efficient streaming with async generators

Endpoints:
- GET /v1/models - List verified Anthropic models
- POST /v1/messages - Message completion with streaming support
- POST /v1/messages/count_tokens - Token counting endpoint

Usage:
    from routers.anthropic_compat_async import create_anthropic_compat_router
    
    app.register_blueprint(create_anthropic_compat_router())
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from quart import Blueprint, request, jsonify, Response
from salesforce_models_client import AsyncSalesforceModelsClient
from compat_async.anthropic_mapper import (
    require_anthropic_headers, 
    map_messages_to_sf_async,
    map_sf_to_anthropic,
    sse_iter_from_sf_generation
)
from compat_async.model_map import get_verified_anthropic_models, verify_model_async
from compat_async.tokenizers import count_tokens_async

logger = logging.getLogger(__name__)

class AnthropicCompatAsyncRouter:
    """
    Async router for Anthropic-compatible API endpoints.
    
    Provides enterprise-grade async implementation of Anthropic API while integrating
    with existing Salesforce backend infrastructure and patterns.
    """
    
    def __init__(self, url_prefix: str = '/v1'):
        """
        Initialize the Anthropic compatibility async router.
        
        Args:
            url_prefix: URL prefix for Anthropic endpoints (default: /v1)
        """
        self.url_prefix = url_prefix
        logger.info(f"🔧 AnthropicCompatAsyncRouter configured with prefix: {url_prefix}")
    
    def create_blueprint(self) -> Blueprint:
        """
        Create Quart blueprint with Anthropic-compatible endpoints.
        
        Returns:
            Blueprint: Configured Quart blueprint with async endpoints
        """
        bp = Blueprint('anthropic_compat_async', __name__, url_prefix=self.url_prefix)
        
        # Register async endpoints
        bp.add_url_rule('/models', 'models', self._models_endpoint, methods=['GET'])
        bp.add_url_rule('/messages', 'messages', self._messages_endpoint, methods=['POST'])
        bp.add_url_rule('/messages/count_tokens', 'count_tokens', self._count_tokens_endpoint, methods=['POST'])
        
        # Register error handlers
        bp.errorhandler(Exception)(self._error_handler)
        
        logger.info("📋 AnthropicCompatAsyncRouter blueprint created with async endpoints")
        return bp
    
    async def _models_endpoint(self) -> Union[Response, tuple]:
        """
        List verified Anthropic models endpoint.
        
        Returns verified models that are available through the Salesforce backend
        based on the anthropic_models.map.json configuration.
        
        Returns:
            Response: JSON response with available Anthropic models
        """
        request_start_time = time.time()
        
        try:
            # Require anthropic-version header
            await require_anthropic_headers(request.headers)
            
            # Get verified models from configuration and Salesforce backend
            models = await get_verified_anthropic_models()
            
            # Format response in Anthropic API format
            response_data = {
                "data": models,
                "has_more": False,
                "first_id": models[0]["id"] if models else None,
                "last_id": models[-1]["id"] if models else None
            }
            
            proxy_latency = (time.time() - request_start_time) * 1000
            response = jsonify(response_data)
            response.headers['x-proxy-latency-ms'] = str(int(proxy_latency))
            return response
            
        except ValueError as e:
            # Anthropic-version header missing or invalid
            return await self._create_error_response(str(e), 400, "invalid_request_error")
        except Exception as e:
            logger.error(f"❌ Error in models endpoint: {e}")
            return await self._create_error_response(str(e), 500, "api_error")
    
    async def _messages_endpoint(self) -> Union[Response, tuple]:
        """
        Anthropic messages completion endpoint with streaming support.
        
        Handles message completion requests with exact Anthropic API compliance
        including proper SSE event sequence for streaming responses.
        
        Returns:
            Response: JSON response or SSE streaming response
        """
        request_start_time = time.time()
        
        try:
            # Require anthropic-version header
            await require_anthropic_headers(request.headers)
            
            # Validate and parse request
            if not request.is_json:
                return await self._create_error_response(
                    "Content-Type must be application/json", 400, "invalid_request_error"
                )
            
            request_data = await request.get_json()
            if not request_data:
                return await self._create_error_response(
                    "Request body must contain valid JSON", 400, "invalid_request_error"
                )
            
            # Extract parameters with validation
            messages = request_data.get('messages', [])
            model = request_data.get('model')
            max_tokens = request_data.get('max_tokens', 1000)
            temperature = request_data.get('temperature', 0.7)
            stream = request_data.get('stream', False)
            system = request_data.get('system')
            tools = request_data.get('tools')
            tool_choice = request_data.get('tool_choice')
            
            # Validate required parameters
            if not model:
                return await self._create_error_response(
                    "Missing required parameter: model", 400, "invalid_request_error"
                )
            
            if not messages:
                return await self._create_error_response(
                    "Missing required parameter: messages", 400, "invalid_request_error"
                )
            
            # Verify model availability
            if not await verify_model_async(model):
                return await self._create_error_response(
                    f"Model '{model}' is not available", 400, "invalid_request_error"
                )
            
            # Convert Anthropic format to Salesforce format
            sf_request = await map_messages_to_sf_async(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                tools=tools,
                tool_choice=tool_choice
            )
            
            # Get async Salesforce client
            from async_endpoint_server import get_async_client
            client = await get_async_client()
            
            # Make API call to Salesforce backend
            sf_response = await client._async_chat_completion(**sf_request)
            
            if stream:
                # Return SSE streaming response
                return await self._create_streaming_response(
                    sf_response, model, request_start_time
                )
            else:
                # Convert Salesforce response to Anthropic format
                anthropic_response = await map_sf_to_anthropic(
                    sf_response, model, messages
                )
                
                proxy_latency = (time.time() - request_start_time) * 1000
                response = jsonify(anthropic_response)
                response.headers['x-proxy-latency-ms'] = str(int(proxy_latency))
                return response
            
        except ValueError as e:
            # Anthropic-version header or validation error
            return await self._create_error_response(str(e), 400, "invalid_request_error")
        except Exception as e:
            logger.error(f"❌ Error in messages endpoint: {e}")
            return await self._create_error_response(str(e), 500, "api_error")
    
    async def _count_tokens_endpoint(self) -> Union[Response, tuple]:
        """
        Token counting endpoint for Anthropic messages.
        
        Provides token estimation for Anthropic message format with system messages,
        user messages, and tool definitions support.
        
        Returns:
            Response: JSON response with token counts
        """
        request_start_time = time.time()
        
        try:
            # Require anthropic-version header
            await require_anthropic_headers(request.headers)
            
            # Validate and parse request
            if not request.is_json:
                return await self._create_error_response(
                    "Content-Type must be application/json", 400, "invalid_request_error"
                )
            
            request_data = await request.get_json()
            if not request_data:
                return await self._create_error_response(
                    "Request body must contain valid JSON", 400, "invalid_request_error"
                )
            
            # Extract parameters
            messages = request_data.get('messages', [])
            model = request_data.get('model')
            system = request_data.get('system')
            tools = request_data.get('tools')
            
            # Validate required parameters
            if not model:
                return await self._create_error_response(
                    "Missing required parameter: model", 400, "invalid_request_error"
                )
            
            # Verify model availability
            if not await verify_model_async(model):
                return await self._create_error_response(
                    f"Model '{model}' is not available", 400, "invalid_request_error"
                )
            
            # Count tokens asynchronously
            token_count = await count_tokens_async(
                messages=messages,
                system=system,
                tools=tools
            )
            
            # Format response in Anthropic format
            response_data = {
                "input_tokens": token_count
            }
            
            proxy_latency = (time.time() - request_start_time) * 1000
            response = jsonify(response_data)
            response.headers['x-proxy-latency-ms'] = str(int(proxy_latency))
            return response
            
        except ValueError as e:
            return await self._create_error_response(str(e), 400, "invalid_request_error")
        except Exception as e:
            logger.error(f"❌ Error in count tokens endpoint: {e}")
            return await self._create_error_response(str(e), 500, "api_error")
    
    async def _create_streaming_response(self, sf_response: Dict[str, Any], 
                                       model: str, request_start_time: float) -> Response:
        """
        Create SSE streaming response with proper Anthropic event sequence.
        
        Implements the exact Anthropic SSE specification:
        - message_start event
        - content_block_start event  
        - content_block_delta events (streaming text)
        - content_block_stop event
        - message_delta event
        - message_stop event
        
        Args:
            sf_response: Salesforce API response
            model: Model name for response
            request_start_time: Request start time for performance tracking
            
        Returns:
            Response: Quart streaming response with SSE format
        """
        async def anthropic_stream_generator() -> AsyncGenerator[str, None]:
            try:
                # Generate SSE events using the async generator
                async for event in sse_iter_from_sf_generation(sf_response, model):
                    yield event
                    await asyncio.sleep(0.01)  # Small async delay for streaming effect
                
                # Track performance
                proxy_latency = (time.time() - request_start_time) * 1000
                logger.debug(f"⚡ Anthropic streaming completed in {proxy_latency:.1f}ms")
                
            except Exception as e:
                logger.error(f"❌ Error in Anthropic streaming: {e}")
                # Send error event in Anthropic format
                error_data = {
                    "type": "error",
                    "error": {
                        "type": "api_error",
                        "message": str(e)
                    }
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        
        return Response(
            anthropic_stream_generator(),
            mimetype='text/plain; charset=utf-8',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, anthropic-version',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'X-Accel-Buffering': 'no'
            }
        )
    
    async def _create_error_response(self, message: str, status_code: int = 500, 
                                   error_type: str = "api_error") -> tuple:
        """
        Create standardized error response in Anthropic format.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_type: Anthropic error type
            
        Returns:
            tuple: (error_response, status_code)
        """
        error_response = {
            "type": "error",
            "error": {
                "type": error_type,
                "message": message
            }
        }
        
        response = jsonify(error_response)
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response, status_code
    
    async def _error_handler(self, error: Exception) -> tuple:
        """
        Global error handler for Anthropic compatibility endpoints.
        
        Args:
            error: Exception that occurred
            
        Returns:
            tuple: Error response in Anthropic format
        """
        logger.error(f"❌ AnthropicCompatAsyncRouter error: {error}")
        
        # Determine error type and status code
        if hasattr(error, 'code'):
            status_code = error.code
        else:
            status_code = 500
        
        return await self._create_error_response(str(error), status_code)


def create_anthropic_compat_router(url_prefix: str = '/v1') -> Blueprint:
    """
    Factory function to create Anthropic compatibility async router blueprint.
    
    Args:
        url_prefix: URL prefix for Anthropic endpoints (default: /v1)
        
    Returns:
        Blueprint: Configured Anthropic compatibility async blueprint
    """
    router = AnthropicCompatAsyncRouter(url_prefix)
    return router.create_blueprint()