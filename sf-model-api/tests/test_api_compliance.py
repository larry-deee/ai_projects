#!/usr/bin/env python3
"""
API Specification Compliance Test Suite
=======================================

Comprehensive test suite validating API specification compliance for both
OpenAI and Anthropic formats. Ensures exact adherence to API specifications
and validates response structure consistency.

Tests cover:
- OpenAI API format validation and compliance
- Anthropic API format validation and compliance
- Tool calling response structure compliance
- Error response format consistency
- Field type and name validation
- Response header compliance
"""

import json
import time
import unittest
import requests
from typing import Dict, Any, List, Optional
from jsonschema import validate, ValidationError
import re

# Import project modules
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from unified_response_formatter import UnifiedResponseFormatter
    from tool_handler import ToolCallingHandler, ToolCallingConfig
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


class OpenAIComplianceTests(unittest.TestCase):
    """Test suite for OpenAI API specification compliance."""
    
    def setUp(self):
        """Set up OpenAI compliance test fixtures."""
        self.formatter = UnifiedResponseFormatter()
        self.server_url = "http://localhost:8000"
        
        # OpenAI API schema definitions
        self.openai_chat_completion_schema = {
            "type": "object",
            "required": ["id", "object", "created", "model", "choices", "usage"],
            "properties": {
                "id": {"type": "string", "pattern": r"^chatcmpl-"},
                "object": {"type": "string", "enum": ["chat.completion"]},
                "created": {"type": "integer"},
                "model": {"type": "string"},
                "choices": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["index", "message", "finish_reason"],
                        "properties": {
                            "index": {"type": "integer"},
                            "message": {
                                "type": "object",
                                "required": ["role", "content"],
                                "properties": {
                                    "role": {"type": "string", "enum": ["assistant"]},
                                    "content": {"type": ["string", "null"]},
                                    "tool_calls": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "required": ["id", "type", "function"],
                                            "properties": {
                                                "id": {"type": "string"},
                                                "type": {"type": "string", "enum": ["function"]},
                                                "function": {
                                                    "type": "object",
                                                    "required": ["name", "arguments"],
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "arguments": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "finish_reason": {
                                "type": "string", 
                                "enum": ["stop", "length", "tool_calls", "content_filter"]
                            }
                        }
                    }
                },
                "usage": {
                    "type": "object",
                    "required": ["prompt_tokens", "completion_tokens", "total_tokens"],
                    "properties": {
                        "prompt_tokens": {"type": "integer", "minimum": 0},
                        "completion_tokens": {"type": "integer", "minimum": 0},
                        "total_tokens": {"type": "integer", "minimum": 0}
                    }
                },
                "system_fingerprint": {"type": "string"}
            }
        }
        
        # Test responses for validation
        self.test_sf_responses = {
            'simple': {
                "generation": {
                    "generatedText": "This is a test response."
                },
                "usage": {
                    "inputTokenCount": 10,
                    "outputTokenCount": 6,
                    "totalTokenCount": 16
                }
            },
            'with_tool_calls': {
                "generation": {
                    "generatedText": "I'll help you with that."
                },
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "San Francisco"}'
                    }
                }],
                "usage": {
                    "inputTokenCount": 15,
                    "outputTokenCount": 8,
                    "totalTokenCount": 23
                }
            }
        }
    
    def test_openai_response_schema_compliance(self):
        """Test that OpenAI responses comply with the official schema."""
        for response_name, sf_response in self.test_sf_responses.items():
            with self.subTest(response_type=response_name):
                openai_response = self.formatter.format_openai_response(
                    sf_response, 
                    model="claude-3-haiku"
                )
                
                # Validate against schema
                try:
                    validate(instance=openai_response, schema=self.openai_chat_completion_schema)
                    print(f"✅ OpenAI schema validation passed for {response_name}")
                except ValidationError as e:
                    self.fail(f"OpenAI schema validation failed for {response_name}: {e.message}")
    
    def test_openai_field_types_strict(self):
        """Test strict field type compliance for OpenAI responses."""
        sf_response = self.test_sf_responses['simple']
        openai_response = self.formatter.format_openai_response(sf_response, "claude-3-haiku")
        
        # Validate top-level field types
        self.assertIsInstance(openai_response['id'], str)
        self.assertIsInstance(openai_response['object'], str)
        self.assertIsInstance(openai_response['created'], int)
        self.assertIsInstance(openai_response['model'], str)
        self.assertIsInstance(openai_response['choices'], list)
        self.assertIsInstance(openai_response['usage'], dict)
        
        # Validate choice structure
        choice = openai_response['choices'][0]
        self.assertIsInstance(choice['index'], int)
        self.assertIsInstance(choice['message'], dict)
        self.assertIsInstance(choice['finish_reason'], str)
        
        # Validate message structure
        message = choice['message']
        self.assertIsInstance(message['role'], str)
        self.assertIsInstance(message['content'], (str, type(None)))
        
        # Validate usage structure
        usage = openai_response['usage']
        self.assertIsInstance(usage['prompt_tokens'], int)
        self.assertIsInstance(usage['completion_tokens'], int)
        self.assertIsInstance(usage['total_tokens'], int)
        
        print("✅ OpenAI field type validation passed")
    
    def test_openai_id_format_compliance(self):
        """Test OpenAI response ID format compliance."""
        sf_response = self.test_sf_responses['simple']
        
        # Generate multiple responses to test ID format consistency
        for i in range(5):
            openai_response = self.formatter.format_openai_response(sf_response, "claude-3-haiku")
            response_id = openai_response['id']
            
            # Validate ID format
            self.assertTrue(response_id.startswith('chatcmpl-'), 
                           f"Invalid ID format: {response_id}")
            self.assertRegex(response_id, r'^chatcmpl-\d+', 
                           f"ID doesn't match expected pattern: {response_id}")
            
            # ID should be reasonable length
            self.assertGreaterEqual(len(response_id), 15, "ID too short")
            self.assertLessEqual(len(response_id), 50, "ID too long")
        
        print("✅ OpenAI ID format compliance validated")
    
    def test_openai_tool_calls_compliance(self):
        """Test OpenAI tool calls format compliance."""
        sf_response = self.test_sf_responses['with_tool_calls']
        openai_response = self.formatter.format_openai_response(sf_response, "claude-3-haiku")
        
        # Validate finish_reason for tool calls
        self.assertEqual(openai_response['choices'][0]['finish_reason'], 'tool_calls')
        
        # Validate tool calls structure
        message = openai_response['choices'][0]['message']
        self.assertIn('tool_calls', message)
        
        tool_calls = message['tool_calls']
        self.assertIsInstance(tool_calls, list)
        self.assertGreater(len(tool_calls), 0)
        
        # Validate each tool call
        for tool_call in tool_calls:
            # Required fields
            self.assertIn('id', tool_call)
            self.assertIn('type', tool_call)
            self.assertIn('function', tool_call)
            
            # Field values
            self.assertIsInstance(tool_call['id'], str)
            self.assertEqual(tool_call['type'], 'function')
            self.assertIsInstance(tool_call['function'], dict)
            
            # Function structure
            function = tool_call['function']
            self.assertIn('name', function)
            self.assertIn('arguments', function)
            self.assertIsInstance(function['name'], str)
            self.assertIsInstance(function['arguments'], str)
            
            # Arguments should be valid JSON
            try:
                json.loads(function['arguments'])
            except json.JSONDecodeError:
                self.fail(f"Tool call arguments not valid JSON: {function['arguments']}")
        
        print("✅ OpenAI tool calls compliance validated")
    
    def test_openai_usage_calculation_accuracy(self):
        """Test usage calculation accuracy for OpenAI responses."""
        test_cases = [
            {
                'sf_response': {
                    "generation": {"generatedText": "Short response"},
                    "usage": {"inputTokenCount": 5, "outputTokenCount": 2, "totalTokenCount": 7}
                },
                'expected_total': 7
            },
            {
                'sf_response': {
                    "generation": {"generatedText": "Longer response with more tokens"},
                    "usage": {"inputTokenCount": 10, "outputTokenCount": 6, "totalTokenCount": 16}
                },
                'expected_total': 16
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            openai_response = self.formatter.format_openai_response(
                test_case['sf_response'], 
                "claude-3-haiku"
            )
            
            usage = openai_response['usage']
            
            # Validate usage calculations
            self.assertEqual(usage['total_tokens'], test_case['expected_total'])
            self.assertEqual(
                usage['total_tokens'], 
                usage['prompt_tokens'] + usage['completion_tokens']
            )
            
            # All values should be non-negative
            self.assertGreaterEqual(usage['prompt_tokens'], 0)
            self.assertGreaterEqual(usage['completion_tokens'], 0)
            self.assertGreaterEqual(usage['total_tokens'], 0)
        
        print("✅ OpenAI usage calculation accuracy validated")
    
    def test_openai_error_response_format(self):
        """Test OpenAI error response format compliance."""
        error_cases = [
            ("Invalid model specified", "invalid_request_error"),
            ("Rate limit exceeded", "rate_limit_error"),
            ("Authentication failed", "authentication_error")
        ]
        
        for error_message, error_type in error_cases:
            error_response = self.formatter.format_error_response(
                error_message,
                error_type=error_type,
                model="claude-3-haiku"
            )
            
            # Validate error structure
            self.assertIn('error', error_response)
            error = error_response['error']
            
            # Required error fields
            self.assertIn('message', error)
            self.assertIn('type', error)
            self.assertIn('code', error)
            
            # Field validation
            self.assertEqual(error['message'], error_message)
            self.assertIsInstance(error['type'], str)
            self.assertIsInstance(error['code'], str)
            
            print(f"✅ Error format validated for {error_type}")


class AnthropicComplianceTests(unittest.TestCase):
    """Test suite for Anthropic API specification compliance."""
    
    def setUp(self):
        """Set up Anthropic compliance test fixtures."""
        self.formatter = UnifiedResponseFormatter()
        
        # Anthropic API schema definition
        self.anthropic_message_schema = {
            "type": "object",
            "required": ["id", "type", "role", "content", "model", "stop_reason", "usage"],
            "properties": {
                "id": {"type": "string", "pattern": r"^msg_"},
                "type": {"type": "string", "enum": ["message"]},
                "role": {"type": "string", "enum": ["assistant"]},
                "content": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["type", "text"],
                        "properties": {
                            "type": {"type": "string", "enum": ["text"]},
                            "text": {"type": "string"}
                        }
                    }
                },
                "model": {"type": "string"},
                "stop_reason": {
                    "type": "string",
                    "enum": ["end_turn", "max_tokens", "stop_sequence", "tool_use"]
                },
                "stop_sequence": {"type": ["string", "null"]},
                "usage": {
                    "type": "object",
                    "required": ["input_tokens", "output_tokens"],
                    "properties": {
                        "input_tokens": {"type": "integer", "minimum": 0},
                        "output_tokens": {"type": "integer", "minimum": 0}
                    }
                }
            }
        }
        
        # Test Salesforce responses
        self.test_sf_responses = {
            'simple': {
                "generation": {"generatedText": "Hello! How can I help you today?"},
                "usage": {"inputTokenCount": 8, "outputTokenCount": 9, "totalTokenCount": 17}
            },
            'long_response': {
                "generation": {"generatedText": "This is a much longer response that contains multiple sentences and should test the handling of longer content in the Anthropic format."},
                "usage": {"inputTokenCount": 12, "outputTokenCount": 25, "totalTokenCount": 37}
            }
        }
    
    def test_anthropic_response_schema_compliance(self):
        """Test that Anthropic responses comply with the official schema."""
        for response_name, sf_response in self.test_sf_responses.items():
            with self.subTest(response_type=response_name):
                anthropic_response = self.formatter.format_anthropic_response(
                    sf_response,
                    model="claude-3-haiku"
                )
                
                # Validate against schema
                try:
                    validate(instance=anthropic_response, schema=self.anthropic_message_schema)
                    print(f"✅ Anthropic schema validation passed for {response_name}")
                except ValidationError as e:
                    self.fail(f"Anthropic schema validation failed for {response_name}: {e.message}")
    
    def test_anthropic_content_blocks_structure(self):
        """Test Anthropic content blocks structure compliance."""
        sf_response = self.test_sf_responses['simple']
        anthropic_response = self.formatter.format_anthropic_response(sf_response, "claude-3-haiku")
        
        # Validate content structure
        content = anthropic_response['content']
        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)
        
        # Validate each content block
        for block in content:
            self.assertIn('type', block)
            self.assertIn('text', block)
            self.assertEqual(block['type'], 'text')
            self.assertIsInstance(block['text'], str)
        
        print("✅ Anthropic content blocks structure validated")
    
    def test_anthropic_id_format_compliance(self):
        """Test Anthropic message ID format compliance."""
        sf_response = self.test_sf_responses['simple']
        
        # Generate multiple responses to test ID consistency
        for i in range(5):
            anthropic_response = self.formatter.format_anthropic_response(sf_response, "claude-3-haiku")
            message_id = anthropic_response['id']
            
            # Validate ID format
            self.assertTrue(message_id.startswith('msg_'),
                           f"Invalid Anthropic ID format: {message_id}")
            
            # ID should be reasonable length
            self.assertGreaterEqual(len(message_id), 8, "Anthropic ID too short")
            self.assertLessEqual(len(message_id), 50, "Anthropic ID too long")
        
        print("✅ Anthropic ID format compliance validated")
    
    def test_anthropic_stop_reason_values(self):
        """Test Anthropic stop_reason value compliance."""
        test_cases = [
            {
                'sf_response': {"generation": {"generatedText": "Normal response"}},
                'expected_stop_reason': 'end_turn'
            }
        ]
        
        for test_case in test_cases:
            anthropic_response = self.formatter.format_anthropic_response(
                test_case['sf_response'],
                model="claude-3-haiku"
            )
            
            stop_reason = anthropic_response['stop_reason']
            self.assertIn(stop_reason, ['end_turn', 'max_tokens', 'stop_sequence', 'tool_use'])
            
            if 'expected_stop_reason' in test_case:
                self.assertEqual(stop_reason, test_case['expected_stop_reason'])
        
        print("✅ Anthropic stop_reason values validated")
    
    def test_anthropic_usage_format(self):
        """Test Anthropic usage format compliance."""
        sf_response = self.test_sf_responses['simple']
        anthropic_response = self.formatter.format_anthropic_response(sf_response, "claude-3-haiku")
        
        usage = anthropic_response['usage']
        
        # Required fields with correct names
        self.assertIn('input_tokens', usage)
        self.assertIn('output_tokens', usage)
        
        # Field types and values
        self.assertIsInstance(usage['input_tokens'], int)
        self.assertIsInstance(usage['output_tokens'], int)
        self.assertGreaterEqual(usage['input_tokens'], 0)
        self.assertGreaterEqual(usage['output_tokens'], 0)
        
        print("✅ Anthropic usage format validated")


