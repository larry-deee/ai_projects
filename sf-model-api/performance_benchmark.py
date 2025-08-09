#!/usr/bin/env python3
"""
Anthropic Native Pass-Through Performance Benchmark
==================================================

Comprehensive performance benchmarking tool for the Anthropic native adapter
that measures:
- Request latency (p50, p95, p99)
- Connection pool utilization
- SSE streaming performance 
- Memory usage patterns
- Throughput under concurrent load

Usage:
    python performance_benchmark.py --test-type all
    python performance_benchmark.py --test-type latency --requests 100
    python performance_benchmark.py --test-type streaming --duration 30
    python performance_benchmark.py --test-type concurrent --workers 10
"""

import asyncio
import json
import time
import statistics
import argparse
import sys
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import psutil
import threading
from dataclasses import dataclass, asdict

try:
    import httpx
    import aiohttp
except ImportError:
    print("Required packages missing. Install with: pip install httpx aiohttp psutil")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Container for benchmark test results."""
    test_type: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float  
    p99_latency_ms: float
    requests_per_second: float
    memory_usage_mb: float
    error_rate: float
    additional_metrics: Dict[str, Any]

class AnthropicBenchmark:
    """
    Performance benchmark suite for Anthropic native adapter.
    """
    
    def __init__(self, 
                 base_url: str = "http://localhost:8000",
                 api_key: str = "test-key",
                 timeout: int = 30):
        """
        Initialize benchmark suite.
        
        Args:
            base_url: Base URL of the service to test
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.process = psutil.Process()
        
        # Test data for consistent benchmarking
        self.test_message = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, this is a test message for benchmarking performance."
                }
            ]
        }
        
        logger.info(f"🔧 AnthropicBenchmark initialized: {base_url}")
    
    async def benchmark_request_latency(self, num_requests: int = 50) -> BenchmarkResult:
        """
        Benchmark basic request latency.
        
        Args:
            num_requests: Number of requests to send
            
        Returns:
            BenchmarkResult: Latency benchmark results
        """
        logger.info(f"🚀 Starting latency benchmark: {num_requests} requests")
        
        latencies = []
        successful = 0
        failed = 0
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(num_requests):
                try:
                    request_start = time.time()
                    
                    response = await client.post(
                        f"{self.base_url}/anthropic/v1/messages",
                        json=self.test_message,
                        headers={
                            "x-api-key": self.api_key,
                            "Content-Type": "application/json"
                        }
                    )
                    
                    request_end = time.time()
                    latency_ms = (request_end - request_start) * 1000
                    latencies.append(latency_ms)
                    
                    if response.status_code == 200:
                        successful += 1
                    else:
                        failed += 1
                        logger.warning(f"Request {i+1} failed: {response.status_code}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"Request {i+1} error: {e}")
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        duration = end_time - start_time
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p50_latency = statistics.median(latencies)
            latencies_sorted = sorted(latencies)
            p95_latency = latencies_sorted[int(0.95 * len(latencies))]
            p99_latency = latencies_sorted[int(0.99 * len(latencies))]
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = 0
        
        return BenchmarkResult(
            test_type="latency",
            duration_seconds=duration,
            total_requests=num_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            requests_per_second=successful / duration if duration > 0 else 0,
            memory_usage_mb=end_memory - start_memory,
            error_rate=failed / num_requests if num_requests > 0 else 0,
            additional_metrics={"latencies": latencies[:10]}  # Sample of latencies
        )
    
    async def benchmark_streaming_performance(self, duration_seconds: int = 30) -> BenchmarkResult:
        """
        Benchmark SSE streaming performance.
        
        Args:
            duration_seconds: How long to run the streaming test
            
        Returns:
            BenchmarkResult: Streaming performance results
        """
        logger.info(f"🌊 Starting streaming benchmark: {duration_seconds}s")
        
        streaming_message = {**self.test_message, "stream": True, "max_tokens": 500}
        
        total_chunks = 0
        total_bytes = 0
        successful_streams = 0
        failed_streams = 0
        chunk_latencies = []
        
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while (time.time() - start_time) < duration_seconds:
                try:
                    stream_start = time.time()
                    
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/anthropic/v1/messages",
                        json=streaming_message,
                        headers={
                            "x-api-key": self.api_key,
                            "Content-Type": "application/json",
                            "Accept": "text/event-stream"
                        }
                    ) as response:
                        if response.status_code != 200:
                            failed_streams += 1
                            continue
                        
                        first_chunk_time = None
                        async for chunk in response.aiter_raw():
                            if chunk:
                                chunk_time = time.time()
                                if first_chunk_time is None:
                                    first_chunk_time = chunk_time
                                    first_chunk_latency = (chunk_time - stream_start) * 1000
                                    chunk_latencies.append(first_chunk_latency)
                                
                                total_chunks += 1
                                total_bytes += len(chunk)
                        
                        successful_streams += 1
                        
                except Exception as e:
                    failed_streams += 1
                    logger.error(f"Streaming error: {e}")
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        actual_duration = end_time - start_time
        
        avg_first_chunk_latency = statistics.mean(chunk_latencies) if chunk_latencies else 0
        chunks_per_second = total_chunks / actual_duration if actual_duration > 0 else 0
        bytes_per_second = total_bytes / actual_duration if actual_duration > 0 else 0
        
        return BenchmarkResult(
            test_type="streaming",
            duration_seconds=actual_duration,
            total_requests=successful_streams + failed_streams,
            successful_requests=successful_streams,
            failed_requests=failed_streams,
            avg_latency_ms=avg_first_chunk_latency,
            p50_latency_ms=statistics.median(chunk_latencies) if chunk_latencies else 0,
            p95_latency_ms=sorted(chunk_latencies)[int(0.95 * len(chunk_latencies))] if chunk_latencies else 0,
            p99_latency_ms=sorted(chunk_latencies)[int(0.99 * len(chunk_latencies))] if chunk_latencies else 0,
            requests_per_second=successful_streams / actual_duration if actual_duration > 0 else 0,
            memory_usage_mb=end_memory - start_memory,
            error_rate=failed_streams / (successful_streams + failed_streams) if (successful_streams + failed_streams) > 0 else 0,
            additional_metrics={
                "total_chunks": total_chunks,
                "total_bytes": total_bytes,
                "chunks_per_second": chunks_per_second,
                "bytes_per_second": bytes_per_second
            }
        )
    
    async def benchmark_concurrent_load(self, concurrent_workers: int = 10, requests_per_worker: int = 20) -> BenchmarkResult:
        """
        Benchmark performance under concurrent load.
        
        Args:
            concurrent_workers: Number of concurrent request workers
            requests_per_worker: Number of requests each worker should make
            
        Returns:
            BenchmarkResult: Concurrent load test results
        """
        logger.info(f"⚡ Starting concurrent load benchmark: {concurrent_workers} workers, {requests_per_worker} requests each")
        
        total_requests = concurrent_workers * requests_per_worker
        results = []
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        async def worker(worker_id: int) -> List[float]:
            """Worker function to send requests concurrently."""
            worker_latencies = []
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for i in range(requests_per_worker):
                    try:
                        request_start = time.time()
                        
                        response = await client.post(
                            f"{self.base_url}/anthropic/v1/messages",
                            json=self.test_message,
                            headers={
                                "x-api-key": self.api_key,
                                "Content-Type": "application/json"
                            }
                        )
                        
                        request_end = time.time()
                        latency_ms = (request_end - request_start) * 1000
                        worker_latencies.append(latency_ms)
                        
                        if response.status_code != 200:
                            logger.warning(f"Worker {worker_id} request {i+1} failed: {response.status_code}")
                            
                    except Exception as e:
                        logger.error(f"Worker {worker_id} request {i+1} error: {e}")
            
            return worker_latencies
        
        # Run all workers concurrently
        tasks = [worker(i) for i in range(concurrent_workers)]
        worker_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all latency results
        all_latencies = []
        successful = 0
        failed = 0
        
        for worker_latencies in worker_results:
            if isinstance(worker_latencies, Exception):
                failed += requests_per_worker
                logger.error(f"Worker failed: {worker_latencies}")
            else:
                all_latencies.extend(worker_latencies)
                successful += len(worker_latencies)
                failed += requests_per_worker - len(worker_latencies)
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        duration = end_time - start_time
        
        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            p50_latency = statistics.median(all_latencies)
            latencies_sorted = sorted(all_latencies)
            p95_latency = latencies_sorted[int(0.95 * len(latencies_sorted))]
            p99_latency = latencies_sorted[int(0.99 * len(latencies_sorted))]
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = 0
        
        return BenchmarkResult(
            test_type="concurrent",
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful,
            failed_requests=failed,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            requests_per_second=successful / duration if duration > 0 else 0,
            memory_usage_mb=end_memory - start_memory,
            error_rate=failed / total_requests if total_requests > 0 else 0,
            additional_metrics={
                "concurrent_workers": concurrent_workers,
                "requests_per_worker": requests_per_worker
            }
        )
    
    async def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get current service performance metrics.
        
        Returns:
            Dict: Service performance metrics
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/anthropic/metrics")
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Metrics endpoint returned {response.status_code}"}
        except Exception as e:
            return {"error": f"Failed to get metrics: {e}"}
    
    def print_results(self, result: BenchmarkResult):
        """
        Print benchmark results in a formatted way.
        
        Args:
            result: Benchmark result to print
        """
        print(f"\n{'='*60}")
        print(f"📊 {result.test_type.upper()} BENCHMARK RESULTS")
        print(f"{'='*60}")
        print(f"Duration:           {result.duration_seconds:.2f}s")
        print(f"Total Requests:     {result.total_requests}")
        print(f"Successful:         {result.successful_requests}")
        print(f"Failed:             {result.failed_requests}")
        print(f"Error Rate:         {result.error_rate:.1%}")
        print(f"")
        print(f"LATENCY METRICS:")
        print(f"Average:            {result.avg_latency_ms:.2f}ms")
        print(f"P50 (Median):       {result.p50_latency_ms:.2f}ms")
        print(f"P95:                {result.p95_latency_ms:.2f}ms")
        print(f"P99:                {result.p99_latency_ms:.2f}ms")
        print(f"")
        print(f"THROUGHPUT:")
        print(f"Requests/sec:       {result.requests_per_second:.2f}")
        print(f"Memory Usage:       {result.memory_usage_mb:+.2f}MB")
        
        if result.additional_metrics:
            print(f"")
            print(f"ADDITIONAL METRICS:")
            for key, value in result.additional_metrics.items():
                if key == "latencies":
                    continue  # Skip raw latency data in summary
                print(f"{key:20}: {value}")

