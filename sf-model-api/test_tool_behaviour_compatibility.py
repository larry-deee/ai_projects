#!/usr/bin/env python3
"""
Test Tool Behaviour Compatibility Layer
======================================

Comprehensive validation suite for the new Tool Behaviour Compatibility Layer
that preserves tools for n8n clients while implementing smart model routing
and response normalization.

Tests:
1. n8n tool preservation with N8N_COMPAT_PRESERVE_TOOLS=1 (default)
2. n8n tool preservation with N8N_COMPAT_PRESERVE_TOOLS=0 (legacy mode)
3. OpenAI-native model detection and passthrough
4. Response normalization for non-native models
5. Environment variable controls
6. Backwards compatibility

Usage:
    python test_tool_behaviour_compatibility.py
"""

import os
import json
import time
import requests
import logging
from typing import Dict, Any, List
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
SERVER_URL = "http://localhost:8000"
TEST_TIMEOUT = 30

class ToolCompatibilityTester:
    """Comprehensive tester for Tool Behaviour Compatibility Layer."""
    
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url
        self.results = []
        
    @contextmanager
    def environment_override(self, **env_vars):
        """Context manager to temporarily override environment variables."""
        original_values = {}
        for key, value in env_vars.items():
            original_values[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)
        
        try:
            yield
        finally:
            for key, original_value in original_values.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def make_request(
        self,
        user_agent: str,
        model: str = "claude-3-haiku",
        include_tools: bool = True,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Make a test request with specified parameters."""
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": user_agent
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "What is the weather like?"}
            ],
            "max_tokens": 150,
            "temperature": 0.7,
            "stream": stream
        }
        
        if include_tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get current weather information",
                        "parameters": {
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
                }
            ]
            payload["tool_choice"] = "auto"
        
        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=TEST_TIMEOUT
            )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response.json() if response.status_code == 200 else {"error": response.text},
                "success": response.status_code == 200
            }
        except Exception as e:
            return {
                "status_code": 0,
                "headers": {},
                "data": {"error": str(e)},
                "success": False
            }
    
    def test_n8n_tool_preservation_enabled(self):
        """Test n8n tool preservation with N8N_COMPAT_PRESERVE_TOOLS=1."""
        logger.info("🧪 Testing n8n tool preservation (enabled)...")
        
        with self.environment_override(N8N_COMPAT_PRESERVE_TOOLS="1"):
            # Test with n8n user agent
            result = self.make_request(
                user_agent="n8n/1.0",
                model="claude-3-haiku",
                include_tools=True,
                stream=False
            )
            
            test_passed = (
                result["success"] and
                result["headers"].get("x-stream-downgraded") == "false" and  # No streaming downgrade needed
                "choices" in result["data"]
            )
            
            self.results.append({
                "test": "n8n_tool_preservation_enabled",
                "passed": test_passed,
                "details": {
                    "status_code": result["status_code"],
                    "stream_downgraded": result["headers"].get("x-stream-downgraded"),
                    "has_response": "choices" in result["data"],
                    "error": result["data"].get("error") if not result["success"] else None
                }
            })
            
            logger.info(f"✅ n8n tool preservation (enabled): {'PASSED' if test_passed else 'FAILED'}")
            return test_passed
    
    def test_n8n_tool_preservation_disabled(self):
        """Test n8n legacy behavior with N8N_COMPAT_PRESERVE_TOOLS=0."""
        logger.info("🧪 Testing n8n legacy tool ignoring (disabled)...")
        
        with self.environment_override(N8N_COMPAT_PRESERVE_TOOLS="0"):
            result = self.make_request(
                user_agent="n8n/1.0",
                model="claude-3-haiku", 
                include_tools=True,
                stream=False
            )
            
            # Should work but tools should be ignored (legacy behavior)
            test_passed = (
                result["success"] and
                "choices" in result["data"]
            )
            
            self.results.append({
                "test": "n8n_tool_preservation_disabled",
                "passed": test_passed,
                "details": {
                    "status_code": result["status_code"],
                    "has_response": "choices" in result["data"],
                    "error": result["data"].get("error") if not result["success"] else None
                }
            })
            
            logger.info(f"✅ n8n legacy behavior: {'PASSED' if test_passed else 'FAILED'}")
            return test_passed
    
    def test_openai_native_detection(self):
        """Test OpenAI-native model detection and passthrough."""
        logger.info("🧪 Testing OpenAI-native model detection...")
        
        with self.environment_override(OPENAI_NATIVE_TOOL_PASSTHROUGH="1"):
            # Test with OpenAI-native model
            result = self.make_request(
                user_agent="MyApp/1.0",
                model="gpt-4",  # Should be detected as OpenAI-native
                include_tools=True,
                stream=False
            )
            
            test_passed = (
                result["success"] and
                "choices" in result["data"]
            )
            
            self.results.append({
                "test": "openai_native_detection",
                "passed": test_passed,
                "details": {
                    "status_code": result["status_code"],
                    "model": "gpt-4",
                    "has_response": "choices" in result["data"],
                    "error": result["data"].get("error") if not result["success"] else None
                }
            })
            
            logger.info(f"✅ OpenAI-native detection: {'PASSED' if test_passed else 'FAILED'}")
            return test_passed
    
    def test_openai_js_compatibility(self):
        """Test openai/js client compatibility."""
        logger.info("🧪 Testing openai/js client compatibility...")
        
        result = self.make_request(
            user_agent="openai/js-1.0.0",
            model="claude-3-haiku",
            include_tools=True,
            stream=False
        )
        
        test_passed = (
            result["success"] and
            result["headers"].get("x-stream-downgraded") == "false" and
            "choices" in result["data"]
        )
        
        self.results.append({
            "test": "openai_js_compatibility", 
            "passed": test_passed,
            "details": {
                "status_code": result["status_code"],
                "user_agent": "openai/js-1.0.0",
                "stream_downgraded": result["headers"].get("x-stream-downgraded"),
                "has_response": "choices" in result["data"],
                "error": result["data"].get("error") if not result["success"] else None
            }
        })
        
        logger.info(f"✅ openai/js compatibility: {'PASSED' if test_passed else 'FAILED'}")
        return test_passed
    
    def test_regular_client_unchanged(self):
        """Test that regular clients (non-n8n) are unchanged."""
        logger.info("🧪 Testing regular client unchanged behavior...")
        
        result = self.make_request(
            user_agent="MyApp/1.0",
            model="claude-3-haiku",
            include_tools=True,
            stream=False
        )
        
        test_passed = (
            result["success"] and
            "choices" in result["data"]
        )
        
        self.results.append({
            "test": "regular_client_unchanged",
            "passed": test_passed,
            "details": {
                "status_code": result["status_code"],
                "user_agent": "MyApp/1.0",
                "has_response": "choices" in result["data"],
                "error": result["data"].get("error") if not result["success"] else None
            }
        })
        
        logger.info(f"✅ Regular client unchanged: {'PASSED' if test_passed else 'FAILED'}")
        return test_passed
    
    def test_streaming_behavior(self):
        """Test streaming behavior with tool preservation."""
        logger.info("🧪 Testing streaming behavior...")
        
        # n8n should have streaming disabled
        result = self.make_request(
            user_agent="n8n/1.0",
            model="claude-3-haiku",
            include_tools=True,
            stream=True  # Requested, but should be downgraded
        )
        
        test_passed = (
            result["success"] and
            result["headers"].get("x-stream-downgraded") == "true" and  # Should be downgraded
            "choices" in result["data"]
        )
        
        self.results.append({
            "test": "streaming_behavior",
            "passed": test_passed,
            "details": {
                "status_code": result["status_code"],
                "stream_requested": True,
                "stream_downgraded": result["headers"].get("x-stream-downgraded"),
                "has_response": "choices" in result["data"],
                "error": result["data"].get("error") if not result["success"] else None
            }
        })
        
        logger.info(f"✅ Streaming behavior: {'PASSED' if test_passed else 'FAILED'}")
        return test_passed
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all compatibility tests and return comprehensive results."""
        logger.info("🚀 Starting Tool Behaviour Compatibility Layer tests...")
        start_time = time.time()
        
        # Run all test methods
        test_methods = [
            self.test_n8n_tool_preservation_enabled,
            self.test_n8n_tool_preservation_disabled,
            self.test_openai_native_detection,
            self.test_openai_js_compatibility,
            self.test_regular_client_unchanged,
            self.test_streaming_behavior
        ]
        
        passed_tests = 0
        for test_method in test_methods:
            try:
                if test_method():
                    passed_tests += 1
            except Exception as e:
                logger.error(f"❌ Test {test_method.__name__} failed with exception: {e}")
                self.results.append({
                    "test": test_method.__name__,
                    "passed": False,
                    "details": {"exception": str(e)}
                })
        
        total_tests = len(test_methods)
        test_duration = time.time() - start_time
        
        # Generate summary report
        summary = {
            "test_suite": "Tool Behaviour Compatibility Layer",
            "timestamp": time.time(),
            "duration_seconds": test_duration,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "all_tests_passed": passed_tests == total_tests,
            "detailed_results": self.results
        }
        
        # Log summary
        logger.info(f"🏁 Test Summary: {passed_tests}/{total_tests} passed ({summary['success_rate']:.1f}%)")
        if summary["all_tests_passed"]:
            logger.info("🎉 All Tool Behaviour Compatibility Layer tests PASSED!")
        else:
            logger.warning(f"⚠️  {summary['failed_tests']} tests FAILED - review implementation")
        
        return summary

def main():
    """Main test execution function."""
    logger.info("Tool Behaviour Compatibility Layer Test Suite")
    logger.info("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error(f"❌ Server health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Cannot reach server at {SERVER_URL}: {e}")
        logger.error("Please ensure the server is running: python src/async_endpoint_server.py")
        return False
    
    # Run tests
    tester = ToolCompatibilityTester(SERVER_URL)
    results = tester.run_all_tests()
    
    # Save detailed results
    with open("tool_compatibility_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"📊 Detailed results saved to: tool_compatibility_test_results.json")
    
    return results["all_tests_passed"]

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)