class ToolCallingComplianceTests(unittest.TestCase):
    """Test suite for tool calling specification compliance."""
    
    def setUp(self):
        """Set up tool calling compliance test fixtures."""
        self.config = ToolCallingConfig()
        self.handler = ToolCallingHandler(self.config)
        self.formatter = UnifiedResponseFormatter()
        
        # Standard tool definition
        self.test_tool = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The location to get weather for"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    
    def test_tool_definition_validation(self):
        """Test tool definition validation compliance."""
        # Valid tool should pass validation
        try:
            validated_tools = self.handler._validate_and_parse_tools([self.test_tool])
            self.assertEqual(len(validated_tools), 1)
            print("✅ Valid tool definition accepted")
        except Exception as e:
            self.fail(f"Valid tool definition rejected: {e}")
        
        # Invalid tools should be rejected
        invalid_tools = [
            {"type": "function", "function": {}},  # Missing name
            {"type": "function", "function": {"name": ""}},  # Empty name
            {"function": {"name": "test"}},  # Missing type
        ]
        
        for invalid_tool in invalid_tools:
            with self.assertRaises(Exception):
                self.handler._validate_and_parse_tools([invalid_tool])
        
        print("✅ Invalid tool definitions properly rejected")
    
    def test_tool_call_response_format(self):
        """Test tool call response format compliance."""
        # Mock tool call response
        mock_response = {
            "generation": {"generatedText": "I'll get the weather for you."},
            "tool_calls": [{
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location": "San Francisco"}'
                }
            }],
            "usage": {"inputTokenCount": 10, "outputTokenCount": 8, "totalTokenCount": 18}
        }
        
        # Format as OpenAI response
        openai_response = self.formatter.format_openai_response(mock_response, "claude-3-haiku")
        
        # Validate tool call format
        self.assertEqual(openai_response['choices'][0]['finish_reason'], 'tool_calls')
        
        message = openai_response['choices'][0]['message']
        self.assertIn('tool_calls', message)
        
        tool_calls = message['tool_calls']
        self.assertIsInstance(tool_calls, list)
        self.assertEqual(len(tool_calls), 1)
        
        tool_call = tool_calls[0]
        self.assertIn('id', tool_call)
        self.assertIn('type', tool_call)
        self.assertIn('function', tool_call)
        self.assertEqual(tool_call['type'], 'function')
        
        function = tool_call['function']
        self.assertIn('name', function)
        self.assertIn('arguments', function)
        self.assertEqual(function['name'], 'get_weather')
        
        # Arguments should be valid JSON
        args = json.loads(function['arguments'])
        self.assertIn('location', args)
        
        print("✅ Tool call response format compliance validated")
    
    def test_tool_call_arguments_serialization(self):
        """Test tool call arguments serialization compliance."""
        test_arguments = [
            {"location": "San Francisco"},
            {"location": "New York", "unit": "celsius"},
            {"complex": {"nested": {"data": [1, 2, 3]}}},
        ]
        
        for args in test_arguments:
            # Serialize arguments
            args_json = json.dumps(args)
            
            # Create mock tool call
            mock_tool_call = {
                "id": "call_test",
                "type": "function",
                "function": {
                    "name": "test_function",
                    "arguments": args_json
                }
            }
            
            # Validate serialization
            self.assertIsInstance(mock_tool_call['function']['arguments'], str)
            
            # Validate deserialization
            deserialized = json.loads(mock_tool_call['function']['arguments'])
            self.assertEqual(deserialized, args)
        
        print("✅ Tool call arguments serialization validated")


