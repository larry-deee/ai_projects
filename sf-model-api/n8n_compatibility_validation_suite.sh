#!/bin/bash
# n8n Compatibility Mode Validation Suite
# ========================================
# 
# Comprehensive QA testing for n8n-compatible mode implementation.
# Tests all specified requirements from the master task with proper assertions.

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
SERVER_URL="http://127.0.0.1:8000"
TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0
TIMEOUT=30

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS_COUNT++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL_COUNT++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test execution function
run_test() {
    local test_name="$1"
    local test_description="$2"
    local curl_cmd="$3"
    local expected_result="$4"
    
    ((TEST_COUNT++))
    log_info "Test $TEST_COUNT: $test_name"
    log_info "Description: $test_description"
    
    echo "Executing: $curl_cmd" | head -c 100
    echo "..."
    
    # Execute the curl command and capture response
    local response
    local http_status
    local headers_file=$(mktemp)
    
    if response=$(eval "$curl_cmd" -D "$headers_file" 2>/dev/null); then
        http_status=$(grep "^HTTP" "$headers_file" | tail -1 | awk '{print $2}' || echo "000")
        
        # Validate the response
        if validate_response "$response" "$headers_file" "$expected_result" "$http_status"; then
            log_success "$test_name - PASSED"
        else
            log_error "$test_name - FAILED"
            echo "Response preview: $(echo "$response" | head -c 200)..."
        fi
    else
        log_error "$test_name - FAILED (curl error)"
    fi
    
    rm -f "$headers_file"
    echo ""
}

# Response validation function
validate_response() {
    local response="$1"
    local headers_file="$2"
    local expected="$3"
    local http_status="$4"
    
    case "$expected" in
        "plain_chat_non_null_content")
            # Check that content is not null and no tool_calls
            if echo "$response" | jq -e '.choices[0].message.content != null' >/dev/null 2>&1; then
                if echo "$response" | jq -e '.choices[0].message | has("tool_calls") | not' >/dev/null 2>&1; then
                    return 0
                else
                    log_error "Response contains tool_calls when it shouldn't"
                fi
            else
                log_error "Response content is null"
            fi
            return 1
            ;;
        "n8n_compat_headers_200")
            # Check for 200 status, no tool_calls, and required headers
            if [[ "$http_status" == "200" ]]; then
                if echo "$response" | jq -e '.choices[0].message | has("tool_calls") | not' >/dev/null 2>&1; then
                    # Check for diagnostic headers
                    if grep -q "x-stream-downgraded: true" "$headers_file" && grep -q "x-proxy-latency-ms:" "$headers_file"; then
                        return 0
                    else
                        log_error "Missing required diagnostic headers"
                    fi
                else
                    log_error "Response contains tool_calls in n8n compatibility mode"
                fi
            else
                log_error "Expected 200 status but got $http_status"
            fi
            return 1
            ;;
        "plain_chat_no_tools")
            # Check that content is not null and no tool_calls (for invalid tools)
            if echo "$response" | jq -e '.choices[0].message.content != null' >/dev/null 2>&1; then
                if echo "$response" | jq -e '.choices[0].message | has("tool_calls") | not' >/dev/null 2>&1; then
                    return 0
                else
                    log_error "Response contains tool_calls for invalid tools"
                fi
            else
                log_error "Response content is null for invalid tools test"
            fi
            return 1
            ;;
        "valid_json_structure")
            # Basic JSON structure validation
            if echo "$response" | jq -e '.choices and .object and .usage' >/dev/null 2>&1; then
                return 0
            else
                log_error "Response missing required JSON fields"
            fi
            return 1
            ;;
    esac
    
    return 1
}

