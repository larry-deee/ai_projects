#!/usr/bin/env python3
"""
Connection Timeout Monitoring Script
====================================

Monitors the Salesforce Models API Gateway for connection issues, timeouts,
and EPIPE errors. Use this script to diagnose production issues.

Usage:
    python connection_monitor.py [--endpoint URL] [--interval SECONDS]
"""

import requests
import time
import json
import logging
import threading
from typing import Dict, Any, List
import statistics
import signal
import sys
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('connection_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConnectionMonitor:
    """Monitor connection health and performance."""
    
    def __init__(self, base_url: str = "http://localhost:8000", interval: int = 30):
        self.base_url = base_url
        self.interval = interval
        self.running = False
        self.metrics = {
            'successful_requests': 0,
            'failed_requests': 0,
            'timeout_errors': 0,
            'connection_errors': 0,
            'response_times': [],
            'last_24h_errors': []
        }
        self.alert_threshold = 3  # Alert after 3 consecutive failures
        
    def test_health_endpoint(self) -> Dict[str, Any]:
        """Test the health endpoint."""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/health",
                timeout=10,
                headers={'Connection': 'keep-alive'}
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'response_time': response_time,
                    'data': response.json()
                }
            else:
                return {
                    'status': 'http_error',
                    'response_time': response_time,
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': 'Request timed out'}
        except requests.exceptions.ConnectionError as e:
            return {'status': 'connection_error', 'error': str(e)}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def test_chat_endpoint(self) -> Dict[str, Any]:
        """Test the chat completions endpoint."""
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "claude-3-haiku",
                    "messages": [{"role": "user", "content": "Health check"}],
                    "max_tokens": 50,
                    "stream": False
                },
                timeout=30,
                headers={
                    'Content-Type': 'application/json',
                    'Connection': 'keep-alive'
                }
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                content_length = len(response.content)
                return {
                    'status': 'success',
                    'response_time': response_time,
                    'content_length': content_length,
                    'has_content': bool(data.get('choices', [{}])[0].get('message', {}).get('content'))
                }
            else:
                return {
                    'status': 'http_error',
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'content': response.text[:500]
                }
                
        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': 'Request timed out'}
        except requests.exceptions.ConnectionError as e:
            return {'status': 'connection_error', 'error': str(e)}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def test_streaming_endpoint(self) -> Dict[str, Any]:
        """Test streaming endpoint for connection issues."""
        try:
            start_time = time.time()
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": "claude-3-haiku",
                    "messages": [{"role": "user", "content": "Stream test"}],
                    "max_tokens": 100,
                    "stream": True
                },
                timeout=30,
                stream=True,
                headers={
                    'Content-Type': 'application/json',
                    'Connection': 'keep-alive'
                }
            )
            
            chunks_received = 0
            last_chunk_time = time.time()
            
            for line in response.iter_lines():
                if line:
                    chunks_received += 1
                    last_chunk_time = time.time()
                    
                    # Check for timeout between chunks
                    if time.time() - start_time > 30:
                        break
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': 'success' if chunks_received > 0 else 'no_chunks',
                'response_time': response_time,
                'chunks_received': chunks_received,
                'stream_complete': True
            }
            
        except requests.exceptions.Timeout:
            return {'status': 'timeout', 'error': 'Stream timed out'}
        except requests.exceptions.ConnectionError as e:
            return {'status': 'connection_error', 'error': str(e)}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def update_metrics(self, test_name: str, result: Dict[str, Any]):
        """Update performance metrics."""
        current_time = datetime.now()
        
        if result['status'] == 'success':
            self.metrics['successful_requests'] += 1
            if 'response_time' in result:
                self.metrics['response_times'].append(result['response_time'])
                # Keep only last 100 response times
                if len(self.metrics['response_times']) > 100:
                    self.metrics['response_times'] = self.metrics['response_times'][-100:]
        else:
            self.metrics['failed_requests'] += 1
            
            # Track specific error types
            if result['status'] == 'timeout':
                self.metrics['timeout_errors'] += 1
            elif result['status'] == 'connection_error':
                self.metrics['connection_errors'] += 1
            
            # Track errors in last 24 hours
            error_entry = {
                'timestamp': current_time,
                'test': test_name,
                'error': result.get('error', result['status'])
            }
            self.metrics['last_24h_errors'].append(error_entry)
            
            # Clean up old errors (24 hours)
            cutoff_time = current_time - timedelta(hours=24)
            self.metrics['last_24h_errors'] = [
                e for e in self.metrics['last_24h_errors'] 
                if e['timestamp'] > cutoff_time
            ]
    
    def check_alerts(self) -> List[str]:
        """Check for alert conditions."""
        alerts = []
        
        # High error rate
        total_requests = self.metrics['successful_requests'] + self.metrics['failed_requests']
        if total_requests > 10:
            error_rate = (self.metrics['failed_requests'] / total_requests) * 100
            if error_rate > 20:
                alerts.append(f"High error rate: {error_rate:.1f}%")
        
        # Timeout alerts
        if self.metrics['timeout_errors'] > 5:
            alerts.append(f"Multiple timeout errors: {self.metrics['timeout_errors']}")
        
        # Connection alerts
        if self.metrics['connection_errors'] > 3:
            alerts.append(f"Multiple connection errors: {self.metrics['connection_errors']}")
        
        # Response time alerts
        if self.metrics['response_times']:
            avg_response_time = statistics.mean(self.metrics['response_times'])
            if avg_response_time > 10000:  # 10 seconds
                alerts.append(f"High average response time: {avg_response_time:.0f}ms")
        
        # Recent error cluster
        recent_errors = [
            e for e in self.metrics['last_24h_errors']
            if e['timestamp'] > datetime.now() - timedelta(minutes=10)
        ]
        if len(recent_errors) >= 3:
            alerts.append(f"Error cluster detected: {len(recent_errors)} errors in last 10 minutes")
        
        return alerts
    
    def print_status(self):
        """Print current status."""
        print(f"\n{'='*60}")
        print(f"Connection Monitor Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Test health endpoint
        print("\n🏥 Health Endpoint Test:")
        health_result = self.test_health_endpoint()
        self.update_metrics('health', health_result)
        
        if health_result['status'] == 'success':
            print(f"   ✅ Health check passed ({health_result['response_time']:.0f}ms)")
            data = health_result.get('data', {})
            print(f"   📊 Client initialized: {data.get('client_initialized', 'unknown')}")
            print(f"   📊 Global config initialized: {data.get('global_config_initialized', 'unknown')}")
        else:
            print(f"   ❌ Health check failed: {health_result.get('error', 'Unknown error')}")
        
        # Test chat endpoint
        print("\n💬 Chat Endpoint Test:")
        chat_result = self.test_chat_endpoint()
        self.update_metrics('chat', chat_result)
        
        if chat_result['status'] == 'success':
            print(f"   ✅ Chat request succeeded ({chat_result['response_time']:.0f}ms)")
            print(f"   📊 Content length: {chat_result.get('content_length', 0)} bytes")
            print(f"   📊 Has content: {chat_result.get('has_content', False)}")
        else:
            print(f"   ❌ Chat request failed: {chat_result.get('error', 'Unknown error')}")
            if 'status_code' in chat_result:
                print(f"   📊 Status code: {chat_result['status_code']}")
        
        # Test streaming endpoint
        print("\n🔄 Streaming Endpoint Test:")
        stream_result = self.test_streaming_endpoint()
        self.update_metrics('streaming', stream_result)
        
        if stream_result['status'] == 'success':
            print(f"   ✅ Streaming succeeded ({stream_result['response_time']:.0f}ms)")
            print(f"   📊 Chunks received: {stream_result.get('chunks_received', 0)}")
        else:
            print(f"   ❌ Streaming failed: {stream_result.get('error', 'Unknown error')}")
        
        # Performance metrics
        print("\n📈 Performance Metrics:")
        total_requests = self.metrics['successful_requests'] + self.metrics['failed_requests']
        if total_requests > 0:
            success_rate = (self.metrics['successful_requests'] / total_requests) * 100
            print(f"   Success rate: {success_rate:.1f}% ({self.metrics['successful_requests']}/{total_requests})")
        
        if self.metrics['response_times']:
            avg_time = statistics.mean(self.metrics['response_times'])
            p95_time = sorted(self.metrics['response_times'])[int(len(self.metrics['response_times']) * 0.95)]
            print(f"   Avg response time: {avg_time:.0f}ms")
            print(f"   P95 response time: {p95_time:.0f}ms")
        
        print(f"   Timeout errors: {self.metrics['timeout_errors']}")
        print(f"   Connection errors: {self.metrics['connection_errors']}")
        print(f"   Errors in last 24h: {len(self.metrics['last_24h_errors'])}")
        
        # Check for alerts
        alerts = self.check_alerts()
        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(f"   ⚠️  {alert}")
                logger.warning(f"ALERT: {alert}")
        
        print(f"\nNext check in {self.interval} seconds...")
    
    def run(self):
        """Run the monitoring loop."""
        self.running = True
        print(f"🔍 Starting connection monitor for {self.base_url}")
        print(f"📊 Check interval: {self.interval} seconds")
        print("🛑 Press Ctrl+C to stop")
        
        try:
            while self.running:
                self.print_status()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped by user")
            self.running = False
    
    def stop(self):
        """Stop monitoring."""
        self.running = False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor connection health')
    parser.add_argument('--endpoint', default='http://localhost:8000',
                       help='Base URL of the API gateway (default: http://localhost:8000)')
    parser.add_argument('--interval', type=int, default=30,
                       help='Check interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    monitor = ConnectionMonitor(args.endpoint, args.interval)
    
    def signal_handler(signum, frame):
        print("\n🛑 Received interrupt signal, stopping monitor...")
        monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor.run()

if __name__ == "__main__":
    main()