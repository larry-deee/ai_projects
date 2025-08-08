#!/bin/bash
"""
Compatibility Test Execution Script
===================================

Automated script for running n8n and Claude Code compatibility tests
against the Salesforce Models API Gateway. Handles server startup,
test execution, and result reporting.

Usage:
    ./run_compatibility_tests.sh [OPTIONS]
    
Options:
    --integration     Enable integration tests (requires running server)
    --performance     Enable performance regression tests  
    --server-url URL  Specify server URL (default: http://localhost:8000)
    --timeout SEC     Test timeout in seconds (default: 300)
    --verbose         Enable verbose output
    --report FILE     Save JSON report to file
    --help            Show this help message
"""

set -e  # Exit on error

# Default configuration
DEFAULT_SERVER_URL="http://localhost:8000"
DEFAULT_TIMEOUT=300
INTEGRATION_TESTS=false
PERFORMANCE_TESTS=false
VERBOSE=false
SERVER_URL=""
TIMEOUT=""
REPORT_FILE=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." &> /dev/null && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${PURPLE}[DEBUG]${NC} $1"
    fi
}

# Show help message
show_help() {
    cat << EOF
🧪 Salesforce Models API Gateway - Compatibility Test Runner

USAGE:
    ./run_compatibility_tests.sh [OPTIONS]

OPTIONS:
    --integration         Enable integration tests (requires running server)
    --performance         Enable performance regression tests
    --server-url URL      Specify server URL (default: $DEFAULT_SERVER_URL)
    --timeout SEC         Test timeout in seconds (default: $DEFAULT_TIMEOUT)
    --verbose             Enable verbose output and debugging
    --report FILE         Save detailed JSON report to specified file
    --help                Show this help message

EXAMPLES:
    # Run basic compatibility tests
    ./run_compatibility_tests.sh

    # Run all tests including integration and performance
    ./run_compatibility_tests.sh --integration --performance --verbose

    # Run against custom server with report
    ./run_compatibility_tests.sh --server-url http://localhost:9000 --report test_results.json

ENVIRONMENT VARIABLES:
    INTEGRATION_TESTS     Set to 'true' to enable integration tests
    PERFORMANCE_TESTS     Set to 'true' to enable performance tests
    SF_RESPONSE_DEBUG     Set to 'true' to enable response debugging

TEST CATEGORIES:
    📋 API Specification Compliance Tests
    🧪 n8n Client Compatibility Tests
    🤖 Claude Code Client Compatibility Tests
    ⚡ Performance Regression Tests (optional)

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --integration)
                INTEGRATION_TESTS=true
                shift
                ;;
            --performance)
                PERFORMANCE_TESTS=true
                shift
                ;;
            --server-url)
                SERVER_URL="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --report)
                REPORT_FILE="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Set defaults if not provided
    if [ -z "$SERVER_URL" ]; then
        SERVER_URL="$DEFAULT_SERVER_URL"
    fi
    if [ -z "$TIMEOUT" ]; then
        TIMEOUT="$DEFAULT_TIMEOUT"
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python installation
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_debug "Python version: $PYTHON_VERSION"
    
    # Check if we're in the correct directory
    if [ ! -f "$SCRIPT_DIR/test_master_suite.py" ]; then
        log_error "Test files not found. Make sure you're running from the tests directory"
        exit 1
    fi
    
    # Check for required Python packages
    log_debug "Checking Python package requirements..."
    if ! python3 -c "import requests, unittest" &> /dev/null; then
        log_warning "Some Python packages may be missing. Installing requirements..."
        if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
            pip3 install -r "$SCRIPT_DIR/requirements.txt" || {
                log_error "Failed to install Python requirements"
                exit 1
            }
        fi
    fi
    
    log_success "System requirements check passed"
}

