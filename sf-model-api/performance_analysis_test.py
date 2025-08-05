#!/usr/bin/env python3
"""
Performance Analysis Test
=========================

Comprehensive analysis of response processing and async implementation 
after token management and chat-generations optimizations.

This script tests:
1. Response processing efficiency 
2. Concurrent request handling
3. Async vs sync performance patterns
4. Identification of remaining bottlenecks
"""

import requests
import json
import time
import threading
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import statistics

BASE_URL = "http://localhost:8000"

class PerformanceAnalyzer:
    """Analyze current performance characteristics."""
    
    def __init__(self):
        self.results = {}
        
    def test_response_processing_efficiency(self) -> Dict[str, Any]:
        """Test current response processing efficiency."""
        print("🔍 Testing Response Processing Efficiency...")
        
        # Test different response sizes to measure processing overhead
        test_cases = [
            {"messages": [{"role": "user", "content": "Hello"}], "name": "small"},
            {"messages": [{"role": "user", "content": "Write a detailed explanation of machine learning in 200 words."}], "name": "medium"},
            {"messages": [{"role": "user", "content": "Write a comprehensive analysis of distributed systems architecture, including microservices, containers, load balancing, and database sharding strategies. Include real-world examples and best practices."}], "name": "large"}
        ]
        
        results = {}
        
        for test_case in test_cases:
            print(f"  Testing {test_case['name']} response...")
            
            payload = {
                "model": "claude-3-haiku",
                "messages": test_case["messages"],
                "max_tokens": 500,
                "temperature": 0.1
            }
            
            # Measure total response time
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{BASE_URL}/v1/chat/completions",
                    json=payload,
                    timeout=60
                )
                
                end_time = time.time()
                total_time = end_time - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    
                    results[test_case['name']] = {
                        "total_time": total_time,
                        "response_length": len(content),
                        "chars_per_second": len(content) / total_time,
                        "status": "success"
                    }
                    print(f"    ✅ {test_case['name']}: {total_time:.2f}s, {len(content)} chars, {len(content)/total_time:.1f} chars/sec")
                else:
                    results[test_case['name']] = {"status": "failed", "code": response.status_code}
                    print(f"    ❌ {test_case['name']}: Failed ({response.status_code})")
                    
            except Exception as e:
                results[test_case['name']] = {"status": "error", "error": str(e)}
                print(f"    ❌ {test_case['name']}: Error - {e}")
        
        return results
    
    def test_concurrent_request_handling(self, num_threads: int = 5) -> Dict[str, Any]:
        """Test concurrent request handling capacity."""
        print(f"🔍 Testing Concurrent Request Handling ({num_threads} threads)...")
        
        def make_request(thread_id: int) -> Dict[str, Any]:
            """Make a single request and measure performance."""
            payload = {
                "model": "claude-3-haiku", 
                "messages": [{"role": "user", "content": f"Hello from thread {thread_id}. Please respond briefly."}],
                "max_tokens": 100,
                "temperature": 0.1
            }
            
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{BASE_URL}/v1/chat/completions",
                    json=payload,
                    timeout=30
                )
                
                end_time = time.time()
                
                if response.status_code == 200:
                    return {
                        "thread_id": thread_id,
                        "response_time": end_time - start_time,
                        "status": "success"
                    }
                else:
                    return {
                        "thread_id": thread_id,
                        "status": "failed", 
                        "code": response.status_code
                    }
                    
            except Exception as e:
                return {
                    "thread_id": thread_id,
                    "status": "error",
                    "error": str(e)
                }
        
        # Execute concurrent requests
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful = [r for r in results if r.get("status") == "success"]
        response_times = [r["response_time"] for r in successful]
        
        analysis = {
            "total_requests": num_threads,
            "successful_requests": len(successful),
            "failed_requests": num_threads - len(successful),
            "total_time": total_time,
            "requests_per_second": num_threads / total_time,
            "success_rate": (len(successful) / num_threads) * 100
        }
        
        if response_times:
            analysis.update({
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times)
            })
        
        print(f"  📊 Results: {len(successful)}/{num_threads} successful")
        print(f"  📊 Success rate: {analysis['success_rate']:.1f}%")
        print(f"  📊 Requests/sec: {analysis['requests_per_second']:.2f}")
        if response_times:
            print(f"  📊 Avg response time: {analysis['avg_response_time']:.2f}s")
            print(f"  📊 Response time range: {min(response_times):.2f}s - {max(response_times):.2f}s")
        
        return analysis
    
    def analyze_async_vs_sync_patterns(self) -> Dict[str, Any]:
        """Analyze current async vs sync usage patterns."""
        print("🔍 Analyzing Async vs Sync Patterns...")
        
        # Test streaming vs non-streaming to understand async utilization
        payload = {
            "model": "claude-3-haiku",
            "messages": [{"role": "user", "content": "Write a brief summary of Python async programming."}],
            "max_tokens": 300,
            "temperature": 0.1
        }
        
        results = {}
        
        # Test non-streaming request
        print("  Testing non-streaming request...")
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                json=payload,
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                results["non_streaming"] = {
                    "response_time": end_time - start_time,
                    "status": "success"
                }
                print(f"    ✅ Non-streaming: {end_time - start_time:.2f}s")
            else:
                results["non_streaming"] = {"status": "failed", "code": response.status_code}
                print(f"    ❌ Non-streaming failed: {response.status_code}")
        except Exception as e:
            results["non_streaming"] = {"status": "error", "error": str(e)}
            print(f"    ❌ Non-streaming error: {e}")
        
        # Test streaming request
        print("  Testing streaming request...")
        streaming_payload = {**payload, "stream": True}
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                json=streaming_payload,
                timeout=30,
                stream=True
            )
            
            first_chunk_time = None
            chunks_received = 0
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: ') and not line.startswith('data: [DONE]'):
                        chunks_received += 1
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
            
            end_time = time.time()
            
            results["streaming"] = {
                "total_time": end_time - start_time,
                "time_to_first_chunk": first_chunk_time - start_time if first_chunk_time else None,
                "chunks_received": chunks_received,
                "status": "success"
            }
            print(f"    ✅ Streaming: {end_time - start_time:.2f}s total, {chunks_received} chunks")
            if first_chunk_time:
                print(f"    ✅ Time to first chunk: {first_chunk_time - start_time:.2f}s")
                
        except Exception as e:
            results["streaming"] = {"status": "error", "error": str(e)}
            print(f"    ❌ Streaming error: {e}")
        
        return results
    
    def identify_bottlenecks(self) -> List[str]:
        """Identify potential remaining bottlenecks."""
        print("🔍 Identifying Potential Bottlenecks...")
        
        bottlenecks = []
        
        # Check if there are sync operations in async context
        if hasattr(self.results.get('async_patterns'), 'non_streaming'):
            non_stream = self.results['async_patterns']['non_streaming']
            if non_stream.get('response_time', 0) > 2.0:
                bottlenecks.append("Non-streaming requests taking > 2 seconds may indicate sync bottlenecks")
        
        # Check concurrent performance
        if hasattr(self.results.get('concurrency'), 'success_rate'):
            success_rate = self.results['concurrency']['success_rate'] 
            if success_rate < 95:
                bottlenecks.append(f"Concurrent success rate ({success_rate:.1f}%) indicates potential thread contention")
        
        # Check response time variance
        if hasattr(self.results.get('concurrency'), 'max_response_time'):
            max_time = self.results['concurrency']['max_response_time']
            min_time = self.results['concurrency']['min_response_time']
            if max_time / min_time > 3:
                bottlenecks.append("High response time variance suggests resource contention or blocking operations")
        
        if not bottlenecks:
            bottlenecks.append("No obvious bottlenecks detected - system performing well")
        
        for bottleneck in bottlenecks:
            print(f"  🔍 {bottleneck}")
        
        return bottlenecks
    
    def run_comprehensive_analysis(self):
        """Run all performance tests and provide analysis."""
        print("🚀 Comprehensive Performance Analysis")
        print("=" * 60)
        print("Analyzing response processing and async implementation")
        print("after token management and chat-generations optimizations...")
        print()
        
        # Test 1: Response Processing Efficiency
        self.results['response_processing'] = self.test_response_processing_efficiency()
        print()
        
        # Test 2: Concurrent Request Handling  
        self.results['concurrency'] = self.test_concurrent_request_handling()
        print()
        
        # Test 3: Async vs Sync Patterns
        self.results['async_patterns'] = self.analyze_async_vs_sync_patterns()
        print()
        
        # Test 4: Bottleneck Identification
        self.results['bottlenecks'] = self.identify_bottlenecks()
        print()
        
        return self.results

