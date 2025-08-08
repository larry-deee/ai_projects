#!/usr/bin/env python3
"""
n8n Client Compatibility Test Suite
===================================

Comprehensive test suite validating n8n client compatibility with the Salesforce
Models API Gateway. Tests all n8n-specific functionality including $fromAI() 
parameter extraction, workflow integration patterns, and error handling.

Tests cover:
- $fromAI() parameter extraction and processing
- n8n-specific HTTP headers and content-type validation
- Tool calling with n8n workflow patterns
- JSON parsing recovery mechanisms
- Timeout handling and error response formats
- Parameter mapping and automatic value determination
"""

import json
import time
import unittest
import requests
import concurrent.futures
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Import project modules
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from tool_handler import ToolCallingHandler, ToolCallingConfig
    from unified_response_formatter import UnifiedResponseFormatter
    from salesforce_models_client import SalesforceModelsClient
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


class N8nCompatibilityTests(unittest.TestCase):
    """Test suite for n8n client compatibility validation."""
    
    def setUp(self):
        """Set up test fixtures and mock responses."""
        self.server_url = "http://localhost:8000"
        self.test_timeout = 30
        
        # Mock n8n workflow data
        self.n8n_test_data = {
            'simple_extraction': {
                "model": "claude-3-haiku",
                "messages": [{
                    "role": "user", 
                    "content": "Extract contact info from: John Smith john@example.com"
                }],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "extract_contact",
                        "description": "Extract contact information",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Parameter value will be determined by the model automatically"
                                },
                                "email": {
                                    "type": "string", 
                                    "description": "Parameter value will be determined by the model automatically"
                                }
                            },
                            "required": ["name", "email"]
                        }
                    }
                }]
            },
            'fromai_parameters': {
                "model": "claude-3-haiku",
                "messages": [{
                    "role": "user",
                    "content": "Send email to {{ $fromAI('recipient', 'john@example.com', 'string') }} with subject {{ $fromAI('subject', 'Default Subject', 'string') }}"
                }],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "send_email",
                        "description": "Send an email",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "recipient": {
                                    "type": "string",
                                    "description": "$fromAI('recipient', 'default@example.com', 'string')"
                                },
                                "subject": {
                                    "type": "string",
                                    "description": "$fromAI('subject', 'Default Subject', 'string')"
                                }
                            },
                            "required": ["recipient", "subject"]
                        }
                    }
                }]
            },
            'complex_workflow': {
                "model": "claude-3-haiku", 
                "messages": [{
                    "role": "user",
                    "content": "Process order for customer Sarah Wilson (sarah.w@company.com) - Order ID: ORD-12345, Amount: $250.99"
                }],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "process_order",
                        "description": "Process customer order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "customer_name": {
                                    "type": "string",
                                    "description": "Parameter value will be determined by the model automatically"
                                },
                                "customer_email": {
                                    "type": "string", 
                                    "description": "Parameter value will be determined by the model automatically"
                                },
                                "order_id": {
                                    "type": "string",
                                    "description": "Parameter value will be determined by the model automatically"
                                },
                                "amount": {
                                    "type": "string",
                                    "description": "Parameter value will be determined by the model automatically"
                                }
                            },
                            "required": ["customer_name", "customer_email", "order_id", "amount"]
                        }
                    }
                }]
            }
        }
        
        # Expected n8n response headers
        self.expected_n8n_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Access-Control-Allow-Origin': '*',
            'X-Content-Type-Options': 'nosniff'
        }
    
    def test_n8n_fromai_parameter_extraction(self):
        """Test n8n $fromAI() parameter extraction patterns."""
        formatter = UnifiedResponseFormatter()
        config = ToolCallingConfig()
        handler = ToolCallingHandler(config)
        
        test_content = "Send email to {{ $fromAI('recipient', 'john@example.com', 'string') }} with subject {{ $fromAI('subject', 'Meeting Tomorrow', 'string') }}"
        
        # Process n8n user message
        processed_content = handler._process_n8n_user_message(
            test_content, 
            self.n8n_test_data['fromai_parameters']['tools']
        )
        
        # Verify $fromAI patterns are converted to contextual markers
        self.assertIn('[AUTO_PARAM:recipient', processed_content)
        self.assertIn('[AUTO_PARAM:subject', processed_content)
        self.assertIn('[CONTEXT:', processed_content)
        
        print(f"✅ n8n parameter extraction test passed")
        print(f"   Original: {test_content[:50]}...")
        print(f"   Processed: {processed_content[:100]}...")
    
    def test_n8n_parameter_extraction_hints(self):
        """Test parameter extraction hint generation."""
        config = ToolCallingConfig()
        handler = ToolCallingHandler(config)
        
        test_content = "Process {{ $fromAI('operation', 'calculate', 'string') }} with {{ $fromAI('value', '100', 'number') }}"
        tools = [{
            "function": {
                "name": "math_operation",
                "parameters": {
                    "properties": {
                        "operation": {
                            "type": "string",
                            "description": "$fromAI('operation', 'add', 'string')"
                        },
                        "value": {
                            "type": "number", 
                            "description": "$fromAI('value', '0', 'number')"
                        }
                    },
                    "required": ["operation", "value"]
                }
            }
        }]
        
        hints = handler._generate_parameter_extraction_hints(test_content, tools)
        
        self.assertIn("automatic parameters", hints.lower())
        self.assertIn("operation", hints)
        self.assertIn("value", hints) 
        self.assertIn("context analysis", hints.lower())
        
        print(f"✅ Parameter extraction hints test passed")
        print(f"   Generated {len(hints.split(chr(10)))} hint lines")
    
    def test_n8n_contextual_parameter_extraction(self):
        """Test contextual extraction of parameters from user content."""
        config = ToolCallingConfig()
        handler = ToolCallingHandler(config)
        
        test_cases = [
            {
                'content': 'Send email to john.doe@company.com about the quarterly report',
                'param_name': 'email',
                'param_type': 'string',
                'expected_contains': 'john.doe@company.com'
            },
            {
                'content': 'Contact Sarah Wilson at the office',
                'param_name': 'name',
                'param_type': 'string',
                'expected_contains': 'Sarah Wilson'
            },
            {
                'content': 'Operation should be multiply and value is 42',
                'param_name': 'operation',
                'param_type': 'string', 
                'expected_contains': 'multiply'
            }
        ]
        
        for test_case in test_cases:
            extracted = handler._contextual_extraction(
                test_case['param_name'],
                test_case['param_type'],
                test_case['content']
            )
            
            if extracted:
                self.assertIsInstance(extracted, str)
                if test_case.get('expected_contains'):
                    self.assertIn(test_case['expected_contains'], extracted)
            
            print(f"✅ Contextual extraction for '{test_case['param_name']}': {extracted}")
    
    def test_n8n_automatic_parameter_defaults(self):
        """Test generation of default values for n8n parameters."""
        config = ToolCallingConfig()
        handler = ToolCallingHandler(config)
        
        test_cases = [
            ('system_message', 'string', 'User wants to process data'),
            ('count', 'number', 'Count the items'),
            ('enabled', 'boolean', 'Should this be enabled?')
        ]
        
        for param_name, param_type, content in test_cases:
            default_value = handler._generate_default_value(param_name, param_type, content)
            
            self.assertIsInstance(default_value, str)
            self.assertTrue(len(default_value) > 0)
            
            # Type-specific validations
            if param_type == 'number':
                try:
                    float(default_value)
                except ValueError:
                    self.fail(f"Number parameter {param_name} generated non-numeric default: {default_value}")
            elif param_type == 'boolean':
                self.assertIn(default_value.lower(), ['true', 'false'])
            
            print(f"✅ Default generation for {param_name} ({param_type}): {default_value}")
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
    )
    def test_n8n_live_tool_calling(self):
        """Integration test for n8n tool calling with live server."""
        try:
            # Test simple n8n-style tool calling
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=self.n8n_test_data['simple_extraction'],
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Validate n8n headers
            for header, expected_value in self.expected_n8n_headers.items():
                if header in response.headers:
                    if header == 'Content-Type':
                        self.assertTrue(response.headers[header].startswith(expected_value.split(';')[0]))
                    else:
                        self.assertEqual(response.headers[header], expected_value)
            
            # Validate response structure
            json_response = response.json()
            self.assertIn('choices', json_response)
            self.assertIn('usage', json_response)
            self.assertEqual(json_response['object'], 'chat.completion')
            
            # Check for tool calls in response
            message = json_response['choices'][0]['message']
            if 'tool_calls' in message:
                tool_calls = message['tool_calls']
                self.assertIsInstance(tool_calls, list)
                self.assertGreater(len(tool_calls), 0)
                
                # Validate tool call structure
                for tool_call in tool_calls:
                    self.assertIn('id', tool_call)
                    self.assertIn('type', tool_call)
                    self.assertEqual(tool_call['type'], 'function')
                    self.assertIn('function', tool_call)
                    
                    function = tool_call['function']
                    self.assertIn('name', function)
                    self.assertIn('arguments', function)
                    
                    # Validate arguments is valid JSON
                    arguments = json.loads(function['arguments'])
                    self.assertIsInstance(arguments, dict)
            
            print(f"✅ n8n live tool calling test passed")
            print(f"   Status: {response.status_code}")
            print(f"   Content-Type: {response.headers.get('Content-Type')}")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available for integration test: {e}")
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
    )
    def test_n8n_fromai_parameter_live_test(self):
        """Live test of $fromAI() parameter processing."""
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=self.n8n_test_data['fromai_parameters'], 
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            json_response = response.json()
            
            # Verify response has appropriate structure
            self.assertIn('choices', json_response)
            message = json_response['choices'][0]['message']
            
            # Should have either content or tool_calls (or both)
            has_content = message.get('content') and len(message['content'].strip()) > 0
            has_tool_calls = 'tool_calls' in message and len(message['tool_calls']) > 0
            
            self.assertTrue(has_content or has_tool_calls, 
                          "Response should have either content or tool calls")
            
            # If tool calls present, validate parameter extraction worked
            if has_tool_calls:
                tool_calls = message['tool_calls']
                for tool_call in tool_calls:
                    arguments = json.loads(tool_call['function']['arguments'])
                    
                    # Check that parameters were extracted/provided
                    if tool_call['function']['name'] == 'send_email':
                        self.assertIn('recipient', arguments)
                        self.assertIn('subject', arguments)
                        
                        # Values should not be empty
                        self.assertTrue(len(arguments['recipient']) > 0)
                        self.assertTrue(len(arguments['subject']) > 0)
                        
                        print(f"✅ Extracted recipient: {arguments['recipient']}")
                        print(f"✅ Extracted subject: {arguments['subject']}")
            
            print(f"✅ n8n $fromAI() live test passed")
            
        except requests.RequestException as e:
            self.skipTest(f"Server not available for integration test: {e}")
    
    def test_n8n_error_response_format(self):
        """Test n8n-compatible error response formatting."""
        formatter = UnifiedResponseFormatter()
        
        test_errors = [
            "Invalid tool configuration",
            "Parameter extraction failed", 
            "Rate limit exceeded",
            "Authentication failed"
        ]
        
        for error_msg in test_errors:
            error_response = formatter.format_error_response(
                error_msg, 
                model="claude-3-haiku"
            )
            
            # Validate error structure
            self.assertIn('error', error_response)
            error = error_response['error']
            
            self.assertIn('message', error)
            self.assertIn('type', error)
            self.assertIn('code', error)
            self.assertEqual(error['message'], error_msg)
            
            # Validate it's JSON serializable (important for n8n)
            try:
                json_str = json.dumps(error_response)
                self.assertIsInstance(json_str, str)
                self.assertGreater(len(json_str), 0)
            except (TypeError, ValueError) as e:
                self.fail(f"Error response not JSON serializable: {e}")
        
        print(f"✅ n8n error response format test passed")
    
    def test_n8n_content_type_validation(self):
        """Test content-type validation for n8n compatibility."""
        # n8n requires specific content-type format
        expected_content_type = 'application/json; charset=utf-8'
        
        # Mock response object
        class MockResponse:
            def __init__(self):
                self.headers = {}
        
        # Test header addition function if available
        try:
            from async_endpoint_server import add_n8n_compatible_headers
            
            mock_response = MockResponse()
            result = add_n8n_compatible_headers(mock_response)
            
            self.assertEqual(result.headers['Content-Type'], expected_content_type)
            self.assertEqual(result.headers['Access-Control-Allow-Origin'], '*')
            self.assertIn('Cache-Control', result.headers)
            
            print(f"✅ n8n content-type validation passed")
            
        except ImportError:
            self.skipTest("n8n header function not available")
    
    def test_n8n_json_parsing_recovery(self):
        """Test JSON parsing recovery mechanisms."""
        formatter = UnifiedResponseFormatter()
        
        # Test malformed JSON responses
        malformed_responses = [
            '{"incomplete": true',  # Missing closing brace
            'Not JSON at all',      # Plain text
            '',                     # Empty response
            '{"nested": {"incomplete": true}',  # Nested incomplete
        ]
        
        for malformed_json in malformed_responses:
            # Test that formatter handles malformed JSON gracefully
            try:
                # This would normally be called with a dict, but test error handling
                result = formatter.extract_response_text({'generation': {'generatedText': malformed_json}})
                
                # Should still return a string result
                self.assertIsInstance(result.text if hasattr(result, 'text') else result, str)
                
            except Exception as e:
                # Should not raise unhandled exceptions
                self.fail(f"Unhandled exception for malformed JSON '{malformed_json}': {e}")
        
        print(f"✅ JSON parsing recovery test passed")
    
    @unittest.skipUnless(
        os.environ.get('PERFORMANCE_TESTS') == 'true',
        "Performance tests disabled. Set PERFORMANCE_TESTS=true to run."
    )
    def test_n8n_concurrent_requests(self):
        """Test concurrent n8n requests for performance validation."""
        if not os.environ.get('INTEGRATION_TESTS') == 'true':
            self.skipTest("Integration tests required for concurrent testing")
        
        concurrent_requests = 5
        test_payload = self.n8n_test_data['simple_extraction']
        
        def make_request():
            try:
                response = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    json=test_payload,
                    timeout=self.test_timeout
                )
                return {
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'success': response.status_code == 200
                }
            except Exception as e:
                return {
                    'status_code': 0,
                    'response_time': 0,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        avg_response_time = sum(r['response_time'] for r in results if r['success']) / max(successful_requests, 1)
        
        # Validate performance
        self.assertGreaterEqual(successful_requests, concurrent_requests * 0.8)  # 80% success rate
        self.assertLess(avg_response_time, 10.0)  # Under 10 seconds average
        
        print(f"✅ Concurrent n8n requests test passed")
        print(f"   Successful requests: {successful_requests}/{concurrent_requests}")
        print(f"   Average response time: {avg_response_time:.2f}s")
    
    def test_n8n_timeout_handling(self):
        """Test timeout handling for n8n requests."""
        formatter = UnifiedResponseFormatter()
        
        # Simulate timeout scenarios
        timeout_response = formatter.format_error_response(
            "Request timeout occurred",
            error_type="timeout_error",
            model="claude-3-haiku"
        )
        
        # Validate timeout error structure
        self.assertIn('error', timeout_response)
        error = timeout_response['error']
        
        self.assertEqual(error['type'], 'timeout_error')
        self.assertIn('timeout', error['message'].lower())
        self.assertIn('suggestion', error.get('details', {}))
        
        # Suggestion should be helpful for n8n users
        suggestion = error.get('details', {}).get('suggestion', '')
        self.assertTrue(len(suggestion) > 0)
        self.assertIn('try', suggestion.lower())
        
        print(f"✅ n8n timeout handling test passed")
        print(f"   Error type: {error['type']}")
        print(f"   Suggestion: {suggestion}")


class N8nToolCallingValidation(unittest.TestCase):
    """Specialized tests for n8n tool calling validation."""
    
    def setUp(self):
        """Set up tool calling test fixtures."""
        self.config = ToolCallingConfig()
        self.handler = ToolCallingHandler(self.config)
        
        # n8n-specific tool definition
        self.n8n_tool = {
            "type": "function",
            "function": {
                "name": "extract_data",
                "description": "Extract data from text using n8n patterns",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "extracted_text": {
                            "type": "string",
                            "description": "Parameter value will be determined by the model automatically"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence score (0-1)"
                        }
                    },
                    "required": ["extracted_text"]
                }
            }
        }
    
    def test_n8n_tool_validation(self):
        """Test validation of n8n-style tool definitions."""
        # Validate tool definition
        validated_tools = self.handler._validate_and_parse_tools([self.n8n_tool])
        
        self.assertEqual(len(validated_tools), 1)
        tool = validated_tools[0]
        
        # Verify function structure
        self.assertTrue(hasattr(tool, 'function'))
        self.assertEqual(tool.function.name, 'extract_data')
        self.assertTrue(hasattr(tool.function, 'parameters'))
        
        # Verify parameters
        params = tool.function.parameters
        self.assertIn('extracted_text', params.properties)
        self.assertIn('confidence', params.properties)
        
        print(f"✅ n8n tool validation passed")
    
    def test_n8n_tool_call_parsing(self):
        """Test parsing of tool calls in n8n format."""
        # Mock response text with tool call
        response_text = """I'll extract the data for you.

TOOL_CALLS:
[{
    "name": "extract_data",
    "arguments": {
        "extracted_text": "John Smith, Manager at Tech Corp",
        "confidence": 0.95
    }
}]"""
        
        tool_calls = self.handler._parse_tool_calls_from_response(
            response_text, 
            [self.handler._validate_and_parse_tools([self.n8n_tool])[0]]
        )
        
        self.assertEqual(len(tool_calls), 1)
        tool_call = tool_calls[0]
        
        # Verify tool call structure
        self.assertEqual(tool_call.function_name, 'extract_data')
        self.assertIn('extracted_text', tool_call.function_arguments)
        self.assertIn('confidence', tool_call.function_arguments)
        
        # Verify argument values
        args = tool_call.function_arguments
        self.assertIn('John Smith', args['extracted_text'])
        self.assertEqual(args['confidence'], 0.95)
        
        print(f"✅ n8n tool call parsing passed")
    
    def test_n8n_parameter_mapping(self):
        """Test parameter mapping for n8n automatic parameters."""
        test_messages = [{
            "role": "user",
            "content": "Extract contact: Sarah Davis, sarah@company.com, Product Manager"
        }]
        
        # Process with n8n tool
        validated_tools = self.handler._validate_and_parse_tools([self.n8n_tool])
        
        # Test parameter extraction
        extracted_params = self.handler._extract_automatic_parameters(
            test_messages[0]['content'],
            validated_tools
        )
        
        # Should have extracted text parameter
        self.assertIn('extracted_text', extracted_params)
        extracted_text = extracted_params['extracted_text']
        
        # Should contain relevant information
        self.assertTrue(len(extracted_text) > 0)
        
        print(f"✅ n8n parameter mapping passed")
        print(f"   Extracted: {extracted_text}")
    
    def test_n8n_error_recovery(self):
        """Test error recovery in n8n tool calling scenarios."""
        # Test with invalid tool definition
        invalid_tool = {
            "type": "function",
            "function": {
                "name": "",  # Empty name should cause validation error
                "parameters": {}
            }
        }
        
        # Should handle gracefully without crashing
        try:
            self.handler._validate_and_parse_tools([invalid_tool])
        except ValueError as e:
            # Expected validation error
            self.assertIn('tool', str(e).lower())
        except Exception as e:
            self.fail(f"Unexpected exception type: {e}")
        
        print(f"✅ n8n error recovery test passed")


def run_n8n_test_suite():
    """Run the complete n8n compatibility test suite."""
    print("🧪 Running n8n Compatibility Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(N8nCompatibilityTests))
    suite.addTest(unittest.makeSuite(N8nToolCallingValidation))
    
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
    run_n8n_test_suite()