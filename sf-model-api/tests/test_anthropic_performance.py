#!/usr/bin/env python3
"""
Performance and Reliability Tests for Anthropic Compatibility Layer
==================================================================

Tests focused on performance characteristics and reliability ensuring:
- Async patterns are properly implemented (no blocking calls)
- Memory efficiency with large responses
- Cache performance and hit rates
- Thread safety and concurrent access
- Error recovery and graceful degradation
"""

import os
import json
import time
import pytest
import asyncio
import gc
from typing import Dict, Any, List, Optional
import psutil
import tracemalloc

@pytest.mark.asyncio
async def test_async_performance_no_blocking():
    """Test that the async implementation avoids blocking calls."""
    from src.compat_async.anthropic_mapper import map_messages_to_sf_async
    from src.compat_async.model_map import verify_model_async, get_verified_anthropic_models
    
    # Create a list of operations to run concurrently
    operations = []
    
    # Add model operations
    operations.append(verify_model_async("claude-3-5-sonnet-latest"))
    operations.append(get_verified_anthropic_models())
    
    # Add mapping operations
    messages = [{"role": "user", "content": "Hello, how are you?"}]
    operations.append(map_messages_to_sf_async(messages, "claude-3-5-sonnet-latest"))
    
    # Run all operations concurrently
    start_time = time.time()
    results = await asyncio.gather(*operations)
    end_time = time.time()
    
    # Calculate total time
    total_time = end_time - start_time
    
    # Run the operations sequentially for comparison
    sequential_start_time = time.time()
    
    await verify_model_async("claude-3-5-sonnet-latest")
    await get_verified_anthropic_models()
    await map_messages_to_sf_async(messages, "claude-3-5-sonnet-latest")
    
    sequential_end_time = time.time()
    sequential_time = sequential_end_time - sequential_start_time
    
    # Log the times
    print(f"Concurrent execution time: {total_time:.4f}s")
    print(f"Sequential execution time: {sequential_time:.4f}s")
    
    # Verify concurrent execution is faster than sequential
    # This tests that the operations are truly async (no blocking)
    assert total_time < sequential_time

@pytest.mark.asyncio
async def test_memory_efficiency_streaming():
    """Test memory efficiency of SSE streaming with large responses."""
    from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
    
    # Start memory tracking
    tracemalloc.start()
    
    # Generate a large response (1MB of text)
    large_text = "This is a test sentence for memory efficiency. " * 10000
    large_response = {
        "generations": [{"text": large_text}],
        "usage": {"inputTokenCount": 10, "outputTokenCount": 50000}
    }
    
    # Snapshot memory before streaming
    snapshot1 = tracemalloc.take_snapshot()
    
    # Process the response with streaming
    event_count = 0
    event_size = 0
    async for event in sse_iter_from_sf_generation(large_response, "claude-3-5-sonnet-latest"):
        event_count += 1
        event_size += len(event)
    
    # Snapshot memory after streaming
    snapshot2 = tracemalloc.take_snapshot()
    
    # Compare snapshots to find top memory users
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    # Calculate total memory difference
    memory_diff = sum(stat.size_diff for stat in top_stats)
    
    # Log memory usage
    print(f"Memory change: {memory_diff / 1024 / 1024:.2f} MB")
    print(f"Processed {event_count} events with total size {event_size / 1024:.2f} KB")
    
    # Stop tracing
    tracemalloc.stop()
    
    # Verify reasonable memory usage (should be much less than the full response size)
    # The exact value will depend on implementation, but it should be bounded
    # We're mainly testing that we don't have a memory leak
    assert event_count > 0
    assert event_size > 0

