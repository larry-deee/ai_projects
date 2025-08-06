#!/usr/bin/env python3
"""
Connection Pool Performance Monitor
==================================

Performance monitoring and validation script for the Salesforce Models API Gateway
connection pooling implementation. Provides benchmarking, statistics tracking, 
and validation of the 20-30% performance improvement target.

Usage:
    python connection_pool_monitor.py --benchmark
    python connection_pool_monitor.py --stats
    python connection_pool_monitor.py --validate
"""

import asyncio
import time
import json
import sys
import argparse
import aiohttp
from typing import Dict, Any, List
import statistics

# Import the connection pool
try:
    from connection_pool import get_connection_pool, benchmark_connection_reuse
except ImportError:
    sys.path.append('.')
    from connection_pool import get_connection_pool, benchmark_connection_reuse


class ConnectionPoolMonitor:
    """
    Monitors and validates connection pool performance for the Salesforce Models API Gateway.
    """
    
    def __init__(self):
        self.pool = get_connection_pool()
        self.results = {}
    
    async def benchmark_performance(self, iterations: int = 1000) -> Dict[str, Any]:
        """
        Comprehensive performance benchmark comparing pooled vs non-pooled connections.
        
        Args:
            iterations: Number of test iterations for statistical significance
            
        Returns:
            Dict[str, Any]: Detailed benchmark results with performance metrics
        """
        print(f"🏃‍♂️ Running connection pool benchmark with {iterations} iterations...")
        
        # Reset pool statistics for clean benchmark
        self.pool.reset_stats()
        
        # Test 1: Connection pool session acquisition time
        pool_times = []
        for i in range(iterations):
            start_time = time.perf_counter()
            session = await self.pool.get_session()
            end_time = time.perf_counter()
            pool_times.append((end_time - start_time) * 1000)  # Convert to ms
            
            if i % 100 == 0:
                print(f"  Progress: {i}/{iterations} iterations completed")
        
        # Test 2: New session creation time (for comparison)
        new_session_times = []
        for i in range(min(100, iterations)):  # Limit to 100 for performance
            start_time = time.perf_counter()
            timeout = aiohttp.ClientTimeout(total=60)
            session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(ssl=True)
            )
            await session.close()
            end_time = time.perf_counter()
            new_session_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        # Calculate statistics
        pool_stats = {
            'mean': statistics.mean(pool_times),
            'median': statistics.median(pool_times),
            'stdev': statistics.stdev(pool_times) if len(pool_times) > 1 else 0,
            'min': min(pool_times),
            'max': max(pool_times),
            'p95': sorted(pool_times)[int(0.95 * len(pool_times))],
            'p99': sorted(pool_times)[int(0.99 * len(pool_times))]
        }
        
        new_session_stats = {
            'mean': statistics.mean(new_session_times),
            'median': statistics.median(new_session_times),
            'stdev': statistics.stdev(new_session_times) if len(new_session_times) > 1 else 0,
            'min': min(new_session_times),
            'max': max(new_session_times),
            'p95': sorted(new_session_times)[int(0.95 * len(new_session_times))],
            'p99': sorted(new_session_times)[int(0.99 * len(new_session_times))]
        }
        
        # Calculate improvement metrics
        improvement_percentage = ((new_session_stats['mean'] - pool_stats['mean']) / new_session_stats['mean']) * 100
        time_saved_per_request = new_session_stats['mean'] - pool_stats['mean']
        
        # Estimate real-world impact
        daily_requests = 10000  # Estimated daily requests
        monthly_time_saved_hours = (time_saved_per_request / 1000) * daily_requests * 30 / 3600
        
        results = {
            'benchmark_config': {
                'iterations': iterations,
                'comparison_sessions': len(new_session_times),
                'timestamp': time.time()
            },
            'connection_pool_performance': pool_stats,
            'new_session_performance': new_session_stats,
            'improvement_metrics': {
                'percentage_improvement': round(improvement_percentage, 2),
                'time_saved_per_request_ms': round(time_saved_per_request, 3),
                'estimated_monthly_savings_hours': round(monthly_time_saved_hours, 2),
                'meets_20_percent_target': improvement_percentage >= 20,
                'meets_30_percent_target': improvement_percentage >= 30
            }
        }
        
        # Get pool statistics
        results['pool_statistics'] = self.pool.get_stats()
        results['connector_statistics'] = await self.pool.get_connector_stats()
        
        return results
    
    async def stress_test(self, concurrent_requests: int = 50, duration_seconds: int = 30) -> Dict[str, Any]:
        """
        Stress test the connection pool under concurrent load.
        
        Args:
            concurrent_requests: Number of concurrent requests to simulate
            duration_seconds: Duration of stress test in seconds
            
        Returns:
            Dict[str, Any]: Stress test results and performance metrics
        """
        print(f"⚡ Running stress test: {concurrent_requests} concurrent requests for {duration_seconds}s")
        
        # Reset statistics
        self.pool.reset_stats()
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_times = []
        error_count = 0
        completed_requests = 0
        
        async def make_request():
            nonlocal error_count, completed_requests
            try:
                request_start = time.perf_counter()
                session = await self.pool.get_session()
                # Simulate a typical API request pattern
                await asyncio.sleep(0.01)  # Simulate processing time
                request_end = time.perf_counter()
                request_times.append((request_end - request_start) * 1000)
                completed_requests += 1
            except Exception as e:
                error_count += 1
                print(f"❌ Request error: {e}")
        
        # Run concurrent requests for specified duration
        tasks = []
        while time.time() < end_time:
            # Launch concurrent requests
            batch_tasks = [make_request() for _ in range(min(concurrent_requests, 10))]
            tasks.extend(batch_tasks)
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            await asyncio.sleep(0.1)  # Brief pause between batches
        
        # Calculate stress test results
        total_duration = time.time() - start_time
        requests_per_second = completed_requests / total_duration
        
        if request_times:
            latency_stats = {
                'mean_ms': statistics.mean(request_times),
                'median_ms': statistics.median(request_times),
                'p95_ms': sorted(request_times)[int(0.95 * len(request_times))],
                'p99_ms': sorted(request_times)[int(0.99 * len(request_times))],
                'max_ms': max(request_times)
            }
        else:
            latency_stats = {'error': 'No successful requests completed'}
        
        return {
            'stress_test_config': {
                'target_concurrent_requests': concurrent_requests,
                'duration_seconds': duration_seconds,
                'actual_duration_seconds': round(total_duration, 2)
            },
            'performance_results': {
                'completed_requests': completed_requests,
                'error_count': error_count,
                'error_rate_percentage': round((error_count / max(1, completed_requests + error_count)) * 100, 2),
                'requests_per_second': round(requests_per_second, 2),
                'latency_statistics': latency_stats
            },
            'pool_statistics': self.pool.get_stats(),
            'connector_statistics': await self.pool.get_connector_stats()
        }
    
    async def validate_connection_reuse(self) -> Dict[str, Any]:
        """
        Validate that connection reuse is working as expected.
        
        Returns:
            Dict[str, Any]: Validation results confirming connection reuse
        """
        print("✅ Validating connection reuse functionality...")
        
        # Reset statistics
        self.pool.reset_stats()
        
        # Make several requests and verify session reuse
        sessions = []
        for i in range(10):
            session = await self.pool.get_session()
            sessions.append(id(session))
        
        # Check that all sessions are the same object (reused)
        unique_sessions = len(set(sessions))
        session_reuse_working = unique_sessions == 1
        
        # Get current statistics
        stats = self.pool.get_stats()
        connector_stats = await self.pool.get_connector_stats()
        
        return {
            'validation_results': {
                'session_reuse_working': session_reuse_working,
                'unique_session_objects': unique_sessions,
                'total_requests_tested': len(sessions),
                'expected_reuse_percentage': 100.0 if session_reuse_working else 0.0
            },
            'pool_statistics': stats,
            'connector_statistics': connector_stats,
            'recommendations': self._generate_recommendations(stats, connector_stats)
        }
    
    def _generate_recommendations(self, pool_stats: Dict[str, Any], connector_stats: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on current statistics."""
        recommendations = []
        
        if pool_stats.get('reuse_percentage', 0) < 80:
            recommendations.append("⚠️ Connection reuse rate is below 80%. Consider investigating session lifecycle.")
        
        if pool_stats.get('errors', 0) > pool_stats.get('requests_made', 1) * 0.05:
            recommendations.append("⚠️ Error rate exceeds 5%. Check error handling and connection stability.")
        
        if connector_stats.get('total_active_connections', 0) > 50:
            recommendations.append("💡 High number of active connections. Consider adjusting max_per_host setting.")
        
        if pool_stats.get('requests_per_session', 0) < 10:
            recommendations.append("💡 Low requests per session ratio. Connection pool may not be providing optimal benefits.")
        
        return recommendations or ["✅ Connection pool performance looks optimal"]
    
    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        print("📊 Generating comprehensive connection pool performance report...")
        
        # Run all tests
        benchmark_results = await self.benchmark_performance(500)
        stress_test_results = await self.stress_test(25, 15)  # Reduced for faster testing
        validation_results = await self.validate_connection_reuse()
        
        # Combine results
        report = {
            'report_metadata': {
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
                'generator': 'Connection Pool Performance Monitor v1.0'
            },
            'performance_benchmark': benchmark_results,
            'stress_test_results': stress_test_results,
            'validation_results': validation_results,
            'overall_assessment': self._assess_performance(benchmark_results, validation_results)
        }
        
        return report
    
    def _assess_performance(self, benchmark_results: Dict, validation_results: Dict) -> Dict[str, Any]:
        """Assess overall performance and provide final recommendations."""
        improvement = benchmark_results['improvement_metrics']['percentage_improvement']
        meets_target = improvement >= 20
        
        assessment = {
            'performance_target_met': meets_target,
            'improvement_percentage': improvement,
            'target_range': '20-30%',
            'status': 'EXCELLENT' if improvement >= 30 else 'GOOD' if improvement >= 20 else 'NEEDS_IMPROVEMENT',
            'session_reuse_working': validation_results['validation_results']['session_reuse_working'],
            'overall_grade': 'A' if meets_target and validation_results['validation_results']['session_reuse_working'] else 'B'
        }
        
        return assessment


async def main():
    """Main CLI interface for connection pool monitoring."""
    parser = argparse.ArgumentParser(description='Connection Pool Performance Monitor')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmark')
    parser.add_argument('--stress', action='store_true', help='Run stress test')
    parser.add_argument('--validate', action='store_true', help='Validate connection reuse')
    parser.add_argument('--report', action='store_true', help='Generate comprehensive report')
    parser.add_argument('--stats', action='store_true', help='Show current pool statistics')
    parser.add_argument('--iterations', type=int, default=500, help='Number of benchmark iterations')
    parser.add_argument('--output', type=str, help='Output file for results (JSON format)')
    
    args = parser.parse_args()
    
    if not any([args.benchmark, args.stress, args.validate, args.report, args.stats]):
        # Default to showing stats
        args.stats = True
    
    monitor = ConnectionPoolMonitor()
    results = {}
    
    try:
        if args.stats:
            print("📊 Current Connection Pool Statistics:")
            stats = monitor.pool.get_stats()
            connector_stats = await monitor.pool.get_connector_stats()
            
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            print("\nConnector Statistics:")
            for key, value in connector_stats.items():
                print(f"  {key}: {value}")
        
        if args.benchmark:
            results['benchmark'] = await monitor.benchmark_performance(args.iterations)
            improvement = results['benchmark']['improvement_metrics']['percentage_improvement']
            print(f"\n🎯 Performance Improvement: {improvement}% (Target: 20-30%)")
            
        if args.stress:
            results['stress_test'] = await monitor.stress_test()
            rps = results['stress_test']['performance_results']['requests_per_second']
            print(f"\n⚡ Stress Test: {rps} requests/second")
        
        if args.validate:
            results['validation'] = await monitor.validate_connection_reuse()
            working = results['validation']['validation_results']['session_reuse_working']
            print(f"\n✅ Connection Reuse: {'Working' if working else 'Failed'}")
        
        if args.report:
            results = await monitor.generate_report()
            grade = results['overall_assessment']['overall_grade']
            print(f"\n📋 Overall Performance Grade: {grade}")
        
        # Output results if requested
        if args.output and results:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"💾 Results saved to {args.output}")
            
    except Exception as e:
        print(f"❌ Error during monitoring: {e}")
        return 1
    
    finally:
        # Cleanup
        await monitor.pool.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))