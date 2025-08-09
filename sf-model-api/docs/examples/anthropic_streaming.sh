#!/bin/bash
# Anthropic API Streaming Examples
# These examples demonstrate SSE streaming usage with exact Anthropic event sequence

set -e

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/anthropic}"
ANTHROPIC_VERSION="2023-06-01"

echo "🌊 Anthropic API Streaming Examples"
echo "===================================="
echo "Using API base URL: $API_BASE_URL"
echo ""

# Function to check if server is running
check_server() {
    echo "🔍 Checking server health..."
    if curl -s -f "$API_BASE_URL/../health" > /dev/null; then
        echo "✅ Server is running"
    else
        echo "❌ Server is not running. Please start the server first."
        exit 1
    fi
    echo ""
}

# Check server status
check_server

echo "1️⃣  Basic Streaming Example"
echo "---------------------------"
echo "Streaming a short response (watch for event types):"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Say hello and introduce yourself briefly."
      }
    ],
    "max_tokens": 100,
    "stream": true
  }'

echo -e "\n\n2️⃣  Streaming with System Context"
echo "---------------------------------"
echo "Streaming response with system context:"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Explain the concept of recursion in programming."
      }
    ],
    "system": "You are a computer science teacher. Explain concepts clearly with simple examples.",
    "max_tokens": 200,
    "stream": true
  }'

echo -e "\n\n3️⃣  Creative Writing Stream"
echo "---------------------------"
echo "Streaming a creative writing task (longer response):"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Write a short poem about the ocean at sunset."
      }
    ],
    "temperature": 0.8,
    "max_tokens": 300,
    "stream": true
  }'

echo -e "\n\n4️⃣  Multi-turn Streaming Conversation"
echo "-------------------------------------"
echo "Streaming in a multi-turn conversation:"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "What is machine learning?"
      },
      {
        "role": "assistant",
        "content": "Machine learning is a subset of artificial intelligence (AI) that enables computer systems to learn and improve from experience without being explicitly programmed for every task."
      },
      {
        "role": "user",
        "content": "Can you give me a simple real-world example?"
      }
    ],
    "max_tokens": 200,
    "stream": true
  }'

echo -e "\n\n5️⃣  Different Model Streaming"
echo "-----------------------------"
echo "Comparing streaming with different models:"
echo ""
echo "Claude 3 Sonnet (more detailed, slower):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "messages": [
      {
        "role": "user",
        "content": "Explain the difference between TCP and UDP in one paragraph."
      }
    ],
    "max_tokens": 150,
    "stream": true
  }'

echo -e "\n\n6️⃣  Temperature Effect on Streaming"
echo "-----------------------------------"
echo "High temperature streaming (more creative/random):"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Create a quirky metaphor for debugging code."
      }
    ],
    "temperature": 0.9,
    "max_tokens": 100,
    "stream": true
  }'

echo -e "\n\nLow temperature streaming (more deterministic):"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "List the first 5 prime numbers."
      }
    ],
    "temperature": 0.1,
    "max_tokens": 50,
    "stream": true
  }'

echo -e "\n\n7️⃣  Understanding SSE Event Sequence"
echo "------------------------------------"
echo "This example shows the exact Anthropic SSE event sequence:"
echo "• message_start: Begins the response"
echo "• content_block_start: Starts a content block"
echo "• content_block_delta: Streaming text chunks"
echo "• content_block_stop: Ends the content block"
echo "• message_delta: Updates with stop reason"
echo "• message_stop: Completes the response"
echo ""
echo "Watch for these events in the following stream:"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Count slowly from 1 to 5, with a word about each number."
      }
    ],
    "max_tokens": 100,
    "stream": true
  }'

echo -e "\n\n8️⃣  Streaming with Heartbeats"
echo "-----------------------------"
echo "Long-running stream to demonstrate heartbeats (:ka events every ~15s):"
echo "Note: Heartbeats prevent connection timeouts during long streams"
echo ""
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Write a detailed story about a space explorer discovering a new planet. Make it at least 3 paragraphs long."
      }
    ],
    "max_tokens": 500,
    "stream": true
  }'

echo -e "\n\n9️⃣  Performance Comparison: Streaming vs Non-streaming"
echo "-----------------------------------------------------"
echo "Non-streaming (wait for complete response):"
time curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Write a haiku about technology."
      }
    ],
    "max_tokens": 100,
    "stream": false
  }' | jq '.content[0].text'

echo -e "\n\nStreaming (immediate response start):"
time curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -N \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Write a haiku about technology."
      }
    ],
    "max_tokens": 100,
    "stream": true
  }' > /dev/null

echo -e "\n\n🔟 Client Integration Testing"
echo "-----------------------------"
echo "Testing with various tools:"
echo ""

echo "Using wget for streaming:"
wget -O - \
  --header="Content-Type: application/json" \
  --header="anthropic-version: $ANTHROPIC_VERSION" \
  --post-data='{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Say hi in 3 different languages."
      }
    ],
    "max_tokens": 50,
    "stream": true
  }' \
  "$API_BASE_URL/v1/messages" 2>/dev/null

echo -e "\n\n✅ Streaming examples completed!"
echo "==============================================="
echo "These examples demonstrated:"
echo "• Basic SSE streaming"
echo "• Event sequence understanding (message_start → content_block_* → message_stop)"
echo "• System context with streaming"
echo "• Multi-turn conversation streaming"
echo "• Model comparison for streaming"
echo "• Temperature effects on streaming"
echo "• SSE heartbeats for long streams"
echo "• Performance comparison"
echo "• Client integration testing"
echo ""
echo "📚 Key SSE Events to Watch For:"
echo "• message_start: Begins the response"
echo "• content_block_start: Starts content generation"  
echo "• content_block_delta: Actual streamed text chunks"
echo "• content_block_stop: Ends content generation"
echo "• message_delta: Provides final metadata (stop reason, token usage)"
echo "• message_stop: Completes the response"
echo "• :ka: Heartbeat events (every ~15 seconds)"
echo ""
echo "For Python streaming examples, see: python_client_examples.py"