# Header validation function  
validate_headers() {
    local headers_file="$1"
    local test_name="$2"
    
    log_info "Validating headers for $test_name"
    
    # Required headers check
    local required_headers=(
        "Content-Type"
        "x-proxy-latency-ms"
    )
    
    local missing_headers=0
    for header in "${required_headers[@]}"; do
        if ! grep -qi "^$header:" "$headers_file"; then
            log_error "Missing header: $header"
            ((missing_headers++))
        fi
    done
    
    # Check specific header values
    if grep -q "Content-Type: application/json" "$headers_file"; then
        log_success "Content-Type header correct"
    else
        log_error "Content-Type header incorrect or missing"
        ((missing_headers++))
    fi
    
    # Check x-proxy-latency-ms format (should be integer)
    local latency_header=$(grep -i "x-proxy-latency-ms:" "$headers_file" | head -1 | cut -d: -f2 | tr -d ' ')
    if [[ "$latency_header" =~ ^[0-9]+$ ]]; then
        log_success "x-proxy-latency-ms header format correct: ${latency_header}ms"
    else
        log_error "x-proxy-latency-ms header format incorrect: '$latency_header'"
        ((missing_headers++))
    fi
    
    return $missing_headers
}

# Environment variable tests
test_environment_variables() {
    log_info "Testing environment variable behavior"
    
    # Test with N8N_COMPAT_MODE=0 (disabled)
    log_info "Testing N8N_COMPAT_MODE=0 (should allow tools for n8n user-agent)"
    
    # This test requires restarting the server with different env vars
    # For now, we'll test the current default behavior
    
    log_info "Current test assumes N8N_COMPAT_MODE=1 (default enabled)"
}

