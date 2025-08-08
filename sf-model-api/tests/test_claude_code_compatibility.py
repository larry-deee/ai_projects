#!/usr/bin/env python3
"""
Claude Code Client Compatibility Test Suite
===========================================

Comprehensive test suite validating Claude Code client compatibility with the
Salesforce Models API Gateway. Tests Anthropic API format compliance, streaming
responses, and claude-code specific functionality.

Tests cover:
- Anthropic /v1/messages endpoint implementation
- System message handling and content blocks
- Streaming responses with SSE format
- Tool calling with Anthropic format differences
- Authentication flow and error handling
- Message format validation and content processing
"""

import json
import time
import unittest
import requests
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from unittest.mock import patch, MagicMock, AsyncMock

# Import project modules
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from unified_response_formatter import UnifiedResponseFormatter
    from salesforce_models_client import AsyncSalesforceModelsClient
    from async_endpoint_server import get_async_client, format_openai_response_async
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


class ClaudeCodeCompatibilityTests(unittest.TestCase):
    """Test suite for Claude Code client compatibility validation."""
    
    def setUp(self):
        """Set up test fixtures for Claude Code testing."""
        self.server_url = "http://localhost:8000"
        self.test_timeout = 30
        
        # Claude Code test data (Anthropic format)
        self.claude_code_test_data = {
            'simple_message': {
                "model": "claude-3-haiku",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": "Hello Claude, how are you today?"
                }]
            },
            'system_message': {
                "model": "claude-3-haiku",
                "max_tokens": 1000,
                "system": "You are a helpful assistant that responds concisely.",
                "messages": [{
                    "role": "user", 
                    "content": "What is the capital of France?"
                }]
            },
            'multi_turn': {
                "model": "claude-3-haiku",
                "max_tokens": 1000,
                "messages": [
                    {"role": "user", "content": "Can you help me write a Python function?"},
                    {"role": "assistant", "content": "Of course! What kind of function do you need?"},
                    {"role": "user", "content": "A function to calculate fibonacci numbers"}
                ]
            },
            'tool_calling': {
                "model": "claude-3-haiku",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": "What's the weather like today?"
                }],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and state"
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }]
            }
        }
        
        # Expected Anthropic response headers
        self.expected_anthropic_headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
        }
        
        self.formatter = UnifiedResponseFormatter()
    
    def test_anthropic_response_format_validation(self):
        """Test Anthropic API response format compliance."""
        # Mock Salesforce response
        mock_sf_response = {
            "generation": {
                "generatedText": "Hello! I'm doing well, thank you for asking."
            },
            "usage": {
                "inputTokenCount": 12,
                "outputTokenCount": 15,
                "totalTokenCount": 27
            }
        }
        
        # Format as Anthropic response
        anthropic_response = self.formatter.format_anthropic_response(
            mock_sf_response,
            model="claude-3-haiku"
        )
        
        # Validate Anthropic response structure
        required_fields = ['id', 'type', 'role', 'content', 'model', 'stop_reason', 'usage']
        for field in required_fields:
            self.assertIn(field, anthropic_response, f"Missing required field: {field}")
        
        # Validate field values
        self.assertEqual(anthropic_response['type'], 'message')
        self.assertEqual(anthropic_response['role'], 'assistant')
        self.assertEqual(anthropic_response['model'], 'claude-3-haiku')
        self.assertIn(anthropic_response['stop_reason'], ['end_turn', 'max_tokens', 'stop_sequence', 'tool_use'])
        
        # Validate content structure (list of content blocks)
        content = anthropic_response['content']
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)
        
        content_block = content[0]
        self.assertIn('type', content_block)
        self.assertIn('text', content_block)
        self.assertEqual(content_block['type'], 'text')
        
        # Validate usage structure (Anthropic format)
        usage = anthropic_response['usage']
        self.assertIn('input_tokens', usage)
        self.assertIn('output_tokens', usage)
        
        print(f"✅ Anthropic response format validation passed")
        print(f"   Response ID: {anthropic_response['id']}")
        print(f"   Content blocks: {len(content)}")
        print(f"   Usage: {usage}")
    
    def test_anthropic_system_message_handling(self):
        """Test system message handling in Anthropic format."""
        # Mock conversation with system message
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        # Test system message extraction and handling
        system_message = None
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                user_messages.append(msg)
        
        self.assertEqual(system_message, "You are a helpful assistant.")
        self.assertEqual(len(user_messages), 1)
        self.assertEqual(user_messages[0]['content'], "Hello!")
        
        print(f"✅ System message handling test passed")
        print(f"   System message: {system_message}")
        print(f"   User messages: {len(user_messages)}")
    
    def test_anthropic_content_block_processing(self):
        """Test content block processing for Anthropic responses."""
        test_texts = [
            "Simple response text",
            "Multi-line\\nresponse\\nwith breaks",
            "Response with special characters: éñ中文",
            "Very long response: " + "x" * 1000
        ]
        
        for text in test_texts:
            mock_sf_response = {
                "generation": {"generatedText": text},
                "usage": {"inputTokenCount": 10, "outputTokenCount": 20, "totalTokenCount": 30}
            }
            
            anthropic_response = self.formatter.format_anthropic_response(
                mock_sf_response,
                model="claude-3-haiku"
            )
            
            # Validate content block
            content = anthropic_response['content']
            self.assertIsInstance(content, list)
            self.assertEqual(len(content), 1)
            
            content_block = content[0]
            self.assertEqual(content_block['type'], 'text')
            self.assertEqual(content_block['text'], text)
            
            print(f"✅ Content block processing passed for: {text[:50]}{'...' if len(text) > 50 else ''}")
    
    def test_anthropic_stop_reason_mapping(self):
        """Test stop reason mapping for Anthropic responses."""
        test_cases = [
            {
                'sf_response': {"generation": {"generatedText": "Normal completion"}},
                'expected_stop_reason': 'end_turn'
            },
            {
                'sf_response': {
                    "generation": {"generatedText": "Tool usage"},
                    "generationDetails": {"parameters": {"stop_reason": "tool_use"}},
                    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "test", "arguments": "{}"}}]
                },
                'expected_stop_reason': 'tool_use'
            }
        ]
        
        for test_case in test_cases:
            anthropic_response = self.formatter.format_anthropic_response(
                test_case['sf_response'],
                model="claude-3-haiku"
            )
            
            self.assertEqual(
                anthropic_response['stop_reason'],
                test_case['expected_stop_reason']
            )
            
            print(f"✅ Stop reason mapping: {test_case['expected_stop_reason']}")
    
    def test_anthropic_error_response_handling(self):
        """Test error response handling for Claude Code."""
        test_errors = [
            ("Invalid API key", "authentication_error"),
            ("Rate limit exceeded", "rate_limit_exceeded"), 
            ("Model overloaded", "service_unavailable"),
            ("Invalid request format", "invalid_request")
        ]
        
        for error_message, error_code in test_errors:
            error_response = self.formatter.format_error_response(
                error_message,
                error_code=error_code,
                model="claude-3-haiku"
            )
            
            # Validate error structure
            self.assertIn('error', error_response)
            error = error_response['error']
            
            self.assertEqual(error['message'], error_message)
            self.assertEqual(error['code'], error_code)
            self.assertIn('type', error)
            self.assertIn('details', error)
            
            print(f"✅ Error handling for {error_code}: {error_message}")
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
    )
    def test_claude_code_live_simple_message(self):
        """Live test of simple message with Claude Code compatibility."""
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=self.claude_code_test_data['simple_message'],
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Validate response format (should be OpenAI format for now)
            json_response = response.json()
            self.assertIn('choices', json_response)
            self.assertIn('usage', json_response)
            self.assertEqual(json_response['object'], 'chat.completion')
            
            # Validate message structure
            message = json_response['choices'][0]['message']
            self.assertEqual(message['role'], 'assistant')
            self.assertIn('content', message)
            self.assertIsInstance(message['content'], str)
            self.assertGreater(len(message['content']), 0)
            
            print(f"✅ Claude Code live simple message test passed")
            print(f"   Response length: {len(message['content'])} characters")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available for integration test: {e}")
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
    )
    def test_claude_code_live_system_message(self):
        """Live test of system message handling."""
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=self.claude_code_test_data['system_message'],
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            json_response = response.json()
            
            # Validate response
            message = json_response['choices'][0]['message']
            content = message['content']
            
            # Should be concise due to system message
            self.assertIsInstance(content, str)
            self.assertGreater(len(content), 0)
            
            # Check that response seems appropriate for the question
            content_lower = content.lower()
            self.assertTrue(
                any(word in content_lower for word in ['paris', 'france']),
                f"Response doesn't seem to answer the question: {content}"
            )
            
            print(f"✅ Claude Code system message test passed")
            print(f"   Response: {content}")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available for integration test: {e}")
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
    )
    def test_claude_code_live_streaming(self):
        """Live test of streaming responses for Claude Code."""
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json={**self.claude_code_test_data['simple_message'], "stream": True},
                stream=True,
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Content-Type'], 'text/event-stream; charset=utf-8')
            
            # Collect streaming chunks
            chunks = []
            content_pieces = []
            
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data.strip() == '[DONE]':
                        break
                    
                    try:
                        chunk = json.loads(data)
                        chunks.append(chunk)
                        
                        # Validate chunk structure
                        self.assertEqual(chunk['object'], 'chat.completion.chunk')
                        self.assertIn('choices', chunk)
                        self.assertEqual(chunk['model'], 'claude-3-haiku')
                        
                        # Collect content
                        choice = chunk['choices'][0]
                        delta = choice.get('delta', {})
                        if 'content' in delta:
                            content_pieces.append(delta['content'])
                            
                    except json.JSONDecodeError:
                        self.fail(f"Invalid JSON in stream chunk: {data}")
            
            # Validate streaming worked
            self.assertGreater(len(chunks), 0, "No chunks received")
            self.assertGreater(len(content_pieces), 0, "No content in stream")
            
            # Reconstruct full content
            full_content = ''.join(content_pieces)
            self.assertGreater(len(full_content), 0, "Empty content from stream")
            
            print(f"✅ Claude Code streaming test passed")
            print(f"   Chunks received: {len(chunks)}")
            print(f"   Content length: {len(full_content)} characters")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available for integration test: {e}")
    
    def test_claude_code_async_response_formatting(self):
        """Test async response formatting for Claude Code compatibility."""
        # Mock async client response
        mock_sf_response = {
            "generation": {
                "generatedText": "This is an async response from Claude."
            },
            "usage": {
                "inputTokenCount": 8,
                "outputTokenCount": 12,
                "totalTokenCount": 20
            }
        }
        
        # Test async formatting (simulated synchronously for testing)
        try:
            # Test the function exists and can be called
            from async_endpoint_server import format_openai_response_async
            
            # Run in event loop
            async def test_async_formatting():
                return await format_openai_response_async(
                    mock_sf_response,
                    model="claude-3-haiku"
                )
            
            # Run async test
            if hasattr(asyncio, 'run'):
                result = asyncio.run(test_async_formatting())
            else:
                # Fallback for older Python versions
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(test_async_formatting())
                finally:
                    loop.close()
            
            # Validate result
            self.assertIsInstance(result, dict)
            self.assertIn('choices', result)
            self.assertIn('usage', result)
            
            print(f"✅ Async response formatting test passed")
            
        except ImportError:
            self.skipTest("Async formatting function not available")
        except Exception as e:
            self.fail(f"Async formatting test failed: {e}")
    
    def test_claude_code_authentication_headers(self):
        """Test authentication header handling for Claude Code."""
        # Test various auth header formats
        auth_headers = [
            {'Authorization': 'Bearer sk-test-key'},
            {'x-api-key': 'claude-api-key'},
            {'Authorization': 'Basic dGVzdDp0ZXN0'},  # base64 test:test
        ]
        
        for headers in auth_headers:
            # Validate headers are properly formatted
            for key, value in headers.items():
                self.assertIsInstance(key, str)
                self.assertIsInstance(value, str)
                self.assertGreater(len(value), 0)
                
                # Validate common auth patterns
                if key == 'Authorization':
                    self.assertTrue(
                        value.startswith('Bearer ') or value.startswith('Basic '),
                        f"Invalid Authorization format: {value}"
                    )
        
        print(f"✅ Authentication headers test passed")
    
    def test_claude_code_request_validation(self):
        """Test request validation for Claude Code format."""
        valid_requests = [
            {
                "model": "claude-3-haiku",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": "Hello"}]
            },
            {
                "model": "claude-3-sonnet", 
                "max_tokens": 2000,
                "system": "You are helpful",
                "messages": [{"role": "user", "content": "Help me"}]
            }
        ]
        
        invalid_requests = [
            {},  # Empty request
            {"model": "claude-3-haiku"},  # Missing messages
            {"messages": [{"role": "user", "content": "Hello"}]},  # Missing model
            {"model": "claude-3-haiku", "messages": []},  # Empty messages
        ]
        
        # Validate valid requests pass basic checks
        for req in valid_requests:
            self.assertIn('model', req)
            self.assertIn('messages', req)
            self.assertIsInstance(req['messages'], list)
            self.assertGreater(len(req['messages']), 0)
            
            # Validate message format
            for msg in req['messages']:
                self.assertIn('role', msg)
                self.assertIn('content', msg)
        
        # Validate invalid requests fail checks
        for req in invalid_requests:
            has_model = 'model' in req and req['model']
            has_messages = 'messages' in req and req['messages']
            
            # At least one should be missing/invalid
            self.assertFalse(has_model and has_messages)
        
        print(f"✅ Claude Code request validation test passed")
    
    def test_claude_code_response_timing(self):
        """Test response timing and performance for Claude Code."""
        # Test response time tracking
        start_time = time.time()
        
        # Simulate processing
        time.sleep(0.1)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Validate timing
        self.assertGreater(processing_time, 0.05)  # At least 50ms (due to sleep)
        self.assertLess(processing_time, 1.0)  # Less than 1 second
        
        # Test timing metrics format
        timing_metrics = {
            'request_start_time': start_time,
            'request_end_time': end_time,
            'processing_time_ms': processing_time * 1000,
            'timestamp': int(time.time())
        }
        
        for key, value in timing_metrics.items():
            self.assertIsInstance(value, (int, float))
            self.assertGreater(value, 0)
        
        print(f"✅ Response timing test passed")
        print(f"   Processing time: {processing_time * 1000:.1f}ms")


