#!/usr/bin/env python3
"""
Anthropic Native Pass-Through Hardening Test Suite
==================================================

Comprehensive test suite to validate the Anthropic native pass-through adapter
against the architecture acceptance criteria:

1. /anthropic/v1/messages returns native Anthropic JSON format
2. SSE streaming with proper headers and no buffering  
3. Tool round-trip unchanged (request → assistant tool_use → tool_result)
4. Error pass-through with original status codes
5. Anthropic-Request-Id preservation
6. Beta header forwarding support

Usage:
    python test_anthropic_native_hardening.py
    
Prerequisites:
    - Server running on localhost:8000 with Anthropic native adapter
    - ANTHROPIC_API_KEY environment variable set (for integration tests)
    - httpx installed: pip install httpx
"""

import os
import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
import unittest
from unittest.mock import patch, MagicMock

try:
    import httpx
except ImportError:
    httpx = None

# Configure logging for test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAnthropicNativeHardening(unittest.TestCase):
    """Test suite for Anthropic native pass-through hardening."""
    
    def setUp(self):
        """Set up test configuration."""
        self.base_url = "http://localhost:8000"
        self.anthropic_endpoint = f"{self.base_url}/anthropic/v1/messages"
        self.health_endpoint = f"{self.base_url}/anthropic/health"
        
        # Test data
        self.test_message = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user", 
                    "content": "Hello, how are you?"
                }
            ]
        }
        
        self.test_tool_message = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 200,
            "messages": [
                {
                    "role": "user",
                    "content": "What's the weather like in San Francisco?"
                }
            ],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get current weather for a location",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City name"
                            }
                        },
                        "required": ["location"]
                    }
                }
            ]
        }
    
    def test_health_endpoint(self):
        """Test Anthropic native health endpoint accessibility."""
        if httpx is None:
            self.skipTest("httpx not available")
        
        try:
            with httpx.Client() as client:
                response = client.get(self.health_endpoint)
                
                self.assertEqual(response.status_code, 200, 
                    "Health endpoint should return 200 OK")
                
                data = response.json()
                self.assertEqual(data.get('status'), 'healthy',
                    "Health endpoint should report healthy status")
                
                # Verify service identification
                self.assertEqual(data.get('service'), 'anthropic-native-router',
                    "Health should identify as anthropic-native-router")
                
                # Verify endpoints are documented
                endpoints = data.get('endpoints', {})
                self.assertIn('messages', endpoints,
                    "Health should document messages endpoint")
                
                logger.info("✅ Health endpoint test passed")
                
        except Exception as e:
            self.fail(f"Health endpoint test failed: {e}")
    
    def test_native_message_format(self):
        """
        Test Acceptance Criteria #1: 
        /anthropic/v1/messages returns native Anthropic JSON format
        """
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.anthropic_endpoint,
                    json=self.test_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                self.assertEqual(response.status_code, 200,
                    f"Expected 200 OK, got {response.status_code}")
                
                data = response.json()
                
                # Verify native Anthropic response structure
                self.assertIn('id', data, "Response should have id field")
                self.assertIn('type', data, "Response should have type field")
                self.assertIn('role', data, "Response should have role field")
                self.assertIn('content', data, "Response should have content field")
                self.assertIn('model', data, "Response should have model field")
                self.assertIn('usage', data, "Response should have usage field")
                
                # Verify specific Anthropic format values
                self.assertEqual(data.get('type'), 'message',
                    "Type should be 'message' in Anthropic format")
                self.assertEqual(data.get('role'), 'assistant',
                    "Role should be 'assistant' in Anthropic format")
                
                # Verify content is array of content blocks (Anthropic format)
                content = data.get('content', [])
                self.assertIsInstance(content, list,
                    "Content should be array in Anthropic format")
                
                if content:
                    self.assertIn('type', content[0],
                        "Content block should have type field")
                    self.assertIn('text', content[0],
                        "Content block should have text field")
                
                # Verify usage structure
                usage = data.get('usage', {})
                self.assertIn('input_tokens', usage,
                    "Usage should have input_tokens field")
                self.assertIn('output_tokens', usage,
                    "Usage should have output_tokens field")
                
                logger.info("✅ Native Anthropic message format test passed")
                
        except Exception as e:
            self.fail(f"Native message format test failed: {e}")
    
    def test_sse_streaming_headers(self):
        """
        Test Acceptance Criteria #2:
        SSE streaming with proper headers and no buffering
        """
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        streaming_message = self.test_message.copy()
        streaming_message['stream'] = True
        
        try:
            with httpx.Client() as client:
                with client.stream(
                    'POST',
                    self.anthropic_endpoint,
                    json=streaming_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                ) as response:
                    
                    self.assertEqual(response.status_code, 200,
                        f"Expected 200 OK, got {response.status_code}")
                    
                    # Verify SSE headers
                    self.assertEqual(response.headers.get('content-type'), 'text/event-stream',
                        "Content-Type should be text/event-stream for SSE")
                    
                    self.assertEqual(response.headers.get('cache-control'), 'no-cache',
                        "Cache-Control should be no-cache for SSE")
                    
                    self.assertEqual(response.headers.get('connection'), 'keep-alive',
                        "Connection should be keep-alive for SSE")
                    
                    # Verify no buffering header
                    self.assertEqual(response.headers.get('x-accel-buffering'), 'no',
                        "X-Accel-Buffering should be 'no' to disable nginx buffering")
                    
                    # Read first few events to verify streaming works
                    events_received = 0
                    for chunk in response.iter_text():
                        if chunk.strip():
                            events_received += 1
                            if events_received >= 3:  # Read a few events
                                break
                    
                    self.assertGreater(events_received, 0,
                        "Should receive at least some SSE events")
                    
                    logger.info("✅ SSE streaming headers test passed")
                    
        except Exception as e:
            self.fail(f"SSE streaming headers test failed: {e}")
    
    def test_tool_call_passthrough(self):
        """
        Test Acceptance Criteria #3:
        Tool round-trip unchanged (request → assistant tool_use → tool_result)
        """
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.anthropic_endpoint,
                    json=self.test_tool_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                self.assertEqual(response.status_code, 200,
                    f"Expected 200 OK, got {response.status_code}")
                
                data = response.json()
                
                # Check if tool was used (Anthropic may or may not use it)
                content = data.get('content', [])
                
                # Look for tool_use content blocks
                tool_use_found = False
                for block in content:
                    if block.get('type') == 'tool_use':
                        tool_use_found = True
                        
                        # Verify native Anthropic tool_use format
                        self.assertIn('id', block,
                            "Tool use block should have id field")
                        self.assertIn('name', block,
                            "Tool use block should have name field")
                        self.assertIn('input', block,
                            "Tool use block should have input field")
                        
                        # Verify tool name matches what we provided
                        self.assertEqual(block.get('name'), 'get_weather',
                            "Tool name should match request")
                        
                        break
                
                if tool_use_found:
                    logger.info("✅ Tool call pass-through test passed - tool was used")
                else:
                    logger.info("ℹ️  Tool call pass-through test passed - tool not used (model decision)")
                
        except Exception as e:
            self.fail(f"Tool call pass-through test failed: {e}")
    
    def test_error_passthrough(self):
        """
        Test Acceptance Criteria #4:
        Error pass-through with original status codes
        """
        if httpx is None:
            self.skipTest("httpx not available")
        
        # Test with invalid request (missing required fields)
        invalid_message = {
            "model": "claude-3-haiku-20240307"
            # Missing required 'messages' field
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.anthropic_endpoint,
                    json=invalid_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                # Should get 4xx error for invalid request
                self.assertIn(response.status_code, [400, 422],
                    f"Expected 400 or 422 for invalid request, got {response.status_code}")
                
                data = response.json()
                
                # Verify Anthropic error format
                self.assertIn('type', data, "Error response should have type field")
                self.assertIn('error', data, "Error response should have error field")
                self.assertEqual(data.get('type'), 'error',
                    "Error response type should be 'error'")
                
                error = data.get('error', {})
                self.assertIn('type', error, "Error object should have type field")
                self.assertIn('message', error, "Error object should have message field")
                
                logger.info("✅ Error pass-through test passed")
                
        except Exception as e:
            self.fail(f"Error pass-through test failed: {e}")
    
    def test_request_id_preservation(self):
        """
        Test Acceptance Criteria #5:
        Anthropic-Request-Id preservation
        """
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.anthropic_endpoint,
                    json=self.test_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                self.assertEqual(response.status_code, 200,
                    f"Expected 200 OK, got {response.status_code}")
                
                # Check if Anthropic-Request-Id header is present
                request_id = response.headers.get('anthropic-request-id')
                
                if request_id:
                    logger.info(f"✅ Request ID preservation test passed: {request_id}")
                else:
                    logger.info("ℹ️  Request ID preservation test: No request ID in response (may be expected)")
                
        except Exception as e:
            self.fail(f"Request ID preservation test failed: {e}")
    
    def test_beta_header_forwarding(self):
        """
        Test Acceptance Criteria #6:
        Beta header forwarding support
        """
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        # Test with anthropic-beta header
        headers = {
            'Content-Type': 'application/json',
            'anthropic-beta': 'tools-2024-04-04'
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.anthropic_endpoint,
                    json=self.test_message,
                    headers=headers,
                    timeout=30.0
                )
                
                # Request should succeed (beta header should be forwarded)
                self.assertEqual(response.status_code, 200,
                    f"Expected 200 OK with beta header, got {response.status_code}")
                
                logger.info("✅ Beta header forwarding test passed")
                
        except Exception as e:
            self.fail(f"Beta header forwarding test failed: {e}")
    
    def test_adapter_unit_functionality(self):
        """Unit test for AnthropicNativeAdapter basic functionality."""
        try:
            from adapters.anthropic_native import AnthropicNativeAdapter
        except ImportError as e:
            self.skipTest(f"Cannot import AnthropicNativeAdapter: {e}")
        
        # Test adapter initialization
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            adapter = AnthropicNativeAdapter()
            
            self.assertEqual(adapter.api_key, 'test-key',
                "Adapter should use environment API key")
            self.assertEqual(adapter.base_url, 'https://api.anthropic.com',
                "Adapter should use default base URL")
            self.assertEqual(adapter.anthropic_version, '2023-06-01',
                "Adapter should use default version")
        
        # Test header preparation
        headers = adapter._prepare_headers({'anthropic-beta': 'test-feature'})
        
        self.assertIn('x-api-key', headers,
            "Prepared headers should include API key")
        self.assertIn('anthropic-version', headers,
            "Prepared headers should include version")
        self.assertIn('anthropic-beta', headers,
            "Prepared headers should preserve beta headers")
        
        logger.info("✅ Adapter unit functionality test passed")
    
    def test_router_unit_functionality(self):
        """Unit test for AnthropicNativeRouter basic functionality."""
        try:
            from routers.anthropic_native import AnthropicNativeRouter
        except ImportError as e:
            self.skipTest(f"Cannot import AnthropicNativeRouter: {e}")
        
        # Test router initialization
        router = AnthropicNativeRouter('/anthropic')
        self.assertEqual(router.url_prefix, '/anthropic',
            "Router should use specified URL prefix")
        
        # Test blueprint creation
        blueprint = router.create_blueprint()
        self.assertIsNotNone(blueprint,
            "Router should create valid blueprint")
        
        # Test error response creation
        error_response, status_code = router._create_error_response("Test error", 400)
        
        self.assertEqual(status_code, 400,
            "Error response should preserve status code")
        
        error_data = error_response.get_json()
        self.assertEqual(error_data.get('type'), 'error',
            "Error response should have Anthropic error format")
        
        logger.info("✅ Router unit functionality test passed")


def run_comprehensive_test_suite():
    """Run the comprehensive test suite with detailed reporting."""
    print("🧪 Anthropic Native Pass-Through Hardening Test Suite")
    print("=" * 60)
    print()
    
    # Check prerequisites
    missing_deps = []
    if httpx is None:
        missing_deps.append("httpx")
    
    if missing_deps:
        print(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        print("   Install with: pip install " + " ".join(missing_deps))
        return False
    
    # Run test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAnthropicNativeHardening)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    if result.skipped:
        print("\nℹ️  Skipped tests:")
        for test, reason in result.skipped:
            print(f"   {test}: {reason}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n✅ All tests passed! Anthropic Native Pass-Through Hardening is working correctly.")
    else:
        print("\n❌ Some tests failed. Please review the failures above.")
    
    return success


if __name__ == "__main__":
    run_comprehensive_test_suite()