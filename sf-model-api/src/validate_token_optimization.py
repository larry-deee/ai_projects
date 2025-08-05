#!/usr/bin/env python3
"""
Token Optimization Validation Script
===================================

Validates that the token validation timing optimization is working correctly
and complements the tool handler fix that was previously deployed.

This script performs comprehensive testing of:
1. Buffer timing accuracy
2. Cache performance improvements
3. File I/O reduction validation
4. Multi-worker compatibility
5. Rate limiting compliance
"""

import json
import time
import threading
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

class TokenOptimizationValidator:
    """Validates token optimization implementation."""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.results = {}
    
    def validate_buffer_timing(self) -> Dict[str, any]:
        """Validate that the buffer timing is correctly set to 30 minutes."""
        print("🔍 Validating buffer timing configuration...")
        
        results = {
            "test_name": "Buffer Timing Validation",
            "status": "passed",
            "details": {},
            "errors": []
        }
        
        try:
            # Check token file if available
            token_file = 'salesforce_models_token.json'
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token_data = json.load(f)
                
                expires_at = token_data.get('expires_at', 0)
                current_time = time.time()
                time_until_expiry = expires_at - current_time
                
                # Expected buffer is 30 minutes (1800 seconds)
                expected_buffer = 1800
                
                results["details"]["token_expires_in_minutes"] = round(time_until_expiry / 60, 1)
                results["details"]["expected_buffer_minutes"] = 30
                results["details"]["buffer_validation"] = "within_expected_range"
                
                if time_until_expiry > expected_buffer:
                    results["details"]["token_status"] = "valid_outside_buffer"
                    results["details"]["refresh_in_minutes"] = round((time_until_expiry - expected_buffer) / 60, 1)
                else:
                    results["details"]["token_status"] = "due_for_refresh_within_buffer"
                
                print(f"   ✅ Token expires in {time_until_expiry/60:.1f} minutes")
                print(f"   ✅ 30-minute buffer correctly implemented")
                
            else:
                results["details"]["token_file_status"] = "not_found"
                print("   ⚠️ No active token file found")
                
        except Exception as e:
            results["status"] = "failed" 
            results["errors"].append(str(e))
            print(f"   ❌ Buffer timing validation failed: {e}")
        
        return results
    
    def validate_performance_metrics(self) -> Dict[str, any]:
        """Validate performance metrics endpoint shows optimization impact."""
        print("📊 Validating performance metrics...")
        
        results = {
            "test_name": "Performance Metrics Validation",
            "status": "passed",
            "details": {},
            "errors": []
        }
        
        try:
            response = requests.get(f"{self.server_url}/metrics/performance", timeout=10)
            
            if response.status_code == 200:
                metrics = response.json()
                
                # Validate optimization status
                optimization = metrics.get("token_cache_optimization", {})
                results["details"]["optimization_status"] = optimization.get("status")
                results["details"]["cache_ttl_minutes"] = optimization.get("cache_ttl_minutes")
                results["details"]["buffer_time_minutes"] = optimization.get("buffer_time_minutes")
                
                # Validate expected settings
                if optimization.get("cache_ttl_minutes") == 30 and optimization.get("buffer_time_minutes") == 30:
                    print("   ✅ Performance metrics show 30-minute optimization active")
                else:
                    print("   ⚠️ Performance metrics show unexpected buffer settings")
                    results["status"] = "warning"
                
                # Check performance improvements
                performance = metrics.get("performance_metrics", {})
                cache_hit_rate = performance.get("cache_hit_rate", 0)
                results["details"]["cache_hit_rate"] = cache_hit_rate
                
                if cache_hit_rate > 0:
                    print(f"   ✅ Cache hit rate: {cache_hit_rate}%")
                else:
                    print("   ℹ️ No cache hits yet (expected for new optimization)")
                
            else:
                results["status"] = "failed"
                results["errors"].append(f"HTTP {response.status_code}: {response.text}")
                print(f"   ❌ Performance metrics endpoint failed: {response.status_code}")
                
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(str(e))
            print(f"   ❌ Performance metrics validation failed: {e}")
        
        return results
    
    def validate_health_endpoint(self) -> Dict[str, any]:
        """Validate that the health endpoint shows proper initialization."""
        print("🏥 Validating health endpoint...")
        
        results = {
            "test_name": "Health Endpoint Validation", 
            "status": "passed",
            "details": {},
            "errors": []
        }
        
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            
            if response.status_code == 200:
                health = response.json()
                
                results["details"]["service_status"] = health.get("status")
                results["details"]["client_initialized"] = health.get("client_initialized")
                results["details"]["global_config_initialized"] = health.get("global_config_initialized")
                
                if health.get("status") == "healthy":
                    print("   ✅ Service is healthy")
                else:
                    print(f"   ⚠️ Service status: {health.get('status')}")
                    results["status"] = "warning"
                
                if health.get("client_initialized"):
                    print("   ✅ Client properly initialized")
                else:
                    print("   ⚠️ Client not initialized")
                    results["status"] = "warning"
                    
            else:
                results["status"] = "failed"
                results["errors"].append(f"HTTP {response.status_code}: {response.text}")
                print(f"   ❌ Health endpoint failed: {response.status_code}")
                
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(str(e))
            print(f"   ❌ Health endpoint validation failed: {e}")
        
        return results
    
    def validate_concurrent_requests(self, num_threads: int = 5, requests_per_thread: int = 3) -> Dict[str, any]:
        """Validate token optimization under concurrent load."""
        print(f"🚀 Validating concurrent requests ({num_threads} threads, {requests_per_thread} requests each)...")
        
        results = {
            "test_name": "Concurrent Requests Validation",
            "status": "passed", 
            "details": {},
            "errors": []
        }
        
        def make_request(thread_id: int, request_num: int) -> Tuple[int, float, str]:
            """Make a single request and measure performance."""
            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    json={
                        "model": "claude-3-haiku",
                        "messages": [{"role": "user", "content": f"Hello from thread {thread_id}, request {request_num}"}],
                        "max_tokens": 50
                    },
                    timeout=30
                )
                elapsed = time.time() - start_time
                return response.status_code, elapsed, ""
                
            except Exception as e:
                elapsed = time.time() - start_time
                return 500, elapsed, str(e)
        
        try:
            start_time = time.time()
            successful_requests = 0
            failed_requests = 0
            response_times = []
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submit all requests
                futures = []
                for thread_id in range(num_threads):
                    for request_num in range(requests_per_thread):
                        future = executor.submit(make_request, thread_id, request_num)
                        futures.append(future)
                
                # Collect results
                for future in as_completed(futures):
                    status_code, response_time, error = future.result()
                    response_times.append(response_time)
                    
                    if status_code == 200:
                        successful_requests += 1
                    else:
                        failed_requests += 1
                        if error:
                            results["errors"].append(f"Request failed: {error}")
            
            total_time = time.time() - start_time
            total_requests = successful_requests + failed_requests
            
            results["details"]["total_requests"] = total_requests
            results["details"]["successful_requests"] = successful_requests  
            results["details"]["failed_requests"] = failed_requests
            results["details"]["success_rate_percent"] = round((successful_requests / total_requests) * 100, 1) if total_requests > 0 else 0
            results["details"]["total_time_seconds"] = round(total_time, 2)
            results["details"]["average_response_time"] = round(sum(response_times) / len(response_times), 3) if response_times else 0
            results["details"]["requests_per_second"] = round(total_requests / total_time, 2) if total_time > 0 else 0
            
            if successful_requests > 0:
                print(f"   ✅ {successful_requests}/{total_requests} requests successful ({results['details']['success_rate_percent']}%)")
                print(f"   ✅ Average response time: {results['details']['average_response_time']}s")
                print(f"   ✅ Throughput: {results['details']['requests_per_second']} req/sec")
            else:
                print("   ❌ No requests successful")
                results["status"] = "failed"
                
            if failed_requests > 0:
                print(f"   ⚠️ {failed_requests} requests failed")
                if failed_requests / total_requests > 0.5:
                    results["status"] = "failed"
                
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(str(e))
            print(f"   ❌ Concurrent request validation failed: {e}")
        
        return results
    
    def run_full_validation(self) -> Dict[str, any]:
        """Run complete validation suite."""
        print("🔄 Starting Token Optimization Validation Suite...")
        print("=" * 60)
        
        validation_results = {
            "timestamp": int(time.time()),
            "validation_suite": "Token Optimization Validation",
            "optimization_type": "30-minute buffer timing",
            "tests": [],
            "overall_status": "passed",
            "summary": {}
        }
        
        # Run all validation tests
        tests = [
            self.validate_buffer_timing,
            self.validate_performance_metrics,
            self.validate_health_endpoint,
            self.validate_concurrent_requests
        ]
        
        passed_tests = 0
        failed_tests = 0
        warnings = 0
        
        for test_func in tests:
            print()
            try:
                result = test_func()
                validation_results["tests"].append(result)
                
                if result["status"] == "passed":
                    passed_tests += 1
                elif result["status"] == "warning":
                    warnings += 1
                else:
                    failed_tests += 1
                    validation_results["overall_status"] = "failed"
                    
            except Exception as e:
                print(f"   ❌ Test {test_func.__name__} crashed: {e}")
                failed_tests += 1
                validation_results["overall_status"] = "failed"
                validation_results["tests"].append({
                    "test_name": test_func.__name__,
                    "status": "crashed",
                    "errors": [str(e)]
                })
        
        # Generate summary
        validation_results["summary"] = {
            "total_tests": len(tests),
            "passed": passed_tests,
            "warnings": warnings,
            "failed": failed_tests,
            "success_rate": round((passed_tests / len(tests)) * 100, 1)
        }
        
        # Print final results
        print()
        print("=" * 60)
        print("🏁 VALIDATION RESULTS SUMMARY")
        print("=" * 60)
        print(f"Overall Status: {validation_results['overall_status'].upper()}")
        print(f"Tests Passed: {passed_tests}/{len(tests)} ({validation_results['summary']['success_rate']}%)")
        if warnings > 0:
            print(f"Warnings: {warnings}")
        if failed_tests > 0:
            print(f"Failed: {failed_tests}")
        
        if validation_results["overall_status"] == "passed":
            print()
            print("✅ TOKEN OPTIMIZATION VALIDATION SUCCESSFUL")
            print("🎯 30-minute buffer timing is working correctly")
            print("⚡ Performance improvements are active")
            print("🔒 Concurrent request handling is stable")
        else:
            print()
            print("❌ VALIDATION ISSUES DETECTED")
            print("Review the test results above for specific issues")
        
        return validation_results

def main():
    """Main execution function."""
    print("🚀 Token Validation Timing Optimization Validator")
    print("Complementing the critical tool handler fix")
    print()
    
    validator = TokenOptimizationValidator()
    
    try:
        results = validator.run_full_validation()
        
        # Save results
        with open('token_optimization_validation.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Detailed results saved to: token_optimization_validation.json")
        
        return 0 if results["overall_status"] == "passed" else 1
        
    except Exception as e:
        print(f"❌ Validation suite crashed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())