# Edge case tests
test_edge_cases() {
    log_info "Running edge case tests..."
    
    # Test empty tools array
    log_info "Testing empty tools array"
    local empty_tools_response
    empty_tools_response=$(curl -s -X POST "$SERVER_URL/v1/chat/completions" \
        -H 'Content-Type: application/json' \
        -d '{
            "model": "claude-4-sonnet",
            "messages": [{"role": "user", "content": "Test with empty tools"}],
            "tools": [],
            "tool_choice": "auto"
        }')
    
    if echo "$empty_tools_response" | jq -e '.choices[0].message.content != null' >/dev/null 2>&1; then
        log_success "Empty tools array handled correctly"
    else
        log_error "Empty tools array not handled correctly"
    fi
    
    # Test malformed tools
    log_info "Testing malformed tools (should fall back to plain chat)"
    local malformed_response
    malformed_response=$(curl -s -X POST "$SERVER_URL/v1/chat/completions" \
        -H 'Content-Type: application/json' \
        -d '{
            "model": "claude-4-sonnet", 
            "messages": [{"role": "user", "content": "Test with malformed tools"}],
            "tools": [{"invalid": "structure"}],
            "tool_choice": "auto"
        }')
    
    if echo "$malformed_response" | jq -e '.choices[0].message.content != null' >/dev/null 2>&1; then
        log_success "Malformed tools handled with fallback to plain chat"
    else
        log_error "Malformed tools not handled correctly"
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "n8n Compatibility Mode Validation Suite"
    echo "=========================================="
    echo ""
    
    log_info "Starting comprehensive QA validation"
    log_info "Server URL: $SERVER_URL"
    
    # Test 1: Plain chat (no tools) - Master Task Requirement
    run_test "Plain Chat No Tools" \
        "Verify content is non-empty string (not null) and no tool_calls field" \
        "curl -s -X POST '$SERVER_URL/v1/chat/completions' -H 'Content-Type: application/json' -d '{\"model\":\"claude-4-sonnet\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi\"}],\"tool_choice\":\"none\"}'" \
        "plain_chat_non_null_content"
    
    # Test 2: n8n-compat (fake tools, n8n User-Agent) - Master Task Requirement  
    run_test "n8n Compatibility Mode" \
        "n8n user-agent with fake tools should return 200, no tool_calls, with diagnostic headers" \
        "curl -s -X POST '$SERVER_URL/v1/chat/completions' -H 'Content-Type: application/json' -H 'User-Agent: n8n/1.105.4' -d '{\"model\":\"claude-4-sonnet\",\"messages\":[{\"role\":\"user\",\"content\":\"Test\"}],\"tools\":[{\"type\":\"function\",\"function\":{\"name\":\"fake\",\"parameters\":{\"type\":\"object\"}}}],\"tool_choice\":\"auto\",\"stream\":true}'" \
        "n8n_compat_headers_200"
    
    # Test 3: Invalid tools (non-n8n) - Master Task Requirement
    run_test "Invalid Tools Non-n8n" \
        "Invalid tools with non-n8n user-agent should fall back to plain chat" \
        "curl -s -X POST '$SERVER_URL/v1/chat/completions' -H 'Content-Type: application/json' -d '{\"model\":\"claude-4-sonnet\",\"messages\":[{\"role\":\"user\",\"content\":\"Test\"}],\"tools\":[{\"type\":\"function\",\"function\":{}}],\"tool_choice\":\"auto\"}'" \
        "plain_chat_no_tools"
    
    # Test 4: Streaming downgrade test
    log_info "Test 4: Streaming Downgrade Validation"
    ((TEST_COUNT++))
    local streaming_test_headers=$(mktemp)
    local streaming_response
    
    streaming_response=$(curl -s -i -X POST "$SERVER_URL/v1/chat/completions" \
        -H 'Content-Type: application/json' \
        -H 'User-Agent: n8n/1.105.4' \
        -d '{
            "model": "claude-4-sonnet",
            "messages": [{"role": "user", "content": "Test streaming"}],
            "tools": [{"type": "function", "function": {"name": "test", "parameters": {"type": "object"}}}],
            "tool_choice": "auto",
            "stream": true
        }' > "$streaming_test_headers")
    
    if grep -q "x-stream-downgraded: true" "$streaming_test_headers"; then
        log_success "Streaming downgrade header present for n8n request"
        ((PASS_COUNT++))
    else
        log_error "Streaming downgrade header missing"
        ((FAIL_COUNT++))
    fi
    rm -f "$streaming_test_headers"
    
    # Test 5: Header validation across all responses
    log_info "Test 5: Comprehensive Header Validation"
    ((TEST_COUNT++))
    local header_test_file=$(mktemp)
    curl -s -i -X POST "$SERVER_URL/v1/chat/completions" \
        -H 'Content-Type: application/json' \
        -d '{
            "model": "claude-4-sonnet",
            "messages": [{"role": "user", "content": "Header test"}]
        }' > "$header_test_file"
    
    if validate_headers "$header_test_file" "Standard Request"; then
        log_success "Header validation passed"
        ((PASS_COUNT++))
    else
        log_error "Header validation failed" 
        ((FAIL_COUNT++))
    fi
    rm -f "$header_test_file"
    
    # Test 6: Content null protection
    log_info "Test 6: Content Null Protection"
    ((TEST_COUNT++))
    local content_test_response
    content_test_response=$(curl -s -X POST "$SERVER_URL/v1/chat/completions" \
        -H 'Content-Type: application/json' \
        -d '{
            "model": "claude-4-sonnet",
            "messages": [{"role": "user", "content": ""}],
            "tool_choice": "none"
        }')
    
    local content_value
    content_value=$(echo "$content_test_response" | jq -r '.choices[0].message.content')
    
    if [[ "$content_value" != "null" ]]; then
        log_success "Content is never null (value: '$content_value')"
        ((PASS_COUNT++))
    else
        log_error "Content is null when it shouldn't be"
        ((FAIL_COUNT++))
    fi
    
    # Edge case tests
    test_edge_cases
    
    # Final validation report
    echo ""
    echo "=========================================="
    echo "FINAL VALIDATION REPORT"
    echo "=========================================="
    echo "Total Tests: $TEST_COUNT"
    echo "Passed: $PASS_COUNT"
    echo "Failed: $FAIL_COUNT"
    
    if [[ $FAIL_COUNT -eq 0 ]]; then
        log_success "ALL TESTS PASSED - n8n compatibility mode is working correctly!"
        echo ""
        echo "✅ Master Task Requirements Validation:"
        echo "   1. Plain chat returns non-null content ✅"
        echo "   2. n8n-compat mode works with diagnostic headers ✅" 
        echo "   3. Invalid tools fall back to plain chat ✅"
        echo "   4. Headers are properly formatted ✅"
        echo "   5. Content is never null ✅"
        echo "   6. Streaming downgrade works ✅"
        exit 0
    else
        log_error "SOME TESTS FAILED - n8n compatibility needs fixes"
        echo ""
        echo "❌ Issues found:"
        echo "   - $FAIL_COUNT out of $TEST_COUNT tests failed"
        echo "   - Review server logs and responses above"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    # Remove any temporary files
    rm -f /tmp/n8n_test_* 2>/dev/null || true
}

# Set trap for cleanup
trap cleanup EXIT

# Run the main test suite
main "$@"