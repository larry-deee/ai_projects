#!/usr/bin/env python3
"""
Response Format Compliance Test Suite
====================================

This test suite validates that the unified response formatter produces
responses that are 100% compliant with OpenAI and Anthropic API specifications.

Tests cover:
- Response structure validation
- Field type validation
- Required field presence
- Response consistency across servers
- Tool calling compliance
- Error response formats
- Usage statistics accuracy
"""

import json
import time
import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

# Import the unified formatter
try:
    from unified_response_formatter import (
        UnifiedResponseFormatter,
        extract_response_text_unified,
        format_openai_response_unified,
        format_anthropic_response_unified,
        format_error_response_unified
    )
except ImportError:
    # Handle import errors gracefully for testing
    print("Warning: unified_response_formatter module not available")


class TestResponseFormatCompliance(unittest.TestCase):
    """Test suite for response format compliance validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = UnifiedResponseFormatter(debug_mode=False)
        self.test_model = "claude-3-haiku"
        
        # Sample Salesforce responses for testing
        self.sample_sf_responses = {
            'standard': {
                "generation": {
                    "generatedText": "Hello, world! This is a test response."
                },
                "usage": {
                    "inputTokenCount": 10,
                    "outputTokenCount": 8,
                    "totalTokenCount": 18
                }
            },
            'legacy': {
                "generations": [{
                    "text": "Legacy response format."
                }],
                "parameters": {
                    "usage": {
                        "inputTokenCount": 5,
                        "outputTokenCount": 3,
                        "totalTokenCount": 8
                    }
                }
            },
            'new_format': {
                "generationDetails": {
                    "generations": [{
                        "content": "New generation details format."
                    }],
                    "parameters": {
                        "usage": {
                            "inputTokenCount": 7,
                            "outputTokenCount": 4,
                            "totalTokenCount": 11
                        }
                    }
                }
            },
            'tool_calls': {
                "generation": {
                    "generatedText": "Let me get the current time for you."
                },
                "generationDetails": {
                    "parameters": {
                        "stop_reason": "tool_use"
                    }
                },
                "tool_calls": [{
                    "id": "call_12345",
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "arguments": "{}"
                    }
                }],
                "usage": {
                    "inputTokenCount": 12,
                    "outputTokenCount": 10,
                    "totalTokenCount": 22
                }
            },
            'error_response': {
                "error": {
                    "message": "Rate limit exceeded. Please try again later.",
                    "type": "rate_limit_error"
                }
            },
            'empty_response': {},
            'malformed_response': {
                "unexpected_field": "unexpected_value"
            }
        }
    
    def test_openai_response_structure_compliance(self):
        """Test that OpenAI responses have the correct structure."""
        for response_type, sf_response in self.sample_sf_responses.items():
            if response_type == 'error_response':
                continue  # Skip error responses for this test
                
            with self.subTest(response_type=response_type):
                openai_response = self.formatter.format_openai_response(sf_response, self.test_model)
                
                # Validate required top-level fields
                self.assertIn('id', openai_response)
                self.assertIn('object', openai_response)
                self.assertIn('created', openai_response)
                self.assertIn('model', openai_response)
                self.assertIn('choices', openai_response)
                self.assertIn('usage', openai_response)
                
                # Validate field types
                self.assertIsInstance(openai_response['id'], str)
                self.assertEqual(openai_response['object'], "chat.completion")
                self.assertIsInstance(openai_response['created'], int)
                self.assertEqual(openai_response['model'], self.test_model)
                self.assertIsInstance(openai_response['choices'], list)
                self.assertIsInstance(openai_response['usage'], dict)
                
                # Validate choices structure
                self.assertGreater(len(openai_response['choices']), 0)
                choice = openai_response['choices'][0]
                
                self.assertIn('index', choice)
                self.assertIn('message', choice)
                self.assertIn('finish_reason', choice)
                
                self.assertEqual(choice['index'], 0)
                self.assertIsInstance(choice['message'], dict)
                self.assertIn(choice['finish_reason'], ['stop', 'length', 'tool_calls', 'content_filter'])
                
                # Validate message structure
                message = choice['message']
                self.assertIn('role', message)
                self.assertIn('content', message)
                
                self.assertEqual(message['role'], 'assistant')
                self.assertIsInstance(message['content'], str)
                
                # Validate usage structure
                usage = openai_response['usage']
                self.assertIn('prompt_tokens', usage)
                self.assertIn('completion_tokens', usage)
                self.assertIn('total_tokens', usage)
                
                for token_count in usage.values():
                    self.assertIsInstance(token_count, int)
                    self.assertGreaterEqual(token_count, 0)
    
    def test_tool_calls_response_compliance(self):
        """Test that tool calls responses are properly formatted."""
        sf_response = self.sample_sf_responses['tool_calls']
        openai_response = self.formatter.format_openai_response(sf_response, self.test_model)
        
        # Check finish reason for tool calls
        self.assertEqual(openai_response['choices'][0]['finish_reason'], 'tool_calls')
        
        # Check tool calls structure
        message = openai_response['choices'][0]['message']
        self.assertIn('tool_calls', message)
        
        tool_calls = message['tool_calls']
        self.assertIsInstance(tool_calls, list)
        self.assertGreater(len(tool_calls), 0)
        
        # Validate each tool call
        for tool_call in tool_calls:
            self.assertIn('id', tool_call)
            self.assertIn('type', tool_call)
            self.assertIn('function', tool_call)
            
            self.assertIsInstance(tool_call['id'], str)
            self.assertEqual(tool_call['type'], 'function')
            self.assertIsInstance(tool_call['function'], dict)
            
            function = tool_call['function']
            self.assertIn('name', function)
            self.assertIn('arguments', function)
            
            self.assertIsInstance(function['name'], str)
            self.assertIsInstance(function['arguments'], str)
            
            # Validate arguments is valid JSON
            try:
                json.loads(function['arguments'])
            except json.JSONDecodeError:
                self.fail(f"Tool call arguments is not valid JSON: {function['arguments']}")
    
    def test_anthropic_response_structure_compliance(self):
        """Test that Anthropic responses have the correct structure."""
        for response_type, sf_response in self.sample_sf_responses.items():
            if response_type in ['error_response', 'tool_calls']:
                continue  # Skip error and tool call responses for this test
                
            with self.subTest(response_type=response_type):
                anthropic_response = self.formatter.format_anthropic_response(sf_response, self.test_model)
                
                # Validate required top-level fields
                self.assertIn('id', anthropic_response)
                self.assertIn('type', anthropic_response)
                self.assertIn('role', anthropic_response)
                self.assertIn('content', anthropic_response)
                self.assertIn('model', anthropic_response)
                self.assertIn('stop_reason', anthropic_response)
                self.assertIn('usage', anthropic_response)
                
                # Validate field types and values
                self.assertIsInstance(anthropic_response['id'], str)
                self.assertEqual(anthropic_response['type'], "message")
                self.assertEqual(anthropic_response['role'], "assistant")
                self.assertEqual(anthropic_response['model'], self.test_model)
                self.assertIn(anthropic_response['stop_reason'], 
                             ['end_turn', 'max_tokens', 'stop_sequence', 'tool_use'])
                
                # Validate content structure
                content = anthropic_response['content']
                self.assertIsInstance(content, list)
                self.assertGreater(len(content), 0)
                
                for content_block in content:
                    self.assertIn('type', content_block)
                    self.assertIn('text', content_block)
                    self.assertEqual(content_block['type'], 'text')
                    self.assertIsInstance(content_block['text'], str)
                
                # Validate usage structure
                usage = anthropic_response['usage']
                self.assertIn('input_tokens', usage)
                self.assertIn('output_tokens', usage)
                
                for token_count in usage.values():
                    self.assertIsInstance(token_count, int)
                    self.assertGreaterEqual(token_count, 0)
    
    def test_response_extraction_consistency(self):
        """Test that response text extraction is consistent across different formats."""
        expected_texts = {
            'standard': "Hello, world! This is a test response.",
            'legacy': "Legacy response format.",
            'new_format': "New generation details format.",
            'tool_calls': "Let me get the current time for you."
        }
        
        for response_type, sf_response in self.sample_sf_responses.items():
            if response_type not in expected_texts:
                continue
                
            with self.subTest(response_type=response_type):
                extracted_text = extract_response_text_unified(sf_response)
                expected_text = expected_texts[response_type]
                
                self.assertEqual(extracted_text, expected_text,
                               f"Text extraction failed for {response_type}")
    
    def test_usage_statistics_accuracy(self):
        """Test that usage statistics are accurately extracted."""
        for response_type, sf_response in self.sample_sf_responses.items():
            if 'usage' not in json.dumps(sf_response).lower():
                continue
                
            with self.subTest(response_type=response_type):
                usage_info = self.formatter.extract_usage_info(sf_response)
                
                # Verify that usage information is extracted
                self.assertIsInstance(usage_info.prompt_tokens, int)
                self.assertIsInstance(usage_info.completion_tokens, int)
                self.assertIsInstance(usage_info.total_tokens, int)
                
                # For responses with usage data, check consistency
                if response_type in ['standard', 'legacy', 'new_format', 'tool_calls']:
                    # Total should equal prompt + completion (or be independently set)
                    if usage_info.total_tokens > 0:
                        self.assertTrue(
                            usage_info.total_tokens == usage_info.prompt_tokens + usage_info.completion_tokens
                            or usage_info.total_tokens > max(usage_info.prompt_tokens, usage_info.completion_tokens),
                            f"Usage calculation inconsistent for {response_type}"
                        )
    
    def test_error_response_compliance(self):
        """Test that error responses are properly formatted."""
        test_errors = [
            ("Authentication failed", "authentication_error"),
            ("Rate limit exceeded", "rate_limit_exceeded"),
            ("Request timed out", "timeout_error"),
            ("Service unavailable", "service_unavailable"),
            ("Generic error", "internal_error")
        ]
        
        for error_message, expected_code in test_errors:
            with self.subTest(error_message=error_message):
                error_response = format_error_response_unified(error_message, self.test_model)
                
                # Validate error structure
                self.assertIn('error', error_response)
                error = error_response['error']
                
                self.assertIn('message', error)
                self.assertIn('type', error)
                self.assertIn('code', error)
                
                self.assertEqual(error['message'], error_message)
                self.assertIsInstance(error['type'], str)
                self.assertIsInstance(error['code'], str)
    
    def test_response_id_consistency(self):
        """Test that response IDs are consistently formatted."""
        sf_response = self.sample_sf_responses['standard']
        
        # Generate multiple responses
        responses = [
            self.formatter.format_openai_response(sf_response, self.test_model)
            for _ in range(5)
        ]
        
        for response in responses:
            response_id = response['id']
            
            # Validate ID format
            self.assertTrue(response_id.startswith('chatcmpl-'))
            self.assertRegex(response_id, r'^chatcmpl-\d+')
            
            # Validate timestamp component is reasonable
            timestamp_str = response_id.replace('chatcmpl-', '')
            # Remove any additional components after timestamp
            if '-' in timestamp_str:
                timestamp_str = timestamp_str.split('-')[0]
            
            try:
                timestamp = int(timestamp_str)
                current_time = int(time.time())
                self.assertLess(abs(current_time - timestamp), 60,  # Within 60 seconds
                              "Response ID timestamp is unrealistic")
            except ValueError:
                self.fail(f"Response ID contains invalid timestamp: {response_id}")
    
    def test_content_validation_and_sanitization(self):
        """Test that content is properly validated and sanitized."""
        test_cases = [
            # Normal content
            {"generation": {"generatedText": "Normal content"}},
            # Very long content
            {"generation": {"generatedText": "x" * 150000}},
            # Empty content
            {"generation": {"generatedText": ""}},
            # Non-string content
            {"generation": {"generatedText": None}},
        ]
        
        for i, sf_response in enumerate(test_cases):
            with self.subTest(test_case=i):
                openai_response = self.formatter.format_openai_response(sf_response, self.test_model)
                
                content = openai_response['choices'][0]['message']['content']
                
                # Content should always be a string
                self.assertIsInstance(content, str)
                
                # Long content should be truncated
                self.assertLessEqual(len(content), 100100,  # 100k + truncation message
                                    "Content was not properly truncated")
                
                # Content should not be None or empty for valid responses
                if sf_response["generation"]["generatedText"] is None:
                    self.assertTrue(content.startswith("Error:") or content.strip() != "")
    
    def test_finish_reason_determination(self):
        """Test that finish reasons are correctly determined."""
        test_cases = [
            # Normal completion
            ({"generation": {"generatedText": "Normal response"}}, "stop"),
            
            # Tool calls
            ({
                "generation": {"generatedText": "Using tools"},
                "generationDetails": {"parameters": {"stop_reason": "tool_use"}},
                "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "test", "arguments": "{}"}}]
            }, "tool_calls"),
            
            # Length limit
            ({"generation": {"generatedText": "x" * 100000}}, "length"),
        ]
        
        for sf_response, expected_finish_reason in test_cases:
            with self.subTest(expected_finish_reason=expected_finish_reason):
                openai_response = self.formatter.format_openai_response(sf_response, self.test_model)
                
                actual_finish_reason = openai_response['choices'][0]['finish_reason']
                
                # For length test case, we expect either "length" or "stop" depending on truncation
                if expected_finish_reason == "length":
                    self.assertIn(actual_finish_reason, ["length", "stop"])
                else:
                    self.assertEqual(actual_finish_reason, expected_finish_reason,
                                   f"Incorrect finish reason for test case")
    
    def test_n8n_header_compatibility(self):
        """Test that n8n-compatible headers are correctly set."""
        # This test would normally require Flask/Quart response objects
        # For now, we verify the function exists and can be called
        try:
            from unified_response_formatter import add_n8n_compatible_headers
            
            # Mock response object
            class MockResponse:
                def __init__(self):
                    self.headers = {}
            
            mock_response = MockResponse()
            result = add_n8n_compatible_headers(mock_response)
            
            # Verify required headers are set
            required_headers = [
                'Content-Type',
                'Cache-Control',
                'Access-Control-Allow-Origin',
                'X-Content-Type-Options'
            ]
            
            for header in required_headers:
                self.assertIn(header, result.headers,
                            f"Required n8n header missing: {header}")
                
            # Verify specific header values
            self.assertEqual(result.headers['Content-Type'], 'application/json; charset=utf-8')
            self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')
            
        except ImportError:
            self.skipTest("n8n header function not available")
    
    def test_streaming_response_format(self):
        """Test streaming response format compliance."""
        test_error = Exception("Streaming error")
        
        try:
            streaming_error = self.formatter.format_streaming_error(test_error, self.test_model)
            
            # Validate SSE format
            self.assertTrue(streaming_error.startswith("data: "))
            self.assertTrue(streaming_error.endswith("\n\n"))
            
            # Extract and validate JSON
            json_part = streaming_error[6:-2]  # Remove "data: " and "\n\n"
            error_chunk = json.loads(json_part)
            
            # Validate chunk structure
            self.assertIn('id', error_chunk)
            self.assertIn('object', error_chunk)
            self.assertIn('created', error_chunk)
            self.assertIn('model', error_chunk)
            self.assertIn('choices', error_chunk)
            
            self.assertEqual(error_chunk['object'], 'chat.completion.chunk')
            self.assertEqual(error_chunk['model'], self.test_model)
            self.assertEqual(error_chunk['choices'][0]['finish_reason'], 'error')
            
        except Exception as e:
            self.fail(f"Streaming error format test failed: {e}")


class TestResponseConsistency(unittest.TestCase):
    """Test consistency between old and new formatters."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = UnifiedResponseFormatter(debug_mode=False)
        self.test_model = "claude-3-haiku"
        
        # Standard test response
        self.test_response = {
            "generation": {
                "generatedText": "This is a test response for consistency validation."
            },
            "usage": {
                "inputTokenCount": 15,
                "outputTokenCount": 12,
                "totalTokenCount": 27
            }
        }
    
    @patch('time.time')
    def test_deterministic_response_generation(self, mock_time):
        """Test that responses are deterministic given the same input."""
        # Mock time to ensure consistent timestamps
        mock_time.return_value = 1640995200  # Fixed timestamp
        
        # Generate multiple responses
        responses = [
            self.formatter.format_openai_response(self.test_response, self.test_model)
            for _ in range(3)
        ]
        
        # All responses should be identical
        for i in range(1, len(responses)):
            self.assertEqual(responses[0], responses[i],
                           f"Response {i} differs from response 0")
    
    def test_backward_compatibility_fields(self):
        """Test that all expected fields are present for backward compatibility."""
        openai_response = self.formatter.format_openai_response(self.test_response, self.test_model)
        
        # Required fields that clients expect
        expected_fields = {
            'id': str,
            'object': str,
            'created': int,
            'model': str,
            'choices': list,
            'usage': dict
        }
        
        for field, expected_type in expected_fields.items():
            self.assertIn(field, openai_response,
                        f"Required field missing: {field}")
            self.assertIsInstance(openai_response[field], expected_type,
                                f"Field {field} has incorrect type")
        
        # Choice fields
        choice = openai_response['choices'][0]
        choice_fields = {
            'index': int,
            'message': dict,
            'finish_reason': str
        }
        
        for field, expected_type in choice_fields.items():
            self.assertIn(field, choice,
                        f"Required choice field missing: {field}")
            self.assertIsInstance(choice[field], expected_type,
                                f"Choice field {field} has incorrect type")
        
        # Message fields
        message = choice['message']
        message_fields = {
            'role': str,
            'content': str
        }
        
        for field, expected_type in message_fields.items():
            self.assertIn(field, message,
                        f"Required message field missing: {field}")
            self.assertIsInstance(message[field], expected_type,
                                f"Message field {field} has incorrect type")
        
        # Usage fields
        usage = openai_response['usage']
        usage_fields = {
            'prompt_tokens': int,
            'completion_tokens': int,
            'total_tokens': int
        }
        
        for field, expected_type in usage_fields.items():
            self.assertIn(field, usage,
                        f"Required usage field missing: {field}")
            self.assertIsInstance(usage[field], expected_type,
                                f"Usage field {field} has incorrect type")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)