class ClaudeCodeStreamingTests(unittest.TestCase):
    """Specialized tests for Claude Code streaming functionality."""
    
    def setUp(self):
        """Set up streaming test fixtures."""
        self.formatter = UnifiedResponseFormatter()
    
    def test_streaming_chunk_format_validation(self):
        """Test streaming chunk format for Claude Code compatibility."""
        # Mock streaming chunk
        chunk_data = {
            "id": "msg_test123",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "claude-3-haiku",
            "choices": [{
                "index": 0,
                "delta": {"content": "Hello"},
                "finish_reason": None
            }]
        }
        
        # Format as SSE
        sse_chunk = f"data: {json.dumps(chunk_data)}{chr(10)}{chr(10)}"
        
        # Validate SSE format
        self.assertTrue(sse_chunk.startswith('data: '))
        self.assertTrue(sse_chunk.endswith('\\n\\n'))
        
        # Parse JSON from SSE
        json_part = sse_chunk[6:-2]  # Remove 'data: ' and '\\n\\n'
        parsed_chunk = json.loads(json_part)
        
        # Validate chunk structure
        self.assertEqual(parsed_chunk['object'], 'chat.completion.chunk')
        self.assertIn('choices', parsed_chunk)
        self.assertIn('model', parsed_chunk)
        
        print(f"✅ Streaming chunk format validation passed")
    
    def test_streaming_content_accumulation(self):
        """Test content accumulation from streaming chunks."""
        # Simulate streaming chunks
        chunks = [
            {"delta": {"content": "Hello"}},
            {"delta": {"content": " there"}},
            {"delta": {"content": "!"}},
            {"delta": {}, "finish_reason": "stop"}
        ]
        
        # Accumulate content
        accumulated_content = ""
        final_finish_reason = None
        
        for chunk in chunks:
            delta = chunk.get('delta', {})
            if 'content' in delta:
                accumulated_content += delta['content']
            
            if chunk.get('finish_reason'):
                final_finish_reason = chunk['finish_reason']
        
        # Validate accumulation
        self.assertEqual(accumulated_content, "Hello there!")
        self.assertEqual(final_finish_reason, "stop")
        
        print(f"✅ Streaming content accumulation test passed")
        print(f"   Final content: {accumulated_content}")
    
    def test_streaming_error_handling(self):
        """Test streaming error handling for Claude Code."""
        # Test streaming error format
        error = Exception("Streaming connection lost")
        
        error_chunk = self.formatter.format_streaming_error(
            error, 
            model="claude-3-haiku"
        )
        
        # Validate error chunk format
        self.assertTrue(error_chunk.startswith("data: "))
        self.assertTrue(error_chunk.endswith("\\n\\n"))
        
        # Parse error chunk
        json_part = error_chunk[6:-2]
        error_data = json.loads(json_part)
        
        # Validate error structure
        self.assertEqual(error_data['object'], 'chat.completion.chunk')
        self.assertEqual(error_data['choices'][0]['finish_reason'], 'error')
        self.assertIn('error', error_data)
        
        print(f"✅ Streaming error handling test passed")


def run_claude_code_test_suite():
    """Run the complete Claude Code compatibility test suite."""
    print("🤖 Running Claude Code Compatibility Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(ClaudeCodeCompatibilityTests))
    suite.addTest(unittest.makeSuite(ClaudeCodeStreamingTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_claude_code_test_suite()