# Check server availability
check_server_availability() {
    local server_url="$1"
    log_info "Checking server availability at $server_url..."
    
    # Try to connect to the server
    if command -v curl &> /dev/null; then
        if curl -s --connect-timeout 5 "$server_url/health" > /dev/null; then
            log_success "Server is responding at $server_url"
            return 0
        fi
    elif command -v wget &> /dev/null; then
        if wget --spider --timeout=5 "$server_url/health" &> /dev/null; then
            log_success "Server is responding at $server_url"
            return 0
        fi
    else
        # Use Python as fallback
        if python3 -c "
import requests
import sys
try:
    response = requests.get('$server_url/health', timeout=5)
    sys.exit(0 if response.status_code == 200 else 1)
except:
    sys.exit(1)
" 2>/dev/null; then
            log_success "Server is responding at $server_url"
            return 0
        fi
    fi
    
    log_warning "Server is not responding at $server_url"
    return 1
}

# Start local server if needed
start_local_server() {
    log_info "Starting local async server..."
    
    # Check if server is already running
    if check_server_availability "$SERVER_URL"; then
        log_success "Server already running at $SERVER_URL"
        return 0
    fi
    
    # Start the async server
    cd "$PROJECT_ROOT"
    
    if [ -f "src/async_endpoint_server.py" ]; then
        log_debug "Starting async server from src/async_endpoint_server.py"
        python3 src/async_endpoint_server.py &
        SERVER_PID=$!
        
        # Wait for server to start
        log_info "Waiting for server to start..."
        for i in {1..30}; do
            if check_server_availability "$SERVER_URL"; then
                log_success "Server started successfully (PID: $SERVER_PID)"
                return 0
            fi
            sleep 1
        done
        
        log_error "Server failed to start within 30 seconds"
        kill $SERVER_PID 2>/dev/null || true
        return 1
        
    elif [ -f "start_async_service.sh" ] && [ -x "start_async_service.sh" ]; then
        log_debug "Starting server using start_async_service.sh"
        ./start_async_service.sh &
        SERVER_PID=$!
        
        # Wait for server to start
        log_info "Waiting for server to start..."
        for i in {1..30}; do
            if check_server_availability "$SERVER_URL"; then
                log_success "Server started successfully"
                return 0
            fi
            sleep 1
        done
        
        log_error "Server failed to start within 30 seconds"
        return 1
    else
        log_error "No server startup script found"
        return 1
    fi
}

# Set environment variables for testing
setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Set test configuration
    export PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT/tests:$PYTHONPATH"
    
    if [ "$INTEGRATION_TESTS" = true ]; then
        export INTEGRATION_TESTS=true
        log_debug "Integration tests enabled"
    else
        export INTEGRATION_TESTS=false
        log_debug "Integration tests disabled"
    fi
    
    if [ "$PERFORMANCE_TESTS" = true ]; then
        export PERFORMANCE_TESTS=true
        log_debug "Performance tests enabled"
    else
        export PERFORMANCE_TESTS=false
        log_debug "Performance tests disabled"
    fi
    
    if [ "$VERBOSE" = true ]; then
        export SF_RESPONSE_DEBUG=true
        log_debug "Response debugging enabled"
    fi
    
    log_success "Test environment configured"
}

# Run the master test suite
run_master_test_suite() {
    log_info "Running master test suite..."
    
    cd "$SCRIPT_DIR"
    
    # Build command arguments
    local args=(
        "--server-url" "$SERVER_URL"
    )
    
    if [ "$INTEGRATION_TESTS" = true ]; then
        args+=("--integration")
    fi
    
    if [ "$PERFORMANCE_TESTS" = true ]; then
        args+=("--performance")
    fi
    
    if [ "$VERBOSE" = false ]; then
        args+=("--quiet")
    fi
    
    if [ -n "$REPORT_FILE" ]; then
        args+=("--save-report" "$REPORT_FILE")
    fi
    
    # Run the master test suite
    log_debug "Executing: python3 test_master_suite.py ${args[*]}"
    
    if python3 test_master_suite.py "${args[@]}"; then
        log_success "Master test suite completed successfully"
        return 0
    else
        log_error "Master test suite failed"
        return 1
    fi
}

