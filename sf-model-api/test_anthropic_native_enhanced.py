#!/usr/bin/env python3
"""
Anthropic Native Enhanced Implementation Test Suite
==================================================

Test suite to validate the enhanced Anthropic native pass-through implementation
including all new features and improvements:

1. Enhanced error handling and resource management
2. Improved SSE streaming with proper async/sync compatibility
3. New endpoints: /anthropic/v1/messages/count_tokens and /anthropic/v1/models
4. Application lifecycle integration
5. Environment configuration validation
6. Production-ready code quality

Usage:
    python test_anthropic_native_enhanced.py
    
Prerequisites:
    - Enhanced Anthropic native adapter implementation
    - httpx installed: pip install httpx
"""

import os
import json
import time
import asyncio
import logging
import unittest
from unittest.mock import patch, MagicMock

try:
    import httpx
except ImportError:
    httpx = None

# Configure logging for test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAnthropicNativeEnhanced(unittest.TestCase):
    """Test suite for enhanced Anthropic native implementation."""
    
    def setUp(self):
        """Set up test configuration."""
        self.base_url = "http://localhost:8000"
        self.anthropic_endpoints = {
            'messages': f"{self.base_url}/anthropic/v1/messages",
            'count_tokens': f"{self.base_url}/anthropic/v1/messages/count_tokens",
            'models': f"{self.base_url}/anthropic/v1/models",
            'health': f"{self.base_url}/anthropic/health"
        }
        
        # Test data
        self.test_message = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user", 
                    "content": "Hello, enhanced implementation!"
                }
            ]
        }
        
        self.test_count_tokens_message = {
            "model": "claude-3-haiku-20240307",
            "messages": [
                {
                    "role": "user",
                    "content": "Count tokens in this message"
                }
            ]
        }
    
    def test_enhanced_adapter_unit_functionality(self):
        """Test enhanced AnthropicNativeAdapter functionality."""
        try:
            from adapters.anthropic_native import AnthropicNativeAdapter
        except ImportError as e:
            self.skipTest(f"Cannot import AnthropicNativeAdapter: {e}")
        
        # Test enhanced configuration validation
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'ANTHROPIC_TIMEOUT': '30.0',
            'ANTHROPIC_MAX_CONNECTIONS': '100',
            'ANTHROPIC_MAX_KEEPALIVE': '50'
        }):
            adapter = AnthropicNativeAdapter()
            
            self.assertEqual(adapter.api_key, 'test-key')
            self.assertEqual(adapter.timeout, 30.0)
            self.assertEqual(adapter.max_connections, 100)
            self.assertEqual(adapter.max_keepalive, 50)
        
        # Test configuration validation errors
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key', 'ANTHROPIC_TIMEOUT': '0'}):
            with self.assertRaises(ValueError):
                AnthropicNativeAdapter()
        
        # Test invalid base URL
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key', 'ANTHROPIC_BASE_URL': 'invalid-url'}):
            with self.assertRaises(ValueError):
                AnthropicNativeAdapter()
        
        logger.info("✅ Enhanced adapter unit functionality test passed")
    
    def test_enhanced_router_unit_functionality(self):
        """Test enhanced AnthropicNativeRouter functionality."""
        try:
            from routers.anthropic_native import AnthropicNativeRouter
        except ImportError as e:
            self.skipTest(f"Cannot import AnthropicNativeRouter: {e}")
        
        # Test router initialization
        router = AnthropicNativeRouter('/anthropic')
        self.assertEqual(router.url_prefix, '/anthropic')
        
        # Test enhanced blueprint creation with new endpoints
        blueprint = router.create_blueprint()
        self.assertIsNotNone(blueprint)
        
        # Verify all endpoints are registered
        rule_endpoints = [rule.endpoint for rule in blueprint.url_map.iter_rules()]
        expected_endpoints = ['messages', 'count_tokens', 'models', 'health']
        
        for endpoint in expected_endpoints:
            self.assertIn(f'anthropic_native.{endpoint}', rule_endpoints,
                         f"Endpoint {endpoint} should be registered")
        
        logger.info("✅ Enhanced router unit functionality test passed")
    
    def test_health_endpoint_enhanced(self):
        """Test enhanced health endpoint with new endpoint documentation."""
        if httpx is None:
            self.skipTest("httpx not available")
        
        try:
            with httpx.Client() as client:
                response = client.get(self.anthropic_endpoints['health'])
                
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertEqual(data.get('status'), 'healthy')
                self.assertEqual(data.get('service'), 'anthropic-native-router')
                
                # Verify all new endpoints are documented
                endpoints = data.get('endpoints', {})
                expected_endpoints = ['messages', 'count_tokens', 'models', 'health']
                
                for endpoint in expected_endpoints:
                    self.assertIn(endpoint, endpoints,
                                f"Health should document {endpoint} endpoint")
                
                logger.info("✅ Enhanced health endpoint test passed")
                
        except Exception as e:
            self.fail(f"Enhanced health endpoint test failed: {e}")
    
    def test_count_tokens_endpoint(self):
        """Test new count tokens endpoint."""
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.anthropic_endpoints['count_tokens'],
                    json=self.test_count_tokens_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                # Should either succeed or fail with proper error format
                if response.status_code == 200:
                    data = response.json()
                    # Verify it returns token count information
                    self.assertIn('input_tokens', data,
                                "Count tokens response should have input_tokens")
                    logger.info("✅ Count tokens endpoint test passed")
                else:
                    # Verify error format is correct
                    data = response.json()
                    self.assertIn('type', data)
                    self.assertIn('error', data)
                    logger.info("ℹ️  Count tokens endpoint returned expected error format")
                
        except Exception as e:
            self.fail(f"Count tokens endpoint test failed: {e}")
    
    def test_models_endpoint(self):
        """Test new models endpoint."""
        if httpx is None:
            self.skipTest("httpx not available")
        
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not set - skipping integration test")
        
        try:
            with httpx.Client() as client:
                response = client.get(
                    self.anthropic_endpoints['models'],
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                # Should either succeed or fail with proper error format
                if response.status_code == 200:
                    data = response.json()
                    # Verify it returns models information
                    self.assertIn('data', data,
                                "Models response should have data field")
                    logger.info("✅ Models endpoint test passed")
                else:
                    # Verify error format is correct
                    data = response.json()
                    self.assertIn('type', data)
                    self.assertIn('error', data)
                    logger.info("ℹ️  Models endpoint returned expected error format")
                
        except Exception as e:
            self.fail(f"Models endpoint test failed: {e}")
    
    def test_enhanced_sse_streaming(self):
        """Test enhanced SSE streaming implementation."""
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
                    self.anthropic_endpoints['messages'],
                    json=streaming_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                ) as response:
                    
                    self.assertEqual(response.status_code, 200)
                    
                    # Verify enhanced SSE headers
                    self.assertEqual(response.headers.get('content-type'), 'text/event-stream')
                    self.assertEqual(response.headers.get('cache-control'), 'no-cache')
                    self.assertEqual(response.headers.get('connection'), 'keep-alive')
                    self.assertEqual(response.headers.get('x-accel-buffering'), 'no')
                    
                    # Verify CORS headers are present
                    self.assertEqual(response.headers.get('access-control-allow-origin'), '*')
                    
                    # Read a few chunks to verify streaming works
                    chunk_count = 0
                    for chunk in response.iter_raw():
                        if chunk:
                            chunk_count += 1
                            if chunk_count >= 3:  # Read a few chunks
                                break
                    
                    self.assertGreater(chunk_count, 0,
                                     "Should receive streaming chunks")
                    
                    logger.info("✅ Enhanced SSE streaming test passed")
                    
        except Exception as e:
            self.fail(f"Enhanced SSE streaming test failed: {e}")
    
    def test_configuration_validation(self):
        """Test enhanced configuration validation."""
        try:
            from adapters.anthropic_native import AnthropicNativeAdapter
        except ImportError as e:
            self.skipTest(f"Cannot import AnthropicNativeAdapter: {e}")
        
        # Test valid configuration
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': 'test-key',
            'ANTHROPIC_BASE_URL': 'https://api.anthropic.com',
            'ANTHROPIC_TIMEOUT': '60.0',
            'ANTHROPIC_MAX_CONNECTIONS': '200',
            'ANTHROPIC_MAX_KEEPALIVE': '100'
        }):
            adapter = AnthropicNativeAdapter()
            self.assertIsNotNone(adapter)
        
        # Test configuration value validation
        test_cases = [
            ({'ANTHROPIC_TIMEOUT': '-1'}, ValueError),
            ({'ANTHROPIC_MAX_CONNECTIONS': '0'}, ValueError),
            ({'ANTHROPIC_MAX_KEEPALIVE': '-10'}, ValueError),
            ({'ANTHROPIC_BASE_URL': 'invalid-url'}, ValueError)
        ]
        
        for env_vars, expected_error in test_cases:
            env_patch = {'ANTHROPIC_API_KEY': 'test-key'}
            env_patch.update(env_vars)
            
            with patch.dict(os.environ, env_patch):
                with self.assertRaises(expected_error):
                    AnthropicNativeAdapter()
        
        logger.info("✅ Configuration validation test passed")
    
    def test_error_handling_enhancement(self):
        """Test enhanced error handling."""
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
                    self.anthropic_endpoints['messages'],
                    json=invalid_message,
                    headers={'Content-Type': 'application/json'},
                    timeout=30.0
                )
                
                # Should get error response
                self.assertIn(response.status_code, [400, 422])
                
                data = response.json()
                
                # Verify enhanced Anthropic error format
                self.assertIn('type', data)
                self.assertIn('error', data)
                self.assertEqual(data.get('type'), 'error')
                
                error = data.get('error', {})
                self.assertIn('type', error)
                self.assertIn('message', error)
                
                logger.info("✅ Enhanced error handling test passed")
                
        except Exception as e:
            self.fail(f"Enhanced error handling test failed: {e}")


def run_enhanced_test_suite():
    """Run the enhanced test suite with detailed reporting."""
    print("🧪 Anthropic Native Enhanced Implementation Test Suite")
    print("=" * 65)
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
    suite = loader.loadTestsFromTestCase(TestAnthropicNativeEnhanced)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 65)
    print("📊 Enhanced Test Results Summary:")
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
        print("\n✅ All enhanced tests passed! Implementation is production-ready.")
    else:
        print("\n❌ Some tests failed. Please review the failures above.")
    
    return success


if __name__ == "__main__":
    run_enhanced_test_suite()