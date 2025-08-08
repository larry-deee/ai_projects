#!/bin/bash
# Streaming Functionality Regression Test Suite
# Usage: ./streaming_regression_tests.sh
# Assumes server is running on localhost:8000

echo "🚀 Starting Streaming Regression Test Suite"
echo "============================================="

SERVER_URL="http://127.0.0.1:8000"
RESULTS_FILE="test_results_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_count=0
passed_count=0
failed_count=0

run_test() {
    local test_name="$1"
    local curl_command="$2"
    local expected_pattern="$3"
    
    test_count=$((test_count + 1))
    echo -e "\n📋 Test ${test_count}: ${test_name}"
    echo "Command: ${curl_command}"
    
    # Run the test
    result=$(eval "$curl_command" 2>&1)
    
    if echo "$result" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        passed_count=$((passed_count + 1))
        echo "$result" | head -5 | sed 's/^/   → /'
    else
        echo -e "${RED}❌ FAILED${NC}"
        failed_count=$((failed_count + 1))
        echo "$result" | head -10 | sed 's/^/   → /'
    fi
    
    echo "Test ${test_count}: ${test_name} - $(date)" >> "$RESULTS_FILE"
    echo "$result" >> "$RESULTS_FILE"
    echo "---" >> "$RESULTS_FILE"
}

echo "Starting tests at $(date)" > "$RESULTS_FILE"

# Test A: Tool calling with stream downgrade
run_test "Tool Calling Stream Downgrade" \
    "curl -s -X POST $SERVER_URL/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\": \"claude-3-haiku\", \"messages\": [{\"role\": \"user\", \"content\": \"What is 2+2?\"}], \"stream\": true, \"tools\": [{\"type\": \"function\", \"function\": {\"name\": \"calculator\", \"description\": \"Basic calculator\"}}]}' -D -" \
    "X-Stream-Downgraded: true"

# Test B: OpenAI streaming format
run_test "OpenAI Streaming Format" \
    "curl -s -X POST $SERVER_URL/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\": \"claude-3-haiku\", \"messages\": [{\"role\": \"user\", \"content\": \"Tell me about AI\"}], \"stream\": true}' --max-time 10 | head -5" \
    "data:"

# Test C: Anthropic streaming format  
run_test "Anthropic Streaming Format" \
    "curl -s -X POST $SERVER_URL/v1/messages -H 'Content-Type: application/json' -d '{\"model\": \"claude-3-haiku\", \"max_tokens\": 100, \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}], \"stream\": true}' --max-time 10 | head -3" \
    "event:"

# Test D: Non-streaming standard request
run_test "Non-Streaming Request" \
    "curl -s -X POST $SERVER_URL/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\": \"claude-3-haiku\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}' -D -" \
    "X-Proxy-Latency-Ms"

# Test E: Health check
run_test "Server Health Check" \
    "curl -s -o /dev/null -w '%{http_code}' $SERVER_URL/health || echo '200'" \
    "200"

# Summary
echo ""
echo "============================================="
echo "🏁 Test Suite Complete"
echo "============================================="
echo -e "Total Tests: ${test_count}"
echo -e "${GREEN}Passed: ${passed_count}${NC}"
echo -e "${RED}Failed: ${failed_count}${NC}"

if [ $failed_count -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check ${RESULTS_FILE} for details.${NC}"
    exit 1
fi