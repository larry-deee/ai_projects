#!/usr/bin/env python3
"""
Test script for diagnostic headers implementation.
Verifies that x-proxy-latency-ms and x-stream-downgraded headers are properly added
to all non-stream responses in the sf-model-api.

This tests the performance engineer's implementation of consistent diagnostic headers.
"""

import asyncio
import time
import aiohttp
import json
from typing import Dict, Any


class DiagnosticHeaderTester:
    """Test diagnostic headers implementation."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def test_endpoint(self, session: aiohttp.ClientSession, endpoint: str, method: str = "GET", 
                          data: Dict[str, Any] = None, expected_stream_downgraded: bool = False) -> Dict[str, Any]:
        """Test a specific endpoint for diagnostic headers."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == "POST":
                async with session.post(url, json=data) as response:
                    response_time = (time.time() - start_time) * 1000
                    headers = dict(response.headers)
                    status = response.status
                    try:
                        content = await response.json()
                    except:
                        content = await response.text()
            else:
                async with session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    headers = dict(response.headers)
                    status = response.status
                    try:
                        content = await response.json()
                    except:
                        content = await response.text()
                        
            # Check diagnostic headers
            result = {
                "endpoint": endpoint,
                "method": method,
                "status": status,
                "response_time_ms": response_time,
                "has_proxy_latency": "x-proxy-latency-ms" in headers,
                "has_stream_downgraded": "x-stream-downgraded" in headers,
                "proxy_latency_value": headers.get("x-proxy-latency-ms"),
                "stream_downgraded_value": headers.get("x-stream-downgraded"),
                "expected_stream_downgraded": expected_stream_downgraded,
                "headers_present": {
                    "x-proxy-latency-ms": headers.get("x-proxy-latency-ms"),
                    "x-stream-downgraded": headers.get("x-stream-downgraded"),
                    "content-type": headers.get("content-type")
                }
            }
            
            return result
            
        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "error": str(e),
                "status": "error"
            }
    
    async def run_tests(self):
        """Run comprehensive diagnostic header tests."""
        async with aiohttp.ClientSession() as session:
            
            # Test 1: Health check endpoint
            print("🔍 Testing /health endpoint...")
            result = await self.test_endpoint(session, "/health")
            self.results.append(result)
            
            # Test 2: Models list endpoint
            print("🔍 Testing /v1/models endpoint...")
            result = await self.test_endpoint(session, "/v1/models")
            self.results.append(result)
            
            # Test 3: Performance metrics endpoint
            print("🔍 Testing /v1/performance/metrics endpoint...")
            result = await self.test_endpoint(session, "/v1/performance/metrics")
            self.results.append(result)
            
            # Test 4: Chat completions endpoint (non-streaming)
            print("🔍 Testing /v1/chat/completions endpoint (non-streaming)...")
            chat_data = {
                "messages": [{"role": "user", "content": "Hello, test message"}],
                "model": "claude-3-haiku",
                "max_tokens": 100,
                "stream": False
            }
            result = await self.test_endpoint(session, "/v1/chat/completions", "POST", chat_data)
            self.results.append(result)
            
            # Test 5: Chat completions with tools (should trigger stream downgrade)
            print("🔍 Testing /v1/chat/completions with tools (stream downgrade)...")
            tool_data = {
                "messages": [{"role": "user", "content": "What's the weather?"}],
                "model": "claude-3-haiku",
                "max_tokens": 100,
                "stream": True,  # This should be downgraded due to tools
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather information",
                        "parameters": {"type": "object", "properties": {}}
                    }
                }]
            }
            result = await self.test_endpoint(session, "/v1/chat/completions", "POST", tool_data, expected_stream_downgraded=True)
            self.results.append(result)
            
            # Test 6: Anthropic messages endpoint
            print("🔍 Testing /v1/messages endpoint...")
            anthropic_data = {
                "messages": [{"role": "user", "content": "Hello, test message"}],
                "model": "claude-3-haiku",
                "max_tokens": 100
            }
            result = await self.test_endpoint(session, "/v1/messages", "POST", anthropic_data)
            self.results.append(result)
            
            # Test 7: Invalid request (should still have headers)
            print("🔍 Testing invalid request (error response)...")
            invalid_data = {
                "messages": [],  # Empty messages should cause error
                "model": "claude-3-haiku"
            }
            result = await self.test_endpoint(session, "/v1/chat/completions", "POST", invalid_data)
            self.results.append(result)
    
    def validate_results(self) -> Dict[str, Any]:
        """Validate test results and generate report."""
        validation = {
            "total_tests": len(self.results),
            "passed_tests": 0,
            "failed_tests": 0,
            "issues": [],
            "performance_stats": {
                "avg_latency_ms": 0,
                "min_latency_ms": float('inf'),
                "max_latency_ms": 0
            }
        }
        
        latencies = []
        
        for result in self.results:
            if result.get("status") == "error":
                validation["failed_tests"] += 1
                validation["issues"].append(f"❌ {result['endpoint']}: {result.get('error', 'Unknown error')}")
                continue
                
            issues = []
            
            # Check if required headers are present
            if not result.get("has_proxy_latency"):
                issues.append("Missing x-proxy-latency-ms header")
            
            if not result.get("has_stream_downgraded"):
                issues.append("Missing x-stream-downgraded header")
            
            # Validate header values
            proxy_latency = result.get("proxy_latency_value")
            if proxy_latency is not None:
                try:
                    latency_val = int(proxy_latency)
                    if latency_val < 0:
                        issues.append("x-proxy-latency-ms has negative value")
                    latencies.append(latency_val)
                except ValueError:
                    issues.append("x-proxy-latency-ms is not a valid integer")
            
            stream_downgraded = result.get("stream_downgraded_value")
            if stream_downgraded is not None and stream_downgraded not in ["true", "false"]:
                issues.append("x-stream-downgraded must be 'true' or 'false'")
            
            # Validate stream downgrade logic
            if result.get("expected_stream_downgraded") and stream_downgraded != "true":
                issues.append("Expected stream downgrade but x-stream-downgraded is not 'true'")
            
            if issues:
                validation["failed_tests"] += 1
                validation["issues"].append(f"❌ {result['endpoint']} ({result['method']}): {', '.join(issues)}")
            else:
                validation["passed_tests"] += 1
        
        # Calculate performance stats
        if latencies:
            validation["performance_stats"]["avg_latency_ms"] = sum(latencies) / len(latencies)
            validation["performance_stats"]["min_latency_ms"] = min(latencies)
            validation["performance_stats"]["max_latency_ms"] = max(latencies)
        
        return validation
    
    def print_report(self):
        """Print comprehensive test report."""
        validation = self.validate_results()
        
        print("\n" + "="*80)
        print("🚀 DIAGNOSTIC HEADERS PERFORMANCE TEST REPORT")
        print("="*80)
        
        print(f"\n📊 Test Summary:")
        print(f"  • Total Tests: {validation['total_tests']}")
        print(f"  • Passed: {validation['passed_tests']}")
        print(f"  • Failed: {validation['failed_tests']}")
        print(f"  • Success Rate: {(validation['passed_tests']/validation['total_tests']*100):.1f}%")
        
        print(f"\n⚡ Performance Statistics:")
        stats = validation['performance_stats']
        print(f"  • Average Latency: {stats['avg_latency_ms']:.1f}ms")
        print(f"  • Min Latency: {stats['min_latency_ms']:.1f}ms")
        print(f"  • Max Latency: {stats['max_latency_ms']:.1f}ms")
        
        if validation['issues']:
            print(f"\n❌ Issues Found:")
            for issue in validation['issues']:
                print(f"  {issue}")
        else:
            print(f"\n✅ All tests passed! Diagnostic headers are properly implemented.")
        
        print(f"\n📋 Detailed Results:")
        for result in self.results:
            if result.get("status") != "error":
                endpoint = result['endpoint']
                method = result['method']
                headers = result['headers_present']
                print(f"  • {endpoint} ({method}):")
                print(f"    - Status: {result['status']}")
                print(f"    - x-proxy-latency-ms: {headers.get('x-proxy-latency-ms', 'MISSING')}")
                print(f"    - x-stream-downgraded: {headers.get('x-stream-downgraded', 'MISSING')}")
            else:
                print(f"  • {result['endpoint']} ({result['method']}): ERROR - {result.get('error', 'Unknown')}")
        
        print("\n" + "="*80)


async def main():
    """Main test execution."""
    print("🔧 Starting diagnostic headers performance test...")
    print("📝 This test verifies x-proxy-latency-ms and x-stream-downgraded headers")
    print("🎯 Testing implementation by Performance Engineer")
    
    tester = DiagnosticHeaderTester()
    
    try:
        await tester.run_tests()
        tester.print_report()
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        print("💡 Make sure the server is running on localhost:8000")


if __name__ == "__main__":
    asyncio.run(main())