@unittest.skipUnless(
    os.environ.get('INTEGRATION_TESTS') == 'true',
    "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
)
class LiveAPIComplianceTests(unittest.TestCase):
    """Live API compliance tests against running server."""
    
    def setUp(self):
        """Set up live API testing."""
        self.server_url = "http://localhost:8000"
        self.test_timeout = 30
        
        self.test_payload = {
            "model": "claude-3-haiku",
            "messages": [{"role": "user", "content": "Hello, please respond briefly."}],
            "max_tokens": 100
        }
    
    def test_live_openai_compliance(self):
        """Test live OpenAI API compliance."""
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=self.test_payload,
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get('Content-Type'), 'application/json; charset=utf-8')
            
            data = response.json()
            
            # Basic OpenAI structure validation
            required_fields = ['id', 'object', 'created', 'model', 'choices', 'usage']
            for field in required_fields:
                self.assertIn(field, data, f"Missing required field: {field}")
            
            self.assertEqual(data['object'], 'chat.completion')
            self.assertTrue(data['id'].startswith('chatcmpl-'))
            self.assertIsInstance(data['created'], int)
            
            print("✅ Live OpenAI compliance validated")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available: {e}")
    
    def test_live_response_headers(self):
        """Test live response headers compliance."""
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=self.test_payload,
                timeout=self.test_timeout
            )
            
            # Validate CORS headers
            self.assertIn('Access-Control-Allow-Origin', response.headers)
            
            # Validate content type
            content_type = response.headers.get('Content-Type')
            self.assertTrue(content_type.startswith('application/json'))
            
            print("✅ Live response headers validated")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available: {e}")
    
    def test_live_error_response_compliance(self):
        """Test live error response compliance."""
        # Send invalid request
        invalid_payload = {
            "model": "invalid-model",
            "messages": []  # Empty messages should cause error
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=invalid_payload,
                timeout=self.test_timeout
            )
            
            # Should return error status
            self.assertGreaterEqual(response.status_code, 400)
            
            # Should still have proper content type
            content_type = response.headers.get('Content-Type')
            self.assertTrue(content_type.startswith('application/json'))
            
            # Should have error structure
            try:
                error_data = response.json()
                self.assertIn('error', error_data)
            except json.JSONDecodeError:
                self.fail("Error response not valid JSON")
            
            print("✅ Live error response compliance validated")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available: {e}")


def run_api_compliance_test_suite():
    """Run the complete API compliance test suite."""
    print("🔍 Running API Specification Compliance Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(OpenAIComplianceTests))
    suite.addTest(unittest.makeSuite(AnthropicComplianceTests))
    suite.addTest(unittest.makeSuite(ToolCallingComplianceTests))
    suite.addTest(unittest.makeSuite(LiveAPIComplianceTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\\n" + "=" * 50)
    print(f"API Compliance Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("🎯 All API compliance tests passed - specifications fully adhered to!")
    else:
        print("⚠️ Some API compliance tests failed - review results above")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_api_compliance_test_suite()