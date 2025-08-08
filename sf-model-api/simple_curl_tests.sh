#!/bin/bash

# Simple Curl Tests for N8N Compatibility 
# Validates the 6 core requirements using individual curl commands

echo "🚀 N8N Compatibility Manual Curl Tests"
echo "======================================"

SERVER_URL=${1:-"http://127.0.0.1:8000"}

echo "📡 Server: $SERVER_URL"
echo ""

echo "Test A: Plain chat (no tools) - content never null"
echo "=================================================="
curl -s -X POST $SERVER_URL/v1/chat/completions \
-H 'Content-Type: application/json' \
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Say hi"}],"tool_choice":"none"}' | jq '{content: .choices[0].message.content, tool_calls: .choices[0].message.tool_calls}'

echo -e "\n"

echo "Test B: n8n-compat (fake tools, UA with n8n)"
echo "============================================="
curl -i -s -X POST $SERVER_URL/v1/chat/completions \
-H 'Content-Type: application/json' \
-H 'User-Agent: n8n/1.105.4' \
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Test"}],"tools":[{"type":"function","function":{"name":"fake","parameters":{"type":"object"}}}],"tool_choice":"auto","stream":true}' \
| grep -E '(HTTP/|x-stream-downgraded|x-proxy-latency-ms|tool_calls)'

echo -e "\n"

echo "Test C: Invalid tools (non-n8n) - graceful fallback"
echo "==================================================="
curl -s -X POST $SERVER_URL/v1/chat/completions \
-H 'Content-Type: application/json' \
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Test"}],"tools":[{"type":"function","function":{}}],"tool_choice":"auto"}' | jq '{content: .choices[0].message.content, tool_calls: .choices[0].message.tool_calls}'

echo -e "\n"

echo "Test D: Valid tool (sanity check)"
echo "================================="
curl -s -X POST $SERVER_URL/v1/chat/completions \
-H 'Content-Type: application/json' \
-H 'User-Agent: Python/requests' \
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"What is weather?"}],"tools":[{"type":"function","function":{"name":"get_weather","description":"Get weather","parameters":{"type":"object","properties":{"location":{"type":"string"}},"required":["location"]}}}],"tool_choice":"auto"}' | jq '{content: .choices[0].message.content, tool_calls: .choices[0].message.tool_calls}'

echo -e "\n"

echo "Test E: Header validation"
echo "========================"
curl -i -s -X POST $SERVER_URL/v1/chat/completions \
-H 'Content-Type: application/json' \
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Test headers"}]}' \
| grep -E '(x-stream-downgraded|x-proxy-latency-ms)' 

echo -e "\n"

echo "Test F: Environment variable testing (N8N_COMPAT_MODE=0)"
echo "========================================================"
echo "Setting N8N_COMPAT_MODE=0 and testing with n8n UA..."
N8N_COMPAT_MODE=0 curl -s -X POST $SERVER_URL/v1/chat/completions \
-H 'Content-Type: application/json' \
-H 'User-Agent: n8n/1.0' \
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Test env"}],"tools":[{"type":"function","function":{"name":"test"}}]}' | jq '{content: .choices[0].message.content, tool_calls: .choices[0].message.tool_calls}'

echo -e "\n"

echo "✅ Manual curl tests completed. Check output above for validation."