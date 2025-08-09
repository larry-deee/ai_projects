#!/bin/bash
# Anthropic API Basic Examples
# These examples demonstrate basic usage of the Anthropic-compatible endpoints

set -e

API_BASE_URL="${API_BASE_URL:-http://localhost:8000/anthropic}"
ANTHROPIC_VERSION="2023-06-01"

echo "🚀 Anthropic API Basic Examples"
echo "================================="
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

echo "1️⃣  List Available Models"
echo "-------------------------"
curl -X GET "$API_BASE_URL/v1/models" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -H "Accept: application/json" \
  | jq '.data[] | {id, name, max_tokens, description}'

echo -e "\n\n2️⃣  Simple Message Completion"
echo "-----------------------------"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Hello, Claude! Can you introduce yourself briefly?"
      }
    ],
    "max_tokens": 1000
  }' | jq '.'

echo -e "\n\n3️⃣  Message with System Context"
echo "-------------------------------"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "What is the capital of France?"
      }
    ],
    "system": "You are a geography expert. Provide accurate and concise answers about world geography.",
    "max_tokens": 100
  }' | jq '.'

echo -e "\n\n4️⃣  Multi-turn Conversation"
echo "---------------------------"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "What is the largest planet in our solar system?"
      },
      {
        "role": "assistant",
        "content": "Jupiter is the largest planet in our solar system. It is a gas giant with a diameter of about 139,822 kilometers (86,881 miles), making it more than 11 times wider than Earth."
      },
      {
        "role": "user",
        "content": "How many moons does Jupiter have?"
      }
    ],
    "max_tokens": 200
  }' | jq '.'

echo -e "\n\n5️⃣  Count Tokens Example"
echo "------------------------"
curl -X POST "$API_BASE_URL/v1/messages/count_tokens" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "This is a test message to count tokens. It contains multiple words and punctuation!"
      }
    ],
    "system": "You are a helpful assistant."
  }' | jq '.'

echo -e "\n\n6️⃣  Temperature Variation Example"
echo "---------------------------------"
echo "High temperature (creative):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Write a creative haiku about coding."
      }
    ],
    "temperature": 0.9,
    "max_tokens": 100
  }' | jq '.content[0].text'

echo -e "\n\nLow temperature (deterministic):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "What is 2 + 2?"
      }
    ],
    "temperature": 0.0,
    "max_tokens": 50
  }' | jq '.content[0].text'

echo -e "\n\n7️⃣  Different Models Comparison"
echo "-------------------------------"
echo "Testing with Claude 3 Haiku (fastest):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-haiku-20240307",
    "messages": [
      {
        "role": "user",
        "content": "Explain quantum computing in one sentence."
      }
    ],
    "max_tokens": 100
  }' | jq '.content[0].text'

echo -e "\n\nTesting with Claude 3 Sonnet (balanced):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "messages": [
      {
        "role": "user",
        "content": "Explain quantum computing in one sentence."
      }
    ],
    "max_tokens": 100
  }' | jq '.content[0].text'

echo -e "\n\n8️⃣  Error Handling Example"
echo "--------------------------"
echo "Testing invalid model name (should return error):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "model": "invalid-model-name",
    "messages": [
      {
        "role": "user",
        "content": "This should fail"
      }
    ],
    "max_tokens": 100
  }' | jq '.'

echo -e "\n\nTesting missing required parameter (should return error):"
curl -X POST "$API_BASE_URL/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: $ANTHROPIC_VERSION" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "This should fail due to missing model parameter"
      }
    ],
    "max_tokens": 100
  }' | jq '.'

echo -e "\n\n✅ Basic examples completed!"
echo "==============================================="
echo "These examples demonstrate:"
echo "• Model listing and selection"
echo "• Basic message completion"
echo "• System context usage"
echo "• Multi-turn conversations"
echo "• Token counting"
echo "• Temperature control"
echo "• Model comparison"
echo "• Error handling"
echo ""
echo "For streaming examples, see: anthropic_streaming.sh"
echo "For Python examples, see: python_client_examples.py"