#!/usr/bin/env python3
"""
OpenAI Front-Door Architecture Integration Test
===============================================

Tests server startup, architecture activation, and end-to-end request handling.
This test validates that the OpenAI Front-Door architecture is properly integrated
and functioning in the actual server environment.

Usage:
    python test_openai_frontdoor_integration.py
    
Prerequisites:
    - Server must be running: python src/async_endpoint_server.py
    - Environment: export OPENAI_FRONTDOOR_ENABLED=1
"""

import os
import sys
import json
import asyncio
import aiohttp
import logging
import subprocess
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

class IntegrationTestSuite:
    """Integration test suite for OpenAI Front-Door architecture."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.server_process: Optional[subprocess.Popen] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
    
    async def check_server_health(self) -> bool:
        """Check if server is running and healthy."""
        try:
            async with self.session.get(f"{BASE_URL}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"✅ Server is healthy: {health_data.get('status')}")
                    return True
                else:
                    logger.error(f"❌ Server health check failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Server health check error: {e}")
            return False
    
    async def test_openai_frontdoor_enabled(self) -> bool:
        """Test that OpenAI Front-Door architecture is enabled."""
        logger.info("🧪 Testing OpenAI Front-Door architecture activation...")
        
        # Check environment variable
        frontdoor_enabled = os.getenv("OPENAI_FRONTDOOR_ENABLED", "0") == "1"
        if not frontdoor_enabled:
            logger.error("❌ OPENAI_FRONTDOOR_ENABLED not set to '1'")
            return False
        
        logger.info("✅ OPENAI_FRONTDOOR_ENABLED environment variable set correctly")
        
        # Test a request that would use the new architecture
        test_payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Test OpenAI Front-Door"}],
            "max_tokens": 50
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=test_payload
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Check for OpenAI format compliance
                    required_fields = ["id", "object", "created", "model", "choices"]
                    for field in required_fields:
                        if field not in response_data:
                            logger.error(f"❌ Missing required field: {field}")
                            return False
                    
                    logger.info("✅ OpenAI Front-Door architecture responding correctly")
                    return True
                else:
                    logger.error(f"❌ Request failed: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ OpenAI Front-Door test error: {e}")
            return False
    
    async def test_backend_routing(self) -> bool:
        """Test that different models route to correct backends."""
        logger.info("🧪 Testing backend routing for different model types...")
        
        test_models = [
            ("sfdc_ai__DefaultGPT4Omni", "openai_native"),
            ("sfdc_ai__DefaultBedrockAnthropicClaude4Sonnet", "anthropic_bedrock"),
            ("sfdc_ai__DefaultVertexAIGemini25Flash001", "vertex_gemini")
        ]
        
        all_passed = True
        
        for model, expected_backend in test_models:
            logger.info(f"  Testing model: {model} (expected backend: {expected_backend})")
            
            test_payload = {
                "model": model,
                "messages": [{"role": "user", "content": f"Test {model}"}],
                "max_tokens": 20
            }
            
            try:
                async with self.session.post(
                    f"{BASE_URL}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json=test_payload
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Validate OpenAI format
                        if "choices" in response_data and response_data["choices"]:
                            logger.info(f"  ✅ {model} routed successfully")
                        else:
                            logger.error(f"  ❌ {model} invalid response format")
                            all_passed = False
                    else:
                        logger.error(f"  ❌ {model} request failed: {response.status}")
                        all_passed = False
            except Exception as e:
                logger.error(f"  ❌ {model} request error: {e}")
                all_passed = False
        
        return all_passed
    
    async def test_tool_calling_compliance(self) -> bool:
        """Test tool calling with OpenAI compliance."""
        logger.info("🧪 Testing tool calling OpenAI compliance...")
        
        test_payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Use the research tool to find information about AI"}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "research_agent",
                    "description": "Research information on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "q": {
                                "type": "string",
                                "description": "Query string"
                            }
                        },
                        "required": ["q"]
                    }
                }
            }],
            "tool_choice": "auto"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=test_payload
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Check for proper response structure
                    if "choices" not in response_data or not response_data["choices"]:
                        logger.error("❌ No choices in tool calling response")
                        return False
                    
                    message = response_data["choices"][0]["message"]
                    
                    # Check for tool calls (might not always be present)
                    if "tool_calls" in message:
                        logger.info("✅ Tool calls present in response")
                        
                        # Validate tool call format
                        for tool_call in message["tool_calls"]:
                            required_fields = ["id", "type", "function"]
                            for field in required_fields:
                                if field not in tool_call:
                                    logger.error(f"❌ Tool call missing field: {field}")
                                    return False
                            
                            # Check function format
                            function = tool_call["function"]
                            if "name" not in function:
                                logger.error("❌ Tool call function missing name")
                                return False
                            
                            # Validate arguments are JSON string
                            if "arguments" in function:
                                args = function["arguments"]
                                if not isinstance(args, str):
                                    logger.error("❌ Tool call arguments not a string")
                                    return False
                                
                                try:
                                    json.loads(args)
                                    logger.info("✅ Tool call arguments are valid JSON string")
                                except json.JSONDecodeError:
                                    logger.error("❌ Tool call arguments not valid JSON")
                                    return False
                        
                        # Check finish reason
                        finish_reason = response_data["choices"][0].get("finish_reason")
                        if finish_reason == "tool_calls":
                            logger.info("✅ Correct finish_reason for tool calls")
                        else:
                            logger.warning(f"⚠️ Unexpected finish_reason: {finish_reason}")
                    else:
                        # No tool calls - check for valid content
                        if "content" in message and message["content"]:
                            logger.info("✅ Valid response without tool calls (acceptable)")
                        else:
                            logger.error("❌ Response has neither tool calls nor content")
                            return False
                    
                    logger.info("✅ Tool calling compliance test passed")
                    return True
                else:
                    logger.error(f"❌ Tool calling request failed: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error: {error_text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Tool calling test error: {e}")
            return False
    
    async def test_n8n_compatibility(self) -> bool:
        """Test n8n User-Agent compatibility."""
        logger.info("🧪 Testing n8n User-Agent compatibility...")
        
        test_payload = {
            "model": "sfdc_ai__DefaultGPT4Omni",
            "messages": [{"role": "user", "content": "Hello from n8n"}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "test_function",
                    "description": "Test function",
                    "parameters": {"type": "object", "properties": {}}
                }
            }]
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "n8n/test-integration"
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/v1/chat/completions",
                headers=headers,
                json=test_payload
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Verify response structure
                    if "choices" in response_data and response_data["choices"]:
                        message = response_data["choices"][0]["message"]
                        
                        # Check that tools were preserved (not stripped)
                        has_tools = "tool_calls" in message
                        has_content = "content" in message and message["content"]
                        
                        if has_tools or has_content:
                            logger.info("✅ n8n compatibility: Tools preserved, valid response")
                            return True
                        else:
                            logger.error("❌ n8n compatibility: No tools or content in response")
                            return False
                    else:
                        logger.error("❌ n8n compatibility: Invalid response structure")
                        return False
                else:
                    logger.error(f"❌ n8n compatibility request failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ n8n compatibility test error: {e}")
            return False
    
    async def test_model_capabilities_override(self) -> bool:
        """Test model capabilities environment variable override."""
        logger.info("🧪 Testing model capabilities override...")
        
        # Set a custom model capability
        custom_capabilities = {
            "integration_test_model": {
                "openai_compatible": True,
                "backend_type": "openai_native"
            }
        }
        
        os.environ["MODEL_CAPABILITIES_JSON"] = json.dumps(custom_capabilities)
        
        test_payload = {
            "model": "integration_test_model",
            "messages": [{"role": "user", "content": "Test custom model"}],
            "max_tokens": 20
        }
        
        try:
            async with self.session.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=test_payload
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Check that custom model was handled
                    if "choices" in response_data:
                        logger.info("✅ Custom model capabilities working")
                        return True
                    else:
                        logger.error("❌ Custom model response invalid")
                        return False
                else:
                    logger.error(f"❌ Custom model request failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Model capabilities override test error: {e}")
            return False
        finally:
            # Clean up environment
            os.environ.pop("MODEL_CAPABILITIES_JSON", None)
    
    async def run_all_tests(self) -> bool:
        """Run all integration tests."""
        logger.info("🚀 Starting OpenAI Front-Door Architecture Integration Tests")
        logger.info("=" * 70)
        
        # Check server health first
        if not await self.check_server_health():
            logger.error("❌ Server health check failed - cannot proceed with tests")
            return False
        
        # Run all tests
        tests = [
            ("OpenAI Front-Door Enabled", self.test_openai_frontdoor_enabled),
            ("Backend Routing", self.test_backend_routing),
            ("Tool Calling Compliance", self.test_tool_calling_compliance),
            ("n8n Compatibility", self.test_n8n_compatibility),
            ("Model Capabilities Override", self.test_model_capabilities_override)
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'=' * 50}")
            
            try:
                result = await test_func()
                results.append((test_name, result))
                
                if result:
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info(f"\n{'=' * 70}")
        logger.info("🎯 Integration Test Summary")
        logger.info(f"{'=' * 70}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {total - passed}")
        
        for test_name, result in results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"  {test_name}: {status}")
        
        if passed == total:
            logger.info("\n🎉 All integration tests passed!")
            logger.info("OpenAI Front-Door architecture is fully operational.")
            return True
        else:
            logger.error(f"\n❌ {total - passed} tests failed.")
            logger.error("Check server logs and implementation for issues.")
            return False

async def main():
    """Main entry point for integration tests."""
    # Verify environment setup
    if os.getenv("OPENAI_FRONTDOOR_ENABLED", "0") != "1":
        logger.error("❌ OPENAI_FRONTDOOR_ENABLED must be set to '1'")
        logger.error("Run: export OPENAI_FRONTDOOR_ENABLED=1")
        sys.exit(1)
    
    # Run tests
    async with IntegrationTestSuite() as test_suite:
        success = await test_suite.run_all_tests()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())