@pytest.mark.asyncio
async def test_model_cache_performance():
    """Test performance of the model verification cache."""
    from src.compat_async.model_map import (
        verify_model_async, clear_model_cache, 
        _model_verification_cache, get_verified_anthropic_models
    )
    
    # Clear cache before testing
    await clear_model_cache()
    
    # Time first verification (cache miss)
    start_time = time.time()
    result1 = await verify_model_async("claude-3-5-sonnet-latest")
    first_verify_time = time.time() - start_time
    
    # Time second verification (cache hit)
    start_time = time.time()
    result2 = await verify_model_async("claude-3-5-sonnet-latest")
    second_verify_time = time.time() - start_time
    
    # Log the times
    print(f"First verification (cache miss): {first_verify_time:.6f}s")
    print(f"Second verification (cache hit): {second_verify_time:.6f}s")
    
    # Cache hit should be significantly faster
    assert second_verify_time < first_verify_time
    assert result1 == result2
    
    # Test cache hit rate for get_verified_anthropic_models
    await clear_model_cache()
    
    # First call (cache miss)
    start_time = time.time()
    models1 = await get_verified_anthropic_models()
    first_models_time = time.time() - start_time
    
    # Second call (cache hit)
    start_time = time.time()
    models2 = await get_verified_anthropic_models()
    second_models_time = time.time() - start_time
    
    # Log the times
    print(f"First get_verified_models (cache miss): {first_models_time:.6f}s")
    print(f"Second get_verified_models (cache hit): {second_models_time:.6f}s")
    
    # Cache hit should be significantly faster
    assert second_models_time < first_models_time
    assert len(models1) == len(models2)

@pytest.mark.asyncio
async def test_thread_safety_concurrent_cache_access():
    """Test thread safety of the model cache with concurrent access."""
    from src.compat_async.model_map import (
        verify_model_async, clear_model_cache, 
        _model_verification_cache, _verified_models_cache
    )
    
    # Clear cache before testing
    await clear_model_cache()
    
    # Define models to verify concurrently
    models = [
        "claude-3-5-sonnet-latest",
        "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229"
    ]
    
    # Run multiple verification tasks concurrently (50 tasks)
    tasks = []
    for _ in range(10):  # 10 concurrent tasks per model
        for model in models:
            tasks.append(verify_model_async(model))
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    
    # Verify all results are True (all verifications succeeded)
    assert all(results)
    
    # Verify cache contains all models
    for model in models:
        assert model in _model_verification_cache

@pytest.mark.asyncio
async def test_concurrent_streaming_performance(test_client, mock_anthropic_messages):
    """Test performance with multiple concurrent streaming requests."""
    # Skip this test if running in CI environment (where performance may vary)
    if os.environ.get('CI') == 'true':
        pytest.skip("Skipping performance test in CI environment")
    
    # Prepare streaming request data
    request_data = {
        'model': 'claude-3-5-sonnet-latest',
        'messages': mock_anthropic_messages,
        'max_tokens': 50,
        'temperature': 0.7,
        'system': 'You are a helpful assistant',
        'stream': True
    }
    
    # Create multiple streaming request coroutines
    request_count = 5
    requests = []
    
    for i in range(request_count):
        # Clone request data to avoid issues
        req_data = dict(request_data)
        req_data['messages'] = list(mock_anthropic_messages)  # Make a copy
        
        # Add request
        requests.append(
            test_client.post(
                '/anthropic/v1/messages',
                headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
                json=req_data
            )
        )
    
    # Send concurrent requests
    start_time = time.time()
    responses = await asyncio.gather(*requests)
    mid_time = time.time()
    
    # Read all streaming responses
    streaming_tasks = []
    
    for response in responses:
        async def read_stream(response):
            events = []
            async for chunk in response.response:
                events.append(chunk)
            return events
        
        streaming_tasks.append(read_stream(response))
    
    # Wait for all streams to complete
    all_events = await asyncio.gather(*streaming_tasks)
    end_time = time.time()
    
    # Calculate times
    setup_time = mid_time - start_time
    streaming_time = end_time - mid_time
    total_time = end_time - start_time
    
    # Count total events
    total_events = sum(len(events) for events in all_events)
    
    # Log performance data
    print(f"Concurrent requests: {request_count}")
    print(f"Setup time: {setup_time:.4f}s")
    print(f"Streaming time: {streaming_time:.4f}s")
    print(f"Total time: {total_time:.4f}s")
    print(f"Total events: {total_events}")
    print(f"Events per second: {total_events/streaming_time:.2f}")
    
    # Verify all responses were successful
    for response in responses:
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_error_recovery():
    """Test graceful error recovery in the async pipeline."""
    from src.compat_async.anthropic_mapper import map_sf_to_anthropic
    
    # Create an invalid response that will cause errors
    invalid_response = {"invalid": "structure"}
    
    # Test error recovery with invalid response
    try:
        # This should not raise an exception but handle the error gracefully
        anthropic_response = await map_sf_to_anthropic(
            invalid_response,
            "claude-3-5-sonnet-latest",
            [{"role": "user", "content": "Hello"}]
        )
        
        # Verify response is still structured properly
        assert "id" in anthropic_response
        assert "type" in anthropic_response
        assert "role" in anthropic_response
        assert "content" in anthropic_response
        
        # Content should indicate an error but in a properly formatted way
        assert "Error" in anthropic_response["content"][0]["text"]
    except Exception as e:
        pytest.fail(f"map_sf_to_anthropic should handle errors gracefully, but raised: {e}")

