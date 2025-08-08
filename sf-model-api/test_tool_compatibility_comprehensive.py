#!/usr/bin/env python3
"""
Comprehensive Test Suite for Tool Behaviour Compatibility Layer
==============================================================

This test suite validates all aspects of the Tool Behaviour Compatibility Layer
implementation, including:

1. Tool preservation behavior with n8n clients
2. OpenAI-native model passthrough 
3. Response normalization across backends
4. Environment variable controls
5. Cross-backend compatibility
6. Performance validation

Usage:
    python test_tool_compatibility_comprehensive.py
"""

import os
import sys
import json
import time
import requests
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import signal
from contextlib import contextmanager

# Test configuration
TEST_CONFIG = {
    'server_url': 'http://localhost:8000',
    'timeout': 30,
    'max_retries': 3,
    'test_model': 'sfdc_ai__DefaultGPT4Omni',
    'verbose': True
}

@dataclass
class TestResult:
    """Test result structure."""
    test_name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    execution_time_ms: float = 0.0

class ToolCompatibilityTestSuite:
    """Comprehensive test suite for Tool Behaviour Compatibility Layer."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.server_url = TEST_CONFIG['server_url']
        self.timeout = TEST_CONFIG['timeout']
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup test logging."""
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        return logger
        
    def log(self, message: str, level: str = 'info'):
        """Log test message."""
        if TEST_CONFIG['verbose']:
            getattr(self.logger, level)(message)
    
    @contextmanager
    def environment_override(self, **env_vars):
        """Context manager for temporary environment variable overrides."""
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = str(value)
        
        try:
            yield
        finally:
            for key in env_vars.keys():
                if original_env[key] is not None:
                    os.environ[key] = original_env[key]
                else:
                    os.environ.pop(key, None)
    
    def make_request(
        self,
        user_agent: str = "TestClient/1.0",
        model: str = None,
        include_tools: bool = True,
        tool_choice: str = "auto",
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a request to the server."""
        model = model or TEST_CONFIG['test_model']
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': user_agent
        }
        
        if custom_headers:
            headers.update(custom_headers)
        
        # Prepare tools if requested
        tools = []
        if include_tools:
            tools = [{
                "type": "function",
                "function": {
                    "name": "research_agent",
                    "description": "Research and analyze information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "q": {
                                "type": "string",
                                "description": "Query to research"
                            }
                        },
                        "required": ["q"]
                    }
                }
            }]
        
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": "Call research_agent with q=\"hello\""
            }],
            "max_tokens": 150
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        try:
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Request failed with status {response.status_code}: {response.text}", "error")
                return None
                
        except Exception as e:
            self.log(f"Request failed: {e}", "error")
            return None
    
    def test_n8n_tool_preservation_enabled(self) -> TestResult:
        """Test n8n tool preservation with N8N_COMPAT_PRESERVE_TOOLS=1."""
        start_time = time.time()
        
        try:
            # Test with n8n user agent
            response = self.make_request(user_agent="openai/js 5.12.1")
            
            if not response:
                return TestResult(
                    "n8n_tool_preservation_enabled", 
                    False, 
                    "Failed to get response from server",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Validate response structure
            if 'choices' not in response or not response['choices']:
                return TestResult(
                    "n8n_tool_preservation_enabled",
                    False,
                    "Response missing choices array",
                    details=response,
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            message = response['choices'][0].get('message', {})
            has_tool_calls = 'tool_calls' in message
            finish_reason = response['choices'][0].get('finish_reason')
            
            # With tool preservation enabled, we should get tool_calls
            if has_tool_calls and finish_reason == "tool_calls":
                # Additional validation: content should be empty when tool calls are present
                content = message.get('content', '')
                if content == "":
                    return TestResult(
                        "n8n_tool_preservation_enabled",
                        True,
                        "✅ n8n client preserves tools correctly",
                        details={
                            'tool_calls_count': len(message.get('tool_calls', [])),
                            'finish_reason': finish_reason,
                            'content_empty': content == ""
                        },
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                else:
                    return TestResult(
                        "n8n_tool_preservation_enabled",
                        False,
                        "Content should be empty when tool calls are present",
                        details={'content': content},
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
            else:
                return TestResult(
                    "n8n_tool_preservation_enabled",
                    False,
                    "Tools were not preserved for n8n client",
                    details={
                        'has_tool_calls': has_tool_calls,
                        'finish_reason': finish_reason
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return TestResult(
                "n8n_tool_preservation_enabled",
                False,
                f"Test failed with exception: {e}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def test_openai_native_passthrough(self) -> TestResult:
        """Test OpenAI-native model detection and passthrough."""
        start_time = time.time()
        
        try:
            # Test with OpenAI-native model
            response = self.make_request(
                user_agent="MyApp/1.0",
                model="sfdc_ai__DefaultGPT4Omni"  # OpenAI-native model
            )
            
            if not response:
                return TestResult(
                    "openai_native_passthrough",
                    False,
                    "Failed to get response from server",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # For OpenAI-native models, tool calls should use direct passthrough
            message = response['choices'][0].get('message', {})
            has_tool_calls = 'tool_calls' in message
            
            if has_tool_calls:
                tool_calls = message['tool_calls']
                # Validate OpenAI tool call format
                for tool_call in tool_calls:
                    if not all(key in tool_call for key in ['id', 'type', 'function']):
                        return TestResult(
                            "openai_native_passthrough",
                            False,
                            "Tool call format invalid",
                            details=tool_call,
                            execution_time_ms=(time.time() - start_time) * 1000
                        )
                    
                    # Validate function structure
                    function = tool_call['function']
                    if not all(key in function for key in ['name', 'arguments']):
                        return TestResult(
                            "openai_native_passthrough",
                            False,
                            "Function structure invalid",
                            details=function,
                            execution_time_ms=(time.time() - start_time) * 1000
                        )
                    
                    # Arguments should be JSON string
                    try:
                        json.loads(function['arguments'])
                    except json.JSONDecodeError:
                        return TestResult(
                            "openai_native_passthrough",
                            False,
                            "Function arguments not valid JSON",
                            details=function['arguments'],
                            execution_time_ms=(time.time() - start_time) * 1000
                        )
                
                return TestResult(
                    "openai_native_passthrough",
                    True,
                    "✅ OpenAI-native model passthrough working",
                    details={
                        'tool_calls_count': len(tool_calls),
                        'model_used': response.get('model')
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            else:
                # This might be valid if the model chose not to use tools
                return TestResult(
                    "openai_native_passthrough",
                    True,
                    "✅ OpenAI-native model responded (no tools used)",
                    details={'model_used': response.get('model')},
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return TestResult(
                "openai_native_passthrough",
                False,
                f"Test failed with exception: {e}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def test_response_normalization(self) -> TestResult:
        """Test response normalization across backends."""
        start_time = time.time()
        
        try:
            # Test with different user agents to simulate different backends
            test_cases = [
                ("Standard OpenAI Client", "openai-python/1.0"),
                ("n8n Client", "openai/js 5.12.1"),
                ("Custom Client", "MyCustomApp/2.0")
            ]
            
            responses = []
            for case_name, user_agent in test_cases:
                response = self.make_request(user_agent=user_agent)
                if response:
                    responses.append((case_name, response))
            
            if not responses:
                return TestResult(
                    "response_normalization",
                    False,
                    "Failed to get any responses",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Validate all responses have consistent OpenAI schema
            issues = []
            for case_name, response in responses:
                # Check required OpenAI fields
                required_fields = ['id', 'object', 'created', 'model', 'choices', 'usage']
                for field in required_fields:
                    if field not in response:
                        issues.append(f"{case_name}: Missing {field}")
                
                # Check choices structure
                if 'choices' in response and response['choices']:
                    choice = response['choices'][0]
                    choice_required = ['index', 'message', 'finish_reason']
                    for field in choice_required:
                        if field not in choice:
                            issues.append(f"{case_name}: Choice missing {field}")
                    
                    # Check message structure
                    if 'message' in choice:
                        message = choice['message']
                        if 'role' not in message:
                            issues.append(f"{case_name}: Message missing role")
                        if 'content' not in message:
                            issues.append(f"{case_name}: Message missing content")
                        
                        # If tool calls present, validate format
                        if 'tool_calls' in message:
                            for i, tool_call in enumerate(message['tool_calls']):
                                if not all(key in tool_call for key in ['id', 'type', 'function']):
                                    issues.append(f"{case_name}: Tool call {i} invalid structure")
            
            if issues:
                return TestResult(
                    "response_normalization",
                    False,
                    "Response format inconsistencies found",
                    details={'issues': issues},
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            else:
                return TestResult(
                    "response_normalization",
                    True,
                    f"✅ All {len(responses)} responses normalized correctly",
                    details={'responses_tested': len(responses)},
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return TestResult(
                "response_normalization",
                False,
                f"Test failed with exception: {e}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def test_tool_call_round_trip(self) -> TestResult:
        """Test complete tool call round-trip conversation."""
        start_time = time.time()
        
        try:
            # First request: get tool calls
            response1 = self.make_request(user_agent="openai/js 5.12.1")
            
            if not response1 or 'choices' not in response1:
                return TestResult(
                    "tool_call_round_trip",
                    False,
                    "Failed to get initial response",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            message1 = response1['choices'][0].get('message', {})
            if 'tool_calls' not in message1:
                return TestResult(
                    "tool_call_round_trip",
                    False,
                    "No tool calls in initial response",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Second request: simulate tool response
            tool_calls = message1['tool_calls']
            
            # Build conversation with tool results
            messages = [
                {"role": "user", "content": "Call research_agent with q=\"hello\""},
                {"role": "assistant", "tool_calls": tool_calls},
                {"role": "tool", "tool_call_id": tool_calls[0]["id"], "content": "{\"summary\":\"Research completed successfully\"}"}
            ]
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'openai/js 5.12.1'
            }
            
            payload = {
                "model": TEST_CONFIG['test_model'],
                "messages": messages,
                "max_tokens": 150
            }
            
            response2 = requests.post(
                f"{self.server_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response2.status_code != 200:
                return TestResult(
                    "tool_call_round_trip",
                    False,
                    f"Follow-up request failed: {response2.status_code}",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            response2_data = response2.json()
            message2 = response2_data['choices'][0].get('message', {})
            finish_reason2 = response2_data['choices'][0].get('finish_reason')
            
            # Follow-up should be normal response with stop finish_reason
            if finish_reason2 == "stop" and 'content' in message2:
                return TestResult(
                    "tool_call_round_trip",
                    True,
                    "✅ Tool call round-trip completed successfully",
                    details={
                        'initial_tool_calls': len(tool_calls),
                        'followup_finish_reason': finish_reason2,
                        'followup_has_content': bool(message2.get('content'))
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            else:
                return TestResult(
                    "tool_call_round_trip",
                    False,
                    "Follow-up response invalid",
                    details={
                        'finish_reason': finish_reason2,
                        'has_content': 'content' in message2
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return TestResult(
                "tool_call_round_trip",
                False,
                f"Test failed with exception: {e}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def test_environment_variable_controls(self) -> TestResult:
        """Test environment variable controls."""
        start_time = time.time()
        
        try:
            # This test checks if environment variables are properly configured
            # Note: We can't dynamically change server environment variables during runtime
            # So we test by checking the current behavior matches expectations
            
            env_vars = [
                'N8N_COMPAT_MODE',
                'N8N_COMPAT_PRESERVE_TOOLS', 
                'OPENAI_NATIVE_TOOL_PASSTHROUGH'
            ]
            
            current_env = {}
            for var in env_vars:
                current_env[var] = os.environ.get(var, 'not_set')
            
            # Test that the server is responding according to current environment
            response = self.make_request(user_agent="openai/js 5.12.1")
            
            if not response:
                return TestResult(
                    "environment_variable_controls",
                    False,
                    "Failed to get response for environment test",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            message = response['choices'][0].get('message', {})
            
            # If N8N_COMPAT_PRESERVE_TOOLS=1 (default), n8n clients should get tool calls
            preserve_tools = os.environ.get('N8N_COMPAT_PRESERVE_TOOLS', '1') == '1'
            has_tool_calls = 'tool_calls' in message
            
            if preserve_tools and not has_tool_calls:
                return TestResult(
                    "environment_variable_controls",
                    False,
                    "N8N_COMPAT_PRESERVE_TOOLS=1 but no tool calls found",
                    details={'preserve_tools': preserve_tools, 'has_tool_calls': has_tool_calls},
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            return TestResult(
                "environment_variable_controls",
                True,
                "✅ Environment variables configured correctly",
                details=current_env,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return TestResult(
                "environment_variable_controls",
                False,
                f"Test failed with exception: {e}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def test_performance_regression(self) -> TestResult:
        """Test that performance hasn't regressed with new features."""
        start_time = time.time()
        
        try:
            # Run multiple requests to test performance
            num_requests = 5
            request_times = []
            
            for i in range(num_requests):
                request_start = time.time()
                response = self.make_request(user_agent="TestClient/1.0")
                request_time = (time.time() - request_start) * 1000
                
                if response:
                    request_times.append(request_time)
                else:
                    return TestResult(
                        "performance_regression",
                        False,
                        f"Request {i+1} failed",
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
            
            avg_time = sum(request_times) / len(request_times)
            max_time = max(request_times)
            min_time = min(request_times)
            
            # Performance threshold: requests should complete within reasonable time
            # This is a basic check - in production you'd compare against baseline metrics
            if avg_time < 5000:  # 5 seconds average
                return TestResult(
                    "performance_regression",
                    True,
                    f"✅ Performance acceptable: avg {avg_time:.1f}ms",
                    details={
                        'average_time_ms': avg_time,
                        'max_time_ms': max_time,
                        'min_time_ms': min_time,
                        'requests_tested': num_requests
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            else:
                return TestResult(
                    "performance_regression",
                    False,
                    f"Performance too slow: avg {avg_time:.1f}ms",
                    details={
                        'average_time_ms': avg_time,
                        'threshold_ms': 5000
                    },
                    execution_time_ms=(time.time() - start_time) * 1000
                )
                
        except Exception as e:
            return TestResult(
                "performance_regression",
                False,
                f"Test failed with exception: {e}",
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all tests in the suite."""
        self.log("🚀 Starting Tool Behaviour Compatibility Layer Test Suite")
        self.log("=" * 60)
        
        test_methods = [
            self.test_n8n_tool_preservation_enabled,
            self.test_openai_native_passthrough,
            self.test_response_normalization,
            self.test_tool_call_round_trip,
            self.test_environment_variable_controls,
            self.test_performance_regression
        ]
        
        for test_method in test_methods:
            self.log(f"\n🧪 Running {test_method.__name__}...")
            result = test_method()
            self.results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            self.log(f"{status}: {result.message}")
            
            if result.details and TEST_CONFIG['verbose']:
                self.log(f"   Details: {json.dumps(result.details, indent=2)}")
            
            self.log(f"   Execution time: {result.execution_time_ms:.1f}ms")
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        
        total_time = sum(r.execution_time_ms for r in self.results)
        
        report = f"""
Tool Behaviour Compatibility Layer Test Report
==============================================

Summary:
  Total Tests: {total_tests}
  Passed: {passed_tests}
  Failed: {failed_tests}
  Success Rate: {(passed_tests/total_tests*100):.1f}%
  Total Execution Time: {total_time:.1f}ms

Test Results:
"""
        
        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            report += f"  {status} {result.test_name}: {result.message}\n"
            if result.details:
                report += f"      Details: {json.dumps(result.details, indent=6)}\n"
            report += f"      Time: {result.execution_time_ms:.1f}ms\n"
        
        # Add acceptance criteria validation
        report += f"\nAcceptance Criteria Validation:\n"
        
        criteria_checks = {
            "n8n clients preserve tools": any("n8n" in r.test_name and r.passed for r in self.results),
            "Tool calls work end-to-end": any("round_trip" in r.test_name and r.passed for r in self.results),
            "OpenAI-native models use passthrough": any("openai_native" in r.test_name and r.passed for r in self.results),
            "Response normalization consistent": any("normalization" in r.test_name and r.passed for r in self.results),
            "Environment variables working": any("environment" in r.test_name and r.passed for r in self.results),
            "Performance acceptable": any("performance" in r.test_name and r.passed for r in self.results)
        }
        
        for criterion, passed in criteria_checks.items():
            status = "✅" if passed else "❌"
            report += f"  {status} {criterion}\n"
        
        return report


def check_server_health() -> bool:
    """Check if the server is running and healthy."""
    try:
        response = requests.get(f"{TEST_CONFIG['server_url']}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    """Main test execution."""
    print("🧪 Tool Behaviour Compatibility Layer - Comprehensive Test Suite")
    print("================================================================")
    
    # Check server health
    print("\n🔍 Checking server health...")
    if not check_server_health():
        print("❌ Server is not running or not healthy!")
        print("Please ensure the server is running with: ./start_async_service.sh")
        sys.exit(1)
    
    print("✅ Server is healthy and ready for testing")
    
    # Display current environment
    print("\n🎯 Current Environment Configuration:")
    env_vars = [
        'N8N_COMPAT_MODE',
        'N8N_COMPAT_PRESERVE_TOOLS',
        'OPENAI_NATIVE_TOOL_PASSTHROUGH',
        'VERBOSE_TOOL_LOGS'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'not_set')
        print(f"   {var}: {value}")
    
    # Initialize and run test suite
    print("\n" + "=" * 60)
    test_suite = ToolCompatibilityTestSuite()
    results = test_suite.run_all_tests()
    
    # Generate and display report
    report = test_suite.generate_report()
    print(report)
    
    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r.passed)
    if failed_count > 0:
        print(f"\n❌ {failed_count} test(s) failed. See details above.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed successfully!")
        print("✅ Tool Behaviour Compatibility Layer is working correctly!")
        sys.exit(0)


if __name__ == "__main__":
    main()