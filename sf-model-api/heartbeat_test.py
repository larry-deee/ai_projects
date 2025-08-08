#!/usr/bin/env python3
"""
Heartbeat Test Script for SSE Streaming
Tests for :ka heartbeats every ~15 seconds during streaming
"""

import requests
import time
import json

def test_heartbeat_streaming():
    """Test streaming with heartbeat monitoring"""
    url = "http://127.0.0.1:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "claude-3-haiku",
        "messages": [{"role": "user", "content": "Tell me about artificial intelligence, machine learning, deep learning, neural networks, and their applications in various industries. Be detailed and comprehensive."}],
        "stream": True
    }
    
    start_time = time.time()
    heartbeat_count = 0
    chunk_count = 0
    
    print("🔄 Starting heartbeat test...")
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        print(f"✅ Response status: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                current_time = time.time()
                elapsed = current_time - start_time
                
                if line == ":ka":
                    heartbeat_count += 1
                    print(f"💓 HEARTBEAT #{heartbeat_count} at {elapsed:.1f}s")
                elif line.startswith("data: "):
                    chunk_count += 1
                    if chunk_count <= 3 or chunk_count % 10 == 0:
                        print(f"📦 Chunk #{chunk_count} at {elapsed:.1f}s: {line[:60]}...")
                
                # Stop after reasonable time to observe heartbeats
                if elapsed > 30:
                    print("⏰ Test timeout reached (30s)")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n📊 Test Summary:")
    print(f"   • Total heartbeats detected: {heartbeat_count}")
    print(f"   • Total data chunks: {chunk_count}")
    print(f"   • Test duration: {elapsed:.1f}s")
    print(f"   • Expected heartbeats (~1 every 15s): {max(1, int(elapsed / 15))}")

if __name__ == "__main__":
    test_heartbeat_streaming()