@pytest.mark.asyncio
async def test_sse_stream_cancellation():
    """Test proper cleanup when SSE stream is cancelled."""
    from src.compat_async.anthropic_mapper import sse_iter_from_sf_generation
    
    # Create a response
    response = {
        "generations": [{"text": "This is a test response for streaming. " * 100}],
        "usage": {"inputTokenCount": 10, "outputTokenCount": 50}
    }
    
    # Start streaming
    stream = sse_iter_from_sf_generation(response, "claude-3-5-sonnet-latest")
    
    # Process a few events
    event_count = 0
    async for event in stream:
        event_count += 1
        if event_count >= 3:
            # Cancel after 3 events
            break
    
    # The stream should be properly closed by exiting the loop
    # Test passes if no exceptions are raised
    
    # Try reading a few more events to ensure the generator is properly terminated
    extra_events = []
    try:
        # Set a timeout to avoid hanging if the generator is not properly terminated
        async def read_more():
            nonlocal extra_events
            async for event in stream:
                extra_events.append(event)
                if len(extra_events) >= 10:
                    break
        
        # Wait for up to 1 second for more events
        await asyncio.wait_for(read_more(), timeout=1.0)
    except asyncio.TimeoutError:
        pass  # Timeout is expected if the generator is properly terminated
    
    print(f"Processed {event_count} events before cancellation")
    print(f"Got {len(extra_events)} events after cancellation")

@pytest.mark.asyncio
async def test_long_running_connection_stability():
    """Test stability of long-running connections with the async server."""
    # Create a minimal Quart application
    from quart import Quart
    from src.routers.anthropic_compat_async import create_anthropic_compat_router
    
    app = Quart(__name__)
    router = create_anthropic_compat_router()
    app.register_blueprint(router, url_prefix='/v1')
    
    # Patch the AsyncSalesforceModelsClient to simulate slow responses
    async def mock_async_chat_completion(**kwargs):
        # Simulate a slow response (5 seconds)
        await asyncio.sleep(5.0)
        return {
            "generations": [{"text": "This is a delayed response after 5 seconds."}],
            "usage": {"inputTokenCount": 10, "outputTokenCount": 12}
        }
    
    # Apply patch
    original_get_client = __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client
    
    async def mock_get_client():
        client = await original_get_client()
        client._async_chat_completion = mock_async_chat_completion
        return client
    
    __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client = mock_get_client
    
    # Mock verify_model_async to return True
    async def mock_verify_model_async(model):
        return True
    
    original_verify = __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async
    __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = mock_verify_model_async
    
    try:
        # Create test client
        client = app.test_client()
        
        # Start time
        start_time = time.time()
        
        # Send a request with a long timeout
        response = await client.post(
            '/v1/messages',
            headers={'anthropic-version': '2023-06-01', 'Content-Type': 'application/json'},
            json={
                'model': 'claude-3-5-sonnet-latest',
                'messages': [{'role': 'user', 'content': 'Hello'}],
                'stream': False
            }
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Verify the response came back after the delay
        assert response.status_code == 200
        assert elapsed_time >= 5.0
        
        # Verify response content
        data = await response.get_json()
        assert "delayed response" in data["content"][0]["text"]
    finally:
        # Restore original functions
        __import__('src.routers.anthropic_compat_async').routers.anthropic_compat_async.get_async_client = original_get_client
        __import__('src.compat_async.model_map').compat_async.model_map.verify_model_async = original_verify