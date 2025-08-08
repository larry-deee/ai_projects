#!/usr/bin/env python3
"""
Server Startup and Log Validation Test
======================================

This script tests server startup behavior and validates that the expected
log messages and environment variable controls are working correctly.

Key Tests:
1. Server startup with proper environment variables
2. Log message validation for tool preservation
3. Environment variable display verification
4. Health check validation
"""

import subprocess
import time
import os
import sys
import signal
import requests
import threading
import queue
from contextlib import contextmanager

class ServerStartupTester:
    """Test server startup and log validation."""
    
    def __init__(self):
        self.server_process = None
        self.log_queue = queue.Queue()
        self.log_thread = None
        self.startup_timeout = 30
        
    def start_server_with_monitoring(self, env_vars=None):
        """Start server and monitor logs."""
        if env_vars is None:
            env_vars = {}
            
        # Set environment variables
        env = os.environ.copy()
        env.update(env_vars)
        
        print(f"🚀 Starting server with environment:")
        for key, value in env_vars.items():
            print(f"   {key}={value}")
        
        # Start server process
        try:
            self.server_process = subprocess.Popen(
                ["./start_async_service.sh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                env=env,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Start log monitoring thread
            self.log_thread = threading.Thread(
                target=self._monitor_logs,
                args=(self.server_process.stdout,)
            )
            self.log_thread.daemon = True
            self.log_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False
    
    def _monitor_logs(self, stdout):
        """Monitor server logs and queue them for analysis."""
        try:
            for line in iter(stdout.readline, ''):
                if line:
                    self.log_queue.put(line.strip())
                    print(f"[SERVER] {line.strip()}")
        except Exception as e:
            print(f"❌ Log monitoring error: {e}")
    
    def wait_for_server_ready(self, timeout=30):
        """Wait for server to be ready and healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get('http://localhost:8000/health', timeout=2)
                if response.status_code == 200:
                    print("✅ Server is healthy and ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
        
        print("❌ Server did not become ready within timeout")
        return False
    
    def stop_server(self):
        """Stop the server process."""
        if self.server_process:
            try:
                # Send SIGTERM to the process group
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self.server_process.wait(timeout=10)
                    print("✅ Server stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    print("⚠️ Server force-killed after timeout")
                    
            except Exception as e:
                print(f"❌ Error stopping server: {e}")
            finally:
                self.server_process = None
    
    def analyze_startup_logs(self):
        """Analyze collected startup logs for expected messages."""
        print("\n🔍 Analyzing startup logs...")
        
        logs = []
        
        # Collect logs with timeout
        timeout = time.time() + 10
        while time.time() < timeout:
            try:
                log = self.log_queue.get_nowait()
                logs.append(log)
            except queue.Empty:
                time.sleep(0.1)
        
        # Expected patterns in startup logs
        expected_patterns = {
            "Environment Variables Display": [
                "n8n compatibility",
                "n8n tool preservation", 
                "OpenAI-native passthrough",
                "Verbose tool logs",
                "Response debug"
            ],
            "Server Startup": [
                "Starting async development server",
                "Features enabled",
                "Connection pooling",
                "Async architecture"
            ],
            "Configuration Loading": [
                "configuration",
                "validated"
            ]
        }
        
        found_patterns = {category: [] for category in expected_patterns.keys()}
        
        # Analyze logs
        for log in logs:
            log_lower = log.lower()
            for category, patterns in expected_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in log_lower:
                        found_patterns[category].append((pattern, log))
        
        # Report results
        print("\n📊 Log Analysis Results:")
        all_good = True
        
        for category, patterns in expected_patterns.items():
            print(f"\n   {category}:")
            for pattern in patterns:
                found = any(pattern.lower() in found[0].lower() for found in found_patterns[category])
                status = "✅" if found else "❌"
                print(f"      {status} {pattern}")
                if not found:
                    all_good = False
        
        # Display some actual log lines for verification
        print(f"\n📝 Sample startup logs ({len(logs)} total lines):")
        for log in logs[-10:]:  # Show last 10 lines
            print(f"   {log}")
        
        return all_good
    
    @contextmanager
    def server_lifecycle(self, env_vars=None):
        """Context manager for server lifecycle management."""
        try:
            if self.start_server_with_monitoring(env_vars):
                if self.wait_for_server_ready():
                    yield True
                else:
                    yield False
            else:
                yield False
        finally:
            self.stop_server()

def test_default_configuration():
    """Test server startup with default configuration."""
    print("\n🧪 Test 1: Default Configuration")
    print("=" * 50)
    
    tester = ServerStartupTester()
    
    with tester.server_lifecycle() as server_ready:
        if not server_ready:
            return False
        
        # Give server time to fully initialize
        time.sleep(3)
        
        # Analyze logs
        logs_ok = tester.analyze_startup_logs()
        
        if logs_ok:
            print("✅ Default configuration startup successful")
            return True
        else:
            print("❌ Default configuration issues found")
            return False

def test_custom_environment():
    """Test server startup with custom environment variables."""
    print("\n🧪 Test 2: Custom Environment Configuration")
    print("=" * 50)
    
    custom_env = {
        'N8N_COMPAT_MODE': '1',
        'N8N_COMPAT_PRESERVE_TOOLS': '1',
        'OPENAI_NATIVE_TOOL_PASSTHROUGH': '1',
        'VERBOSE_TOOL_LOGS': '1',
        'SF_RESPONSE_DEBUG': 'true'
    }
    
    tester = ServerStartupTester()
    
    with tester.server_lifecycle(custom_env) as server_ready:
        if not server_ready:
            return False
        
        # Give server time to fully initialize
        time.sleep(3)
        
        # Analyze logs
        logs_ok = tester.analyze_startup_logs()
        
        # Test a quick API call to ensure functionality
        try:
            response = requests.post(
                'http://localhost:8000/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'openai/js 5.12.1'
                },
                json={
                    "model": "claude-3-haiku",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 50
                },
                timeout=10
            )
            
            api_ok = response.status_code == 200
            if api_ok:
                print("✅ API call successful with custom environment")
            else:
                print(f"❌ API call failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ API call error: {e}")
            api_ok = False
        
        if logs_ok and api_ok:
            print("✅ Custom environment configuration successful")
            return True
        else:
            print("❌ Custom environment configuration issues found")
            return False

def test_environment_variable_display():
    """Test that environment variables are properly displayed on startup."""
    print("\n🧪 Test 3: Environment Variable Display")
    print("=" * 50)
    
    test_env = {
        'N8N_COMPAT_MODE': '1',
        'N8N_COMPAT_PRESERVE_TOOLS': '0',  # Intentionally different
        'OPENAI_NATIVE_TOOL_PASSTHROUGH': '0',  # Intentionally different
        'VERBOSE_TOOL_LOGS': '1'
    }
    
    tester = ServerStartupTester()
    
    with tester.server_lifecycle(test_env) as server_ready:
        if not server_ready:
            return False
        
        time.sleep(3)
        
        # Check that environment variables are displayed correctly
        logs = []
        timeout = time.time() + 5
        while time.time() < timeout:
            try:
                log = tester.log_queue.get_nowait()
                logs.append(log)
            except queue.Empty:
                time.sleep(0.1)
        
        # Look for environment variable display
        env_display_found = False
        correct_values_found = {
            'N8N_COMPAT_PRESERVE_TOOLS': False,
            'OPENAI_NATIVE_TOOL_PASSTHROUGH': False
        }
        
        for log in logs:
            if "n8n tool preservation" in log.lower():
                env_display_found = True
                if "DISABLED" in log or "❌" in log:
                    correct_values_found['N8N_COMPAT_PRESERVE_TOOLS'] = True
            if "openai-native passthrough" in log.lower():
                if "DISABLED" in log or "❌" in log:
                    correct_values_found['OPENAI_NATIVE_TOOL_PASSTHROUGH'] = True
        
        if env_display_found and all(correct_values_found.values()):
            print("✅ Environment variables displayed correctly")
            return True
        else:
            print("❌ Environment variable display issues")
            print(f"   Display found: {env_display_found}")
            print(f"   Correct values: {correct_values_found}")
            return False

def main():
    """Run all server startup tests."""
    print("🚀 Server Startup and Log Validation Tests")
    print("==========================================")
    
    # Check prerequisites
    if not os.path.exists('./start_async_service.sh'):
        print("❌ start_async_service.sh not found in current directory")
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    if not os.access('./start_async_service.sh', os.X_OK):
        print("❌ start_async_service.sh is not executable")
        print("Run: chmod +x ./start_async_service.sh")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("Default Configuration", test_default_configuration),
        ("Custom Environment", test_custom_environment),
        ("Environment Variable Display", test_environment_variable_display)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n⚠️ Test interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Results Summary")
    print('='*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All server startup tests passed!")
        print("✅ Server startup and logging is working correctly!")
        sys.exit(0)
    else:
        print(f"\n❌ {len(results) - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n⚠️ Received interrupt signal, cleaning up...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    main()