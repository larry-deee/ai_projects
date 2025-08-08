#!/usr/bin/env python3
"""
Master Test Runner for Tool Behaviour Compatibility Layer
=========================================================

This script runs all test suites to comprehensively validate the
Tool Behaviour Compatibility Layer implementation.

Test Suites:
1. Comprehensive API Tests
2. cURL Scenario Tests  
3. Server Startup Tests

Usage:
    python run_all_compatibility_tests.py [--quick] [--verbose]
"""

import sys
import os
import time
import subprocess
import argparse
from typing import List, Tuple, Dict, Any
import requests

def check_prerequisites() -> bool:
    """Check that all prerequisites are met."""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    # Check required files exist
    required_files = [
        './start_async_service.sh',
        'test_tool_compatibility_comprehensive.py',
        'test_curl_scenarios.py',
        'test_server_startup.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Required file not found: {file}")
            return False
        if file.endswith('.sh') and not os.access(file, os.X_OK):
            print(f"❌ File not executable: {file}")
            print(f"Run: chmod +x {file}")
            return False
    
    # Check required Python modules
    required_modules = ['requests', 'json', 'subprocess']
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            print(f"❌ Required Python module not found: {module}")
            return False
    
    print("✅ All prerequisites met")
    return True

def is_server_running() -> bool:
    """Check if the server is already running."""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def wait_for_server_stop(timeout: int = 30) -> bool:
    """Wait for server to stop running."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_server_running():
            return True
        time.sleep(1)
    return False

def run_test_suite(script_name: str, description: str, args: List[str] = None) -> Tuple[bool, str, float]:
    """Run a test suite and return results."""
    print(f"\n🧪 Running {description}")
    print("=" * 80)
    
    start_time = time.time()
    cmd = [sys.executable, script_name]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per test suite
        )
        
        execution_time = time.time() - start_time
        
        # Print output for visibility
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        status_msg = f"{'✅ PASSED' if success else '❌ FAILED'} in {execution_time:.1f}s"
        
        return success, status_msg, execution_time
        
    except subprocess.TimeoutExpired:
        execution_time = time.time() - start_time
        return False, f"❌ TIMEOUT after {execution_time:.1f}s", execution_time
    
    except Exception as e:
        execution_time = time.time() - start_time
        return False, f"❌ ERROR: {e}", execution_time

def display_environment_info():
    """Display current environment configuration."""
    print("\n📋 Environment Configuration")
    print("=" * 50)
    
    env_vars = [
        'N8N_COMPAT_MODE',
        'N8N_COMPAT_PRESERVE_TOOLS',
        'OPENAI_NATIVE_TOOL_PASSTHROUGH',
        'VERBOSE_TOOL_LOGS',
        'SF_RESPONSE_DEBUG'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'not_set')
        print(f"   {var}: {value}")

def run_acceptance_criteria_validation(results: List[Tuple[str, bool, str, float]]) -> Dict[str, bool]:
    """Validate that acceptance criteria are met based on test results."""
    print("\n📊 Acceptance Criteria Validation")
    print("=" * 50)
    
    # Map test results to acceptance criteria
    criteria_map = {
        "n8n clients preserve tools": any("comprehensive" in name.lower() for name, passed, _, _ in results if passed),
        "Tool calls work end-to-end": any("curl" in name.lower() for name, passed, _, _ in results if passed),
        "OpenAI-native models use passthrough": any("comprehensive" in name.lower() for name, passed, _, _ in results if passed),
        "Response normalization consistent": any("comprehensive" in name.lower() for name, passed, _, _ in results if passed),
        "Environment variables control behavior": any("startup" in name.lower() for name, passed, _, _ in results if passed),
        "No regression in existing functionality": all(passed for _, passed, _, _ in results),
        "Performance remains acceptable": all(exec_time < 60 for _, _, _, exec_time in results)  # All tests complete within 60s
    }
    
    all_passed = True
    for criterion, passed in criteria_map.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {criterion}")
        if not passed:
            all_passed = False
    
    return {"all_criteria_met": all_passed, "individual_criteria": criteria_map}

def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description='Run Tool Behaviour Compatibility Layer tests')
    parser.add_argument('--quick', action='store_true', help='Skip server startup tests (faster)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--server-running', action='store_true', help='Assume server is already running')
    
    args = parser.parse_args()
    
    print("🚀 Tool Behaviour Compatibility Layer - Master Test Runner")
    print("=" * 80)
    print("Testing the complete implementation including:")
    print("   • n8n tool preservation behavior")
    print("   • OpenAI-native model passthrough")
    print("   • Response normalization across backends")
    print("   • Environment variable controls")
    print("   • Cross-backend compatibility")
    print("   • Performance validation")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Display environment
    display_environment_info()
    
    # Check server status
    server_was_running = is_server_running()
    if server_was_running and not args.server_running:
        print("\n⚠️ Server appears to be already running")
        print("   Use --server-running flag to continue with existing server")
        print("   Or stop the server first to allow startup tests to run")
        response = input("\nContinue with existing server? (y/N): ")
        if response.lower() != 'y':
            print("Exiting. Please stop the server or use --server-running flag")
            sys.exit(1)
        args.server_running = True
    
    # Define test suites
    test_suites = []
    
    if not args.quick and not args.server_running:
        test_suites.append((
            'test_server_startup.py',
            'Server Startup and Log Validation Tests',
            []
        ))
    
    test_suites.extend([
        (
            'test_tool_compatibility_comprehensive.py',
            'Comprehensive API Compatibility Tests',
            []
        ),
        (
            'test_curl_scenarios.py', 
            'cURL Scenario Tests',
            []
        )
    ])
    
    # Run test suites
    results = []
    total_start_time = time.time()
    
    for script, description, suite_args in test_suites:
        success, message, exec_time = run_test_suite(script, description, suite_args)
        results.append((description, success, message, exec_time))
        
        if not success:
            print(f"\n⚠️ Test suite failed: {description}")
            if not args.verbose:
                print("Use --verbose flag for more details")
    
    total_execution_time = time.time() - total_start_time
    
    # Generate final report
    print("\n" + "=" * 80)
    print("📊 Final Test Report")
    print("=" * 80)
    
    passed_suites = sum(1 for _, passed, _, _ in results if passed)
    total_suites = len(results)
    
    print(f"\nTest Suite Results:")
    for name, passed, message, exec_time in results:
        print(f"   {message} - {name}")
    
    print(f"\nSummary:")
    print(f"   Total Test Suites: {total_suites}")
    print(f"   Passed: {passed_suites}")
    print(f"   Failed: {total_suites - passed_suites}")
    print(f"   Success Rate: {(passed_suites/total_suites*100):.1f}%")
    print(f"   Total Execution Time: {total_execution_time:.1f}s")
    
    # Validate acceptance criteria
    criteria_validation = run_acceptance_criteria_validation(results)
    
    # Final verdict
    print("\n" + "=" * 80)
    if passed_suites == total_suites and criteria_validation["all_criteria_met"]:
        print("🎉 ALL TESTS PASSED SUCCESSFULLY!")
        print("✅ Tool Behaviour Compatibility Layer implementation is COMPLETE and WORKING!")
        print("\nExpected behaviors confirmed:")
        print("   ✅ n8n clients preserve tools (logs show 'tools PRESERVED')")
        print("   ✅ Tool calls work end-to-end with round-trip conversations") 
        print("   ✅ OpenAI-native models use direct passthrough")
        print("   ✅ All backends output consistent OpenAI tool schema")
        print("   ✅ Environment variables control behavior as expected")
        print("   ✅ No regression in existing functionality")
        print("   ✅ Performance remains acceptable")
        
        print(f"\nThe server is ready for production with Tool Behaviour Compatibility Layer!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("The Tool Behaviour Compatibility Layer implementation needs attention.")
        print(f"\nFailed test suites: {total_suites - passed_suites}")
        
        failed_criteria = [k for k, v in criteria_validation["individual_criteria"].items() if not v]
        if failed_criteria:
            print("Failed acceptance criteria:")
            for criterion in failed_criteria:
                print(f"   ❌ {criterion}")
        
        print("\nPlease review the test output above for specific issues.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Test execution interrupted by user")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)