def check_server_status():
    """Check if server is running and get current metrics."""
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            return False, "Health check failed"
        
        metrics_response = requests.get(f"{BASE_URL}/metrics/performance", timeout=5)
        if metrics_response.status_code == 200:
            metrics = metrics_response.json()
            return True, metrics
        else:
            return True, "Metrics not available"
            
    except Exception as e:
        return False, str(e)

def main():
    """Run the performance analysis."""
    # Check server status
    server_ok, server_info = check_server_status()
    if not server_ok:
        print("❌ Server not running or not responding")
        print("Please start the server with: python src/llm_endpoint_server.py")
        return
    
    print("✅ Server is running")
    
    if isinstance(server_info, dict):
        print("📊 Current Optimization Status:")
        opt_info = server_info.get('token_cache_optimization', {})
        perf_info = server_info.get('performance_metrics', {})
        print(f"  Cache TTL: {opt_info.get('cache_ttl_minutes', 'N/A')} minutes")
        print(f"  Cache hit rate: {perf_info.get('cache_hit_rate', 'N/A')}%")
        print(f"  File I/O reduction: {server_info.get('file_io_optimization', {}).get('file_io_reduction_percentage', 'N/A')}%")
    
    print()
    
    # Run analysis
    analyzer = PerformanceAnalyzer()
    results = analyzer.run_comprehensive_analysis()
    
    # Generate summary
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    
    # Response processing summary
    rp = results.get('response_processing', {})
    successful_tests = [k for k, v in rp.items() if v.get('status') == 'success']
    if successful_tests:
        avg_chars_per_sec = statistics.mean([rp[k]['chars_per_second'] for k in successful_tests])
        print(f"Response Processing: {len(successful_tests)}/3 tests successful")
        print(f"Average processing speed: {avg_chars_per_sec:.1f} chars/sec")
    
    # Concurrency summary
    conc = results.get('concurrency', {})
    if 'success_rate' in conc:
        print(f"Concurrent handling: {conc['success_rate']:.1f}% success rate")
        print(f"Throughput: {conc['requests_per_second']:.2f} requests/sec")
    
    # Async patterns summary
    async_pat = results.get('async_patterns', {})
    if async_pat.get('streaming', {}).get('status') == 'success':
        streaming = async_pat['streaming']
        print(f"Streaming: {streaming.get('chunks_received', 0)} chunks processed")
        if streaming.get('time_to_first_chunk'):
            print(f"Time to first chunk: {streaming['time_to_first_chunk']:.2f}s")
    
    print()
    print("🔍 BOTTLENECK ANALYSIS")
    print("=" * 60)
    bottlenecks = results.get('bottlenecks', [])
    for i, bottleneck in enumerate(bottlenecks, 1):
        print(f"{i}. {bottleneck}")
    
    print()
    print("💡 OPTIMIZATION RECOMMENDATIONS")
    print("=" * 60)
    
    # Generate recommendations based on results
    recommendations = []
    
    # Check response processing efficiency
    if rp and len(successful_tests) < 3:
        recommendations.append("MEDIUM: Response processing optimization - some test cases failed")
    elif rp and successful_tests:
        avg_speed = statistics.mean([rp[k]['chars_per_second'] for k in successful_tests])
        if avg_speed < 100:
            recommendations.append("HIGH: Response processing speed is low (<100 chars/sec)")
        elif avg_speed < 500:
            recommendations.append("LOW: Response processing could be optimized (current: {avg_speed:.1f} chars/sec)")
    
    # Check concurrency performance
    if conc and conc.get('success_rate', 100) < 95:
        recommendations.append("HIGH: Concurrent request handling needs improvement")
    elif conc and conc.get('requests_per_second', 0) < 2:
        recommendations.append("MEDIUM: Concurrent throughput could be improved")
    
    # Check streaming performance
    stream_result = async_pat.get('streaming', {})
    if stream_result.get('time_to_first_chunk', 0) > 1.0:
        recommendations.append("MEDIUM: Streaming latency could be reduced")
    
    if not recommendations:
        recommendations.append("✅ No immediate optimizations needed - system performing well")
    
    for i, rec in enumerate(recommendations, 1):
        priority = rec.split(':')[0]
        message = ':'.join(rec.split(':')[1:]).strip()
        
        if priority == "HIGH":
            print(f"{i}. 🔴 HIGH PRIORITY: {message}")
        elif priority == "MEDIUM": 
            print(f"{i}. 🟡 MEDIUM PRIORITY: {message}")
        elif priority == "LOW":
            print(f"{i}. 🟢 LOW PRIORITY: {message}")
        else:
            print(f"{i}. {rec}")

if __name__ == "__main__":
    main()