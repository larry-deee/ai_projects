#!/usr/bin/env python3
"""
Master Test Suite Runner
========================

Comprehensive test suite runner that executes all compatibility and regression
tests for the Salesforce Models API Gateway. Provides detailed reporting,
performance analysis, and deployment readiness assessment.

Test Categories:
- n8n Client Compatibility Tests
- Claude Code Client Compatibility Tests  
- Performance Regression Tests
- API Specification Compliance Tests
- Integration Tests (when enabled)
"""

import os
import sys
import json
import time
import unittest
import argparse
import subprocess
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path

# Import test suites
try:
    from test_n8n_compatibility import run_n8n_test_suite
    from test_claude_code_compatibility import run_claude_code_test_suite
    from test_performance_regression import run_performance_test_suite
    from test_api_compliance import run_api_compliance_test_suite
    from test_response_format_compliance import TestResponseFormatCompliance
except ImportError as e:
    print(f"Warning: Could not import test modules: {e}")
    print("Make sure you're running from the tests directory")


@dataclass
class TestSuiteResult:
    """Result container for test suite execution."""
    name: str
    passed: bool
    tests_run: int
    failures: int
    errors: int
    duration: float
    details: str = ""


@dataclass
class MasterTestReport:
    """Master test report with comprehensive results."""
    total_tests: int
    total_passed: int
    total_failed: int
    total_errors: int
    success_rate: float
    total_duration: float
    suite_results: List[TestSuiteResult]
    deployment_ready: bool
    recommendations: List[str]