async def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(description="Anthropic Native Pass-Through Performance Benchmark")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of service to test")
    parser.add_argument("--api-key", default="test-key", help="API key for authentication")
    parser.add_argument("--test-type", choices=["latency", "streaming", "concurrent", "all"], default="all", help="Type of test to run")
    parser.add_argument("--requests", type=int, default=50, help="Number of requests for latency test")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds for streaming test")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--output", help="JSON file to save detailed results")
    
    args = parser.parse_args()
    
    benchmark = AnthropicBenchmark(
        base_url=args.base_url,
        api_key=args.api_key
    )
    
    results = []
    
    # Get initial metrics
    logger.info("📋 Getting initial service metrics...")
    initial_metrics = await benchmark.get_service_metrics()
    print(f"Initial Service Metrics: {json.dumps(initial_metrics, indent=2)}")
    
    try:
        if args.test_type in ["latency", "all"]:
            result = await benchmark.benchmark_request_latency(args.requests)
            benchmark.print_results(result)
            results.append(result)
        
        if args.test_type in ["streaming", "all"]:
            result = await benchmark.benchmark_streaming_performance(args.duration)
            benchmark.print_results(result)
            results.append(result)
        
        if args.test_type in ["concurrent", "all"]:
            result = await benchmark.benchmark_concurrent_load(args.workers)
            benchmark.print_results(result)
            results.append(result)
            
        # Get final metrics
        logger.info("📋 Getting final service metrics...")
        final_metrics = await benchmark.get_service_metrics()
        print(f"\nFinal Service Metrics: {json.dumps(final_metrics, indent=2)}")
        
        if args.output:
            output_data = {
                "timestamp": time.time(),
                "test_configuration": vars(args),
                "initial_metrics": initial_metrics,
                "final_metrics": final_metrics,
                "results": [asdict(result) for result in results]
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"📄 Detailed results saved to {args.output}")
    
    except KeyboardInterrupt:
        logger.info("❌ Benchmark interrupted by user")
    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())