# Run individual test suites for debugging
run_individual_suites() {
    log_info "Running individual test suites for detailed analysis..."
    
    cd "$SCRIPT_DIR"
    local overall_success=true
    
    # API Compliance Tests
    log_info "Running API Compliance Tests..."
    if python3 test_api_compliance.py; then
        log_success "API Compliance Tests: PASSED"
    else
        log_error "API Compliance Tests: FAILED"
        overall_success=false
    fi
    
    # n8n Compatibility Tests
    log_info "Running n8n Compatibility Tests..."
    if python3 test_n8n_compatibility.py; then
        log_success "n8n Compatibility Tests: PASSED"
    else
        log_error "n8n Compatibility Tests: FAILED"
        overall_success=false
    fi
    
    # Claude Code Compatibility Tests
    log_info "Running Claude Code Compatibility Tests..."
    if python3 test_claude_code_compatibility.py; then
        log_success "Claude Code Compatibility Tests: PASSED"
    else
        log_error "Claude Code Compatibility Tests: FAILED"
        overall_success=false
    fi
    
    # Performance Tests (if enabled)
    if [ "$PERFORMANCE_TESTS" = true ]; then
        log_info "Running Performance Regression Tests..."
        if python3 test_performance_regression.py; then
            log_success "Performance Regression Tests: PASSED"
        else
            log_error "Performance Regression Tests: FAILED"
            overall_success=false
        fi
    fi
    
    return $([ "$overall_success" = true ] && echo 0 || echo 1)
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    
    # Kill server if we started it
    if [ -n "$SERVER_PID" ]; then
        log_debug "Stopping server (PID: $SERVER_PID)"
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    
    # Clean up temporary files
    find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true
    find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
}

# Main execution function
main() {
    echo -e "${CYAN}"
    echo "🧪 Salesforce Models API Gateway"
    echo "   Compatibility Test Runner"
    echo "==============================="
    echo -e "${NC}"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Setup cleanup trap
    trap cleanup EXIT
    
    # Check system requirements
    check_requirements
    
    # Setup test environment
    setup_test_environment
    
    # Handle server availability
    local server_started=false
    if [ "$INTEGRATION_TESTS" = true ]; then
        if ! check_server_availability "$SERVER_URL"; then
            log_warning "Integration tests enabled but server not available"
            log_info "Attempting to start local server..."
            
            if start_local_server; then
                server_started=true
            else
                log_error "Failed to start server. Disabling integration tests."
                export INTEGRATION_TESTS=false
            fi
        fi
    fi
    
    # Run the test suite
    log_info "Starting compatibility test execution..."
    log_info "Configuration:"
    log_info "  Server URL: $SERVER_URL"
    log_info "  Integration Tests: $INTEGRATION_TESTS"
    log_info "  Performance Tests: $PERFORMANCE_TESTS"
    log_info "  Timeout: ${TIMEOUT}s"
    
    local start_time=$(date +%s)
    local success=true
    
    # Run master test suite
    if ! run_master_test_suite; then
        success=false
        
        # If master suite failed, try individual suites for better debugging
        if [ "$VERBOSE" = true ]; then
            log_warning "Master suite failed. Running individual suites for debugging..."
            run_individual_suites
        fi
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Print final results
    echo -e "\\n${CYAN}===============================${NC}"
    if [ "$success" = true ]; then
        echo -e "${GREEN}✅ COMPATIBILITY TESTS PASSED${NC}"
        echo -e "${GREEN}   System ready for deployment${NC}"
    else
        echo -e "${RED}❌ COMPATIBILITY TESTS FAILED${NC}"
        echo -e "${RED}   Issues must be resolved${NC}"
    fi
    echo -e "${CYAN}===============================${NC}"
    echo -e "Execution time: ${duration}s"
    
    if [ -n "$REPORT_FILE" ]; then
        echo -e "Report saved to: $REPORT_FILE"
    fi
    
    # Return appropriate exit code
    exit $([ "$success" = true ] && echo 0 || echo 1)
}

# Execute main function with all arguments
main "$@"