class MasterTestRunner:
    """Master test runner for comprehensive testing."""
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.results = []
        self.start_time = time.time()
        
        # Test configuration
        self.test_suites = [
            {
                'name': 'API Compliance Tests',
                'runner': self.run_api_compliance_suite,
                'critical': True,
                'description': 'OpenAI/Anthropic API specification compliance'
            },
            {
                'name': 'n8n Compatibility Tests', 
                'runner': self.run_n8n_suite,
                'critical': True,
                'description': 'n8n workflow integration and $fromAI() processing'
            },
            {
                'name': 'Claude Code Compatibility Tests',
                'runner': self.run_claude_code_suite,
                'critical': True,
                'description': 'Claude Code client integration and Anthropic format'
            },
            {
                'name': 'Performance Regression Tests',
                'runner': self.run_performance_suite,
                'critical': False,
                'description': 'Async optimization and performance validation'
            }
        ]
    
    def check_server_availability(self) -> bool:
        """Check if the test server is available."""
        try:
            import requests
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Server availability check failed: {e}")
            return False
    
    def run_api_compliance_suite(self) -> TestSuiteResult:
        """Run API compliance test suite."""
        print("\\n🔍 Running API Specification Compliance Tests...")
        start_time = time.time()
        
        try:
            success = run_api_compliance_test_suite()
            duration = time.time() - start_time
            
            return TestSuiteResult(
                name="API Compliance",
                passed=success,
                tests_run=0,  # Will be filled by individual runners
                failures=0,
                errors=0,
                duration=duration,
                details="OpenAI and Anthropic API specification validation"
            )
        except Exception as e:
            return TestSuiteResult(
                name="API Compliance",
                passed=False,
                tests_run=0,
                failures=0,
                errors=1,
                duration=time.time() - start_time,
                details=f"Suite execution failed: {e}"
            )
    
    def run_n8n_suite(self) -> TestSuiteResult:
        """Run n8n compatibility test suite."""
        print("\\n🧪 Running n8n Compatibility Tests...")
        start_time = time.time()
        
        try:
            success = run_n8n_test_suite()
            duration = time.time() - start_time
            
            return TestSuiteResult(
                name="n8n Compatibility",
                passed=success,
                tests_run=0,
                failures=0,
                errors=0,
                duration=duration,
                details="n8n workflow integration and parameter extraction"
            )
        except Exception as e:
            return TestSuiteResult(
                name="n8n Compatibility", 
                passed=False,
                tests_run=0,
                failures=0,
                errors=1,
                duration=time.time() - start_time,
                details=f"Suite execution failed: {e}"
            )
    
    def run_claude_code_suite(self) -> TestSuiteResult:
        """Run Claude Code compatibility test suite."""
        print("\\n🤖 Running Claude Code Compatibility Tests...")
        start_time = time.time()
        
        try:
            success = run_claude_code_test_suite()
            duration = time.time() - start_time
            
            return TestSuiteResult(
                name="Claude Code Compatibility",
                passed=success,
                tests_run=0,
                failures=0,
                errors=0,
                duration=duration,
                details="Claude Code client integration and Anthropic format"
            )
        except Exception as e:
            return TestSuiteResult(
                name="Claude Code Compatibility",
                passed=False,
                tests_run=0,
                failures=0,
                errors=1,
                duration=time.time() - start_time,
                details=f"Suite execution failed: {e}"
            )
    
    def run_performance_suite(self) -> TestSuiteResult:
        """Run performance regression test suite."""
        print("\\n⚡ Running Performance Regression Tests...")
        start_time = time.time()
        
        try:
            success = run_performance_test_suite()
            duration = time.time() - start_time
            
            return TestSuiteResult(
                name="Performance Regression",
                passed=success,
                tests_run=0,
                failures=0,
                errors=0,
                duration=duration,
                details="Async optimization and performance validation"
            )
        except Exception as e:
            return TestSuiteResult(
                name="Performance Regression",
                passed=False,
                tests_run=0,
                failures=0,
                errors=1,
                duration=time.time() - start_time,
                details=f"Suite execution failed: {e}"
            )
    
    def run_all_tests(self, skip_integration: bool = True) -> MasterTestReport:
        """Run all test suites and generate comprehensive report."""
        print("🚀 Starting Master Test Suite Execution")
        print("=" * 60)
        
        # Check server availability for integration tests
        server_available = self.check_server_availability()
        if not server_available and not skip_integration:
            print("⚠️ Server not available - integration tests will be skipped")
            skip_integration = True
        
        if skip_integration:
            print("ℹ️ Integration tests disabled (set INTEGRATION_TESTS=true to enable)")
            os.environ['INTEGRATION_TESTS'] = 'false'
        else:
            print("✅ Server available - integration tests enabled") 
            os.environ['INTEGRATION_TESTS'] = 'true'
        
        # Run each test suite
        suite_results = []
        for suite_config in self.test_suites:
            print(f"{chr(10)}📋 {suite_config['name']}")
            print(f"   {suite_config['description']}")
            
            try:
                result = suite_config['runner']()
                suite_results.append(result)
                
                status = "✅ PASSED" if result.passed else "❌ FAILED"
                print(f"   {status} - Duration: {result.duration:.1f}s")
                
            except Exception as e:
                print(f"   💥 CRASHED: {e}")
                suite_results.append(TestSuiteResult(
                    name=suite_config['name'],
                    passed=False,
                    tests_run=0,
                    failures=0,
                    errors=1,
                    duration=0,
                    details=f"Suite crashed: {e}"
                ))
        
        # Generate comprehensive report
        return self.generate_master_report(suite_results)
    
    def generate_master_report(self, suite_results: List[TestSuiteResult]) -> MasterTestReport:
        """Generate comprehensive master test report."""
        total_duration = time.time() - self.start_time
        
        # Aggregate statistics
        total_tests = sum(r.tests_run for r in suite_results)
        total_failures = sum(r.failures for r in suite_results)
        total_errors = sum(r.errors for r in suite_results)
        total_passed = sum(1 for r in suite_results if r.passed)
        
        # Calculate success rate
        total_suites = len(suite_results)
        success_rate = (total_passed / total_suites * 100) if total_suites > 0 else 0
        
        # Determine deployment readiness
        critical_suites = [s for s in self.test_suites if s.get('critical', False)]
        critical_results = [r for r in suite_results if any(cs['name'] == r.name for cs in critical_suites)]
        critical_passed = all(r.passed for r in critical_results)
        deployment_ready = critical_passed and success_rate >= 80
        
        # Generate recommendations
        recommendations = self.generate_recommendations(suite_results, deployment_ready)
        
        return MasterTestReport(
            total_tests=total_tests,
            total_passed=total_passed,
            total_failed=len(suite_results) - total_passed,
            total_errors=total_errors,
            success_rate=success_rate,
            total_duration=total_duration,
            suite_results=suite_results,
            deployment_ready=deployment_ready,
            recommendations=recommendations
        )
    
    def generate_recommendations(self, suite_results: List[TestSuiteResult], deployment_ready: bool) -> List[str]:
        """Generate deployment and improvement recommendations."""
        recommendations = []
        
        # Deployment readiness
        if deployment_ready:
            recommendations.append("✅ System is ready for production deployment")
            recommendations.append("🔄 All critical compatibility tests passed")
        else:
            recommendations.append("❌ System NOT ready for production deployment") 
            recommendations.append("🔧 Critical issues must be resolved before deployment")
        
        # Suite-specific recommendations
        failed_suites = [r for r in suite_results if not r.passed]
        for failed_suite in failed_suites:
            if "n8n" in failed_suite.name.lower():
                recommendations.append("🧪 n8n integration requires attention - check $fromAI() processing")
            elif "claude" in failed_suite.name.lower():
                recommendations.append("🤖 Claude Code integration issues - verify Anthropic format compliance")
            elif "performance" in failed_suite.name.lower():
                recommendations.append("⚡ Performance optimization needed - check async implementation")
            elif "api" in failed_suite.name.lower():
                recommendations.append("🔍 API compliance issues - review OpenAI/Anthropic specification adherence")
        
        # Performance recommendations
        performance_result = next((r for r in suite_results if "Performance" in r.name), None)
        if performance_result and performance_result.passed:
            recommendations.append("🚀 Async optimization is working correctly")
        elif performance_result:
            recommendations.append("⚠️ Performance regression detected - review async implementation")
        
        # General recommendations
        success_rate = len([r for r in suite_results if r.passed]) / len(suite_results) * 100
        if success_rate >= 90:
            recommendations.append("🎯 Excellent test coverage and compatibility")
        elif success_rate >= 75:
            recommendations.append("👍 Good test coverage with minor issues to address")
        else:
            recommendations.append("🔧 Multiple issues detected - comprehensive review needed")
        
        return recommendations
    
    def print_detailed_report(self, report: MasterTestReport):
        """Print detailed test report."""
        print("\\n" + "=" * 60)
        print("📊 MASTER TEST SUITE REPORT")
        print("=" * 60)
        
        # Summary statistics
        print(f"{chr(10)}📈 SUMMARY STATISTICS:")
        print(f"   Total Test Suites: {len(report.suite_results)}")
        print(f"   Suites Passed: {report.total_passed}")
        print(f"   Suites Failed: {report.total_failed}")
        print(f"   Success Rate: {report.success_rate:.1f}%")
        print(f"   Total Duration: {report.total_duration:.1f}s")
        
        # Deployment readiness
        status_icon = "✅" if report.deployment_ready else "❌"
        status_text = "READY" if report.deployment_ready else "NOT READY"
        print(f"{chr(10)}🚀 DEPLOYMENT STATUS: {status_icon} {status_text}")
        
        # Suite details
        print(f"{chr(10)}📋 SUITE DETAILS:")
        for result in report.suite_results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"   {status} {result.name} ({result.duration:.1f}s)")
            if result.details:
                print(f"      └─ {result.details}")
        
        # Recommendations
        print(f"{chr(10)}💡 RECOMMENDATIONS:")
        for recommendation in report.recommendations:
            print(f"   {recommendation}")
        
        print("\\n" + "=" * 60)
    
    def save_report_json(self, report: MasterTestReport, filename: str = None):
        """Save detailed report as JSON."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"test_report_{timestamp}.json"
        
        report_data = {
            'timestamp': int(time.time()),
            'summary': {
                'total_suites': len(report.suite_results),
                'suites_passed': report.total_passed,
                'suites_failed': report.total_failed,
                'success_rate': report.success_rate,
                'total_duration': report.total_duration,
                'deployment_ready': report.deployment_ready
            },
            'suite_results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'tests_run': r.tests_run,
                    'failures': r.failures,
                    'errors': r.errors,
                    'duration': r.duration,
                    'details': r.details
                }
                for r in report.suite_results
            ],
            'recommendations': report.recommendations
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
            print(f"{chr(10)}💾 Report saved to: {filename}")
        except Exception as e:
            print(f"{chr(10)}⚠️ Failed to save report: {e}")


def main():
    """Main entry point for master test runner."""
    parser = argparse.ArgumentParser(
        description="Master Test Suite Runner for Salesforce Models API Gateway"
    )
    parser.add_argument(
        '--server-url',
        default='http://localhost:8000',
        help='URL of the test server (default: http://localhost:8000)'
    )
    parser.add_argument(
        '--integration',
        action='store_true',
        help='Enable integration tests (requires running server)'
    )
    parser.add_argument(
        '--performance',
        action='store_true', 
        help='Enable performance tests'
    )
    parser.add_argument(
        '--save-report',
        help='Save JSON report to specified file'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Reduce output verbosity'
    )
    
    args = parser.parse_args()
    
    # Set environment variables for test configuration
    if args.integration:
        os.environ['INTEGRATION_TESTS'] = 'true'
    if args.performance:
        os.environ['PERFORMANCE_TESTS'] = 'true'
    
    # Create and run master test suite
    runner = MasterTestRunner(server_url=args.server_url)
    
    if not args.quiet:
        print("🎯 Salesforce Models API Gateway - Master Test Suite")
        print(f"🔧 Server URL: {args.server_url}")
        print(f"🔍 Integration tests: {'enabled' if args.integration else 'disabled'}")
        print(f"⚡ Performance tests: {'enabled' if args.performance else 'disabled'}")
    
    # Run all tests
    report = runner.run_all_tests(skip_integration=not args.integration)
    
    # Print detailed report
    if not args.quiet:
        runner.print_detailed_report(report)
    
    # Save JSON report if requested
    if args.save_report:
        runner.save_report_json(report, args.save_report)
    
    # Exit with appropriate code
    exit_code = 0 if report.deployment_ready else 1
    if not args.quiet:
        exit_status = "SUCCESS" if exit_code == 0 else "FAILURE"
        print(f"{chr(10)}🏁 Test execution completed with status: {exit_status}")
    
    return exit_code


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)