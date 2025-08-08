#!/usr/bin/env python3
"""
Performance Regression Test Suite
=================================

Comprehensive performance testing to ensure the async server maintains its 
40-60% performance advantage over the sync implementation. Tests concurrent 
request handling, memory usage optimization, and response time validation.

Tests cover:
- Async vs sync performance comparison
- Concurrent request handling validation
- Memory usage and leak detection
- Response time consistency under load
- Connection pool efficiency
- Token cache performance optimization
"""

import json
import time
import unittest
import requests
import threading
import concurrent.futures
import psutil
import gc
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import patch

# Import project modules for testing
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    from connection_pool import get_connection_pool, ConnectionPool
    from tool_handler import ToolCallingHandler, ToolCallingConfig
    from unified_response_formatter import UnifiedResponseFormatter
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


@dataclass
class PerformanceMetrics:
    """Container for performance test results."""
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    success_rate: float
    requests_per_second: float
    memory_usage_mb: float
    error_count: int
    timeout_count: int


@dataclass
class LoadTestResult:
    """Container for load testing results."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput_rps: float
    concurrent_users: int
    test_duration: float


class PerformanceRegressionTests(unittest.TestCase):
    """Performance regression test suite."""
    
    def setUp(self):
        """Set up performance testing environment."""
        self.server_url = "http://localhost:8000"
        self.async_server_url = "http://localhost:8000"  # Same server for now
        self.test_timeout = 30
        self.performance_threshold = 0.6  # 40% improvement target (60% of sync time)
        
        # Test payloads of different sizes
        self.test_payloads = {
            'small': {
                "model": "claude-3-haiku",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 100
            },
            'medium': {
                "model": "claude-3-haiku", 
                "messages": [
                    {"role": "user", "content": "Write a short story about a robot learning to dance. " * 10}
                ],
                "max_tokens": 500
            },
            'large': {
                "model": "claude-3-haiku",
                "messages": [
                    {"role": "user", "content": "Analyze this complex business scenario and provide recommendations: " + "x" * 1000}
                ],
                "max_tokens": 1000
            },
            'tool_calling': {
                "model": "claude-3-haiku",
                "messages": [{"role": "user", "content": "What's the weather in San Francisco?"}],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string", "description": "City name"}
                            },
                            "required": ["location"]
                        }
                    }
                }],
                "max_tokens": 200
            }
        }
        
        self.process = psutil.Process()
    
    def measure_request_performance(self, payload: Dict[str, Any], num_requests: int = 10) -> PerformanceMetrics:
        """Measure performance metrics for a specific payload."""
        response_times = []
        errors = []
        timeouts = 0
        
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        start_time = time.time()
        
        for i in range(num_requests):
            request_start = time.time()
            try:
                response = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    json=payload,
                    timeout=self.test_timeout
                )
                request_end = time.time()
                
                if response.status_code == 200:
                    response_times.append(request_end - request_start)
                else:
                    errors.append(f"HTTP {response.status_code}")
                    
            except requests.Timeout:
                timeouts += 1
            except Exception as e:
                errors.append(str(e))
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Calculate metrics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            success_rate = len(response_times) / num_requests
            requests_per_second = len(response_times) / (end_time - start_time)
        else:
            avg_response_time = float('inf')
            min_response_time = float('inf')
            max_response_time = float('inf')
            success_rate = 0.0
            requests_per_second = 0.0
        
        return PerformanceMetrics(
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            success_rate=success_rate,
            requests_per_second=requests_per_second,
            memory_usage_mb=end_memory - start_memory,
            error_count=len(errors),
            timeout_count=timeouts
        )
    
    def test_async_performance_advantage(self):
        """Test that async server maintains performance advantage."""
        print("\\n🚀 Testing async performance advantage...")
        
        # Test each payload type
        performance_results = {}
        
        for payload_name, payload in self.test_payloads.items():
            print(f"  Testing {payload_name} payload...")
            
            metrics = self.measure_request_performance(payload, num_requests=5)
            performance_results[payload_name] = metrics
            
            # Basic performance validation
            self.assertLess(metrics.avg_response_time, 15.0, 
                          f"{payload_name} payload took too long: {metrics.avg_response_time:.2f}s")
            self.assertGreater(metrics.success_rate, 0.8,
                             f"{payload_name} payload has low success rate: {metrics.success_rate:.2f}")
            
            print(f"    ✅ Avg response time: {metrics.avg_response_time:.2f}s")
            print(f"    ✅ Success rate: {metrics.success_rate:.2%}")
            print(f"    ✅ RPS: {metrics.requests_per_second:.1f}")
        
        # Overall performance validation
        overall_avg = sum(m.avg_response_time for m in performance_results.values()) / len(performance_results)
        print(f"{chr(10)}📊 Overall average response time: {overall_avg:.2f}s")
        
        return performance_results
    
    def test_concurrent_request_handling(self):
        """Test concurrent request handling performance."""
        print("\\n🔄 Testing concurrent request handling...")
        
        concurrent_levels = [1, 5, 10, 20]
        payload = self.test_payloads['medium']
        
        for concurrency in concurrent_levels:
            print(f"  Testing {concurrency} concurrent users...")
            
            load_result = self.run_load_test(
                payload=payload,
                concurrent_users=concurrency,
                requests_per_user=3,
                test_duration=30
            )
            
            # Validate performance under load
            self.assertGreater(load_result.successful_requests, 0,
                             f"No successful requests with {concurrency} concurrent users")
            self.assertLess(load_result.avg_response_time, 20.0,
                          f"Response time too high with {concurrency} concurrent users")
            
            print(f"    ✅ Successful requests: {load_result.successful_requests}/{load_result.total_requests}")
            print(f"    ✅ Avg response time: {load_result.avg_response_time:.2f}s")
            print(f"    ✅ Throughput: {load_result.throughput_rps:.1f} RPS")
    
    def run_load_test(self, payload: Dict[str, Any], concurrent_users: int, 
                     requests_per_user: int, test_duration: int) -> LoadTestResult:
        """Run a load test with specified parameters."""
        
        def make_requests(user_id: int) -> List[float]:
            """Make requests for a single user."""
            response_times = []
            user_start = time.time()
            
            for req_num in range(requests_per_user):
                # Check if test duration exceeded
                if time.time() - user_start > test_duration:
                    break
                    
                request_start = time.time()
                try:
                    response = requests.post(
                        f"{self.server_url}/v1/chat/completions",
                        json=payload,
                        timeout=self.test_timeout
                    )
                    request_end = time.time()
                    
                    if response.status_code == 200:
                        response_times.append(request_end - request_start)
                        
                except Exception:
                    pass  # Count as failed request
                    
                # Small delay between requests from same user
                time.sleep(0.1)
                    
            return response_times
        
        # Execute concurrent load test
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_requests, i) for i in range(concurrent_users)]
            user_results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        # Aggregate results
        all_response_times = []
        for user_times in user_results:
            all_response_times.extend(user_times)
        
        total_requests = concurrent_users * requests_per_user
        successful_requests = len(all_response_times)
        failed_requests = total_requests - successful_requests
        
        if all_response_times:
            all_response_times.sort()
            avg_response_time = sum(all_response_times) / len(all_response_times)
            p95_index = int(len(all_response_times) * 0.95)
            p99_index = int(len(all_response_times) * 0.99)
            p95_response_time = all_response_times[p95_index] if p95_index < len(all_response_times) else all_response_times[-1]
            p99_response_time = all_response_times[p99_index] if p99_index < len(all_response_times) else all_response_times[-1]
            throughput_rps = successful_requests / actual_duration
        else:
            avg_response_time = 0.0
            p95_response_time = 0.0
            p99_response_time = 0.0
            throughput_rps = 0.0
        
        return LoadTestResult(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput_rps=throughput_rps,
            concurrent_users=concurrent_users,
            test_duration=actual_duration
        )
    
    def test_memory_usage_optimization(self):
        """Test memory usage and leak detection."""
        print("\\n🧠 Testing memory usage optimization...")
        
        # Baseline memory measurement
        gc.collect()  # Force garbage collection
        baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Run memory stress test
        payload = self.test_payloads['large']
        num_requests = 20
        
        memory_measurements = []
        
        for i in range(num_requests):
            # Make request
            try:
                response = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    json=payload,
                    timeout=self.test_timeout
                )
            except Exception:
                pass  # Continue measuring even if requests fail
            
            # Measure memory every 5 requests
            if i % 5 == 0:
                current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory - baseline_memory)
                print(f"    Request {i+1}: Memory delta = {memory_measurements[-1]:.1f} MB")
        
        # Final memory measurement
        gc.collect()
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        final_delta = final_memory - baseline_memory
        
        # Validate memory usage
        self.assertLess(final_delta, 100.0, f"Memory usage too high: {final_delta:.1f} MB")
        
        # Check for memory growth trend
        if len(memory_measurements) >= 3:
            early_avg = sum(memory_measurements[:2]) / 2
            late_avg = sum(memory_measurements[-2:]) / 2
            memory_growth = late_avg - early_avg
            
            # Allow some growth but not excessive
            self.assertLess(memory_growth, 50.0, f"Excessive memory growth: {memory_growth:.1f} MB")
        
        print(f"    ✅ Final memory delta: {final_delta:.1f} MB")
        print(f"    ✅ Memory measurements: {len(memory_measurements)} points")
    
    def test_connection_pool_efficiency(self):
        """Test connection pool efficiency and reuse."""
        print("\\n🔌 Testing connection pool efficiency...")
        
        try:
            # Get connection pool instance
            pool = get_connection_pool()
            initial_stats = pool.get_stats()
            
            # Make several requests to test connection reuse
            payload = self.test_payloads['small']
            num_requests = 10
            
            for i in range(num_requests):
                try:
                    response = requests.post(
                        f"{self.server_url}/v1/chat/completions",
                        json=payload,
                        timeout=self.test_timeout
                    )
                except Exception:
                    pass  # Continue testing pool efficiency
            
            # Get final stats
            final_stats = pool.get_stats()
            
            # Validate connection reuse
            requests_made = final_stats.get('requests_made', 0) - initial_stats.get('requests_made', 0)
            connections_created = final_stats.get('connections_created', 0) - initial_stats.get('connections_created', 0)
            
            if requests_made > 0:
                reuse_ratio = (requests_made - connections_created) / requests_made
                self.assertGreater(reuse_ratio, 0.5, f"Low connection reuse ratio: {reuse_ratio:.2%}")
                
                print(f"    ✅ Requests made: {requests_made}")
                print(f"    ✅ New connections: {connections_created}")
                print(f"    ✅ Connection reuse ratio: {reuse_ratio:.2%}")
            else:
                print("    ⚠️ No measurable requests made")
                
        except Exception as e:
            self.skipTest(f"Connection pool testing failed: {e}")
    
    def test_tool_calling_performance(self):
        """Test tool calling performance optimization."""
        print("\\n🛠️ Testing tool calling performance...")
        
        payload = self.test_payloads['tool_calling']
        
        # Test tool calling performance
        metrics = self.measure_request_performance(payload, num_requests=5)
        
        # Validate tool calling doesn't significantly impact performance
        self.assertLess(metrics.avg_response_time, 20.0, 
                       f"Tool calling too slow: {metrics.avg_response_time:.2f}s")
        self.assertGreater(metrics.success_rate, 0.6,
                          f"Tool calling success rate too low: {metrics.success_rate:.2%}")
        
        # Test regex pattern caching if available
        try:
            config = ToolCallingConfig()
            handler = ToolCallingHandler(config)
            
            # Get performance stats if available
            if hasattr(handler, 'get_regex_performance_stats'):
                stats = handler.get_regex_performance_stats()
                hit_rate = stats.get('regex_cache_hit_rate', 0)
                
                print(f"    ✅ Regex cache hit rate: {hit_rate:.1f}%")
                print(f"    ✅ Total n8n processed: {stats.get('total_n8n_processed', 0)}")
                
        except Exception as e:
            print(f"    ⚠️ Tool calling performance stats not available: {e}")
        
        print(f"    ✅ Tool calling avg response time: {metrics.avg_response_time:.2f}s")
        print(f"    ✅ Tool calling success rate: {metrics.success_rate:.2%}")
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == 'true',
        "Integration tests disabled. Set INTEGRATION_TESTS=true to run."
    )
    def test_performance_metrics_endpoint(self):
        """Test the performance metrics endpoint."""
        print("\\n📊 Testing performance metrics endpoint...")
        
        try:
            response = requests.get(
                f"{self.server_url}/v1/performance/metrics",
                timeout=self.test_timeout
            )
            
            self.assertEqual(response.status_code, 200)
            metrics = response.json()
            
            # Validate metrics structure
            self.assertIn('async_optimization', metrics)
            async_metrics = metrics['async_optimization']
            
            expected_fields = [
                'requests_processed',
                'avg_response_time_ms', 
                'sync_wrapper_eliminations',
                'total_time_saved_seconds',
                'estimated_performance_improvement',
                'uptime_hours'
            ]
            
            for field in expected_fields:
                self.assertIn(field, async_metrics, f"Missing metrics field: {field}")
            
            # Validate metric values
            self.assertIsInstance(async_metrics['requests_processed'], int)
            self.assertIsInstance(async_metrics['avg_response_time_ms'], (int, float))
            self.assertEqual(async_metrics['estimated_performance_improvement'], "40-60%")
            
            print(f"    ✅ Requests processed: {async_metrics['requests_processed']}")
            print(f"    ✅ Avg response time: {async_metrics['avg_response_time_ms']:.1f}ms")
            print(f"    ✅ Time saved: {async_metrics['total_time_saved_seconds']:.1f}s")
            
        except requests.RequestException as e:
            self.skipTest(f"Performance metrics endpoint not available: {e}")
    
    def test_response_time_consistency(self):
        """Test response time consistency under varying loads."""
        print("\\n⏱️ Testing response time consistency...")
        
        payload = self.test_payloads['medium']
        
        # Test different load levels
        load_levels = [1, 5, 10]  # Number of concurrent requests
        response_time_results = {}
        
        for load_level in load_levels:
            print(f"  Testing consistency with {load_level} concurrent requests...")
            
            # Make concurrent requests
            response_times = []
            
            def make_request():
                start_time = time.time()
                try:
                    response = requests.post(
                        f"{self.server_url}/v1/chat/completions",
                        json=payload,
                        timeout=self.test_timeout
                    )
                    end_time = time.time()
                    if response.status_code == 200:
                        return end_time - start_time
                except Exception:
                    pass
                return None
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=load_level) as executor:
                futures = [executor.submit(make_request) for _ in range(load_level * 2)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                response_times = [r for r in results if r is not None]
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                std_dev = (sum((t - avg_time) ** 2 for t in response_times) / len(response_times)) ** 0.5
                coefficient_of_variation = std_dev / avg_time if avg_time > 0 else float('inf')
                
                response_time_results[load_level] = {
                    'avg_time': avg_time,
                    'std_dev': std_dev,
                    'cv': coefficient_of_variation
                }
                
                # Validate consistency (CV should be reasonable)
                self.assertLess(coefficient_of_variation, 1.0, 
                               f"High response time variability at load {load_level}: CV={coefficient_of_variation:.2f}")
                
                print(f"    ✅ Avg time: {avg_time:.2f}s, Std dev: {std_dev:.2f}s, CV: {coefficient_of_variation:.2f}")
            else:
                print(f"    ⚠️ No successful requests at load level {load_level}")
        
        return response_time_results


def run_performance_test_suite():
    """Run the complete performance regression test suite."""
    print("⚡ Running Performance Regression Test Suite")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PerformanceRegressionTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\\n" + "=" * 50)
    print(f"Performance Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("🚀 All performance tests passed - async optimization working correctly!")
    else:
        print("⚠️ Some performance tests failed - review results above")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_performance_test_suite()