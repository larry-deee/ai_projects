#!/bin/bash
# Production-ready Salesforce LLM Endpoint Service Startup Script
# Usage: 
#   Development: ./start_llm_service.sh
#   Production: ENVIRONMENT=production ./start_llm_service.sh

set -e  # Exit on any error

# Configuration
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
SERVICE_NAME="salesforce-llm-gateway"
ENVIRONMENT=${ENVIRONMENT:-development}

# Load environment variables from .env file if it exists
ENV_FILE="../.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Loading environment variables from $ENV_FILE..."
    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        value=$(echo "$value" | sed 's/[[:space:]]*#.*//')
        if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
            export "$key"="$value"
        fi
    done < "$ENV_FILE"
elif [ -f .env ]; then
    echo "📄 Loading environment variables from .env..."
    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue
        value=$(echo "$value" | sed 's/[[:space:]]*#.*//')
        if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
            export "$key"="$value"
        fi
    done < .env
fi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Pre-flight checks
check_dependencies() {
    echo "🔍 Checking dependencies..."
    
    # Change to project root directory
    cd "$(dirname "$0")"/.. 
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        log_error "Requirements file not found: $REQUIREMENTS_FILE"
        exit 1
    fi
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_info "Python version: $python_version"
    
    # Check if gunicorn is available
    if ! command -v gunicorn &> /dev/null; then
        log_warning "gunicorn not found, will install from requirements"
        return 1
    fi
    
    return 0
}

# Virtual environment setup
setup_virtualenv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "📦 Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    echo "🔄 Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    echo "📦 Installing/upgrading dependencies..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
}

# Configuration validation
validate_config() {
    echo "🔐 Validating configuration..."
    
    # Check configuration exists (prioritize secure location)
    if [ ! -f ".secure/config.json" ] && [ ! -f "config.json" ] && [ -z "$SALESFORCE_CONSUMER_KEY" ]; then
        log_error "Configuration not found!"
        echo ""
        echo "Please either:"
        echo "1. Create config.json with your Salesforce credentials, OR"
        echo "2. Set environment variables:"
        echo "   export SALESFORCE_CONSUMER_KEY='your_key'"
        echo "   export SALESFORCE_CONSUMER_SECRET='your_secret'"
        echo "   export SALESFORCE_INSTANCE_URL='your_instance_url'"
        echo ""
        exit 1
    fi
    
    # Test configuration loading
    echo "🧪 Testing configuration..."
    python3 -c "
import sys
sys.path.insert(0, './src')
try:
    from salesforce_models_client import SalesforceModelsClient
    import os
    config_file = '.secure/config.json' if os.path.exists('.secure/config.json') else 'config.json'
    client = SalesforceModelsClient(config_file=config_file)
    client._validate_config()
    print('✅ Configuration validated successfully')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
" || {
        log_error "Configuration validation failed"
        exit 1
    }
    
    log_info "Configuration validated"
}

# Setup production directories
setup_production_dirs() {
    if [ "$ENVIRONMENT" == "production" ]; then
        echo "📁 Setting up production directories..."
        
        # Create log and pid directories
        sudo mkdir -p /var/log/salesforce-llm-gateway
        sudo mkdir -p /var/run/salesforce-llm-gateway
        
        # Set proper permissions
        sudo chown -R www-data:www-data /var/log/salesforce-llm-gateway
        sudo chown -R www-data:www-data /var/run/salesforce-llm-gateway
        
        log_info "Production directories setup complete"
    fi
}

# Service startup
start_service() {
    echo "🚀 Starting $SERVICE_NAME in $ENVIRONMENT mode..."
    
    # Activate virtual environment
    if [ -d "$VENV_DIR" ]; then
        source "$VENV_DIR/bin/activate"
    fi
    
    # Build gunicorn command based on environment
    GUNICORN_CMD="gunicorn --config ../gunicorn_config.py"
    
    # Add environment-specific options
    if [ "$ENVIRONMENT" == "production" ]; then
        GUNICORN_CMD="$GUNICORN_CMD --daemon"
        echo "📊 Production mode: daemon process with logging"
    else
        echo "🔧 Development mode: foreground process"
    fi
    
    # Start the service
    echo "🌐 Starting server on http://localhost:8000"
    echo "🛑 Press Ctrl+C to stop the server"
    echo ""
    
    if [ "$ENVIRONMENT" == "production" ]; then
        # Production: start as daemon
        cd src && $GUNICORN_CMD llm_endpoint_server:app
        
        # Check if service started successfully
        sleep 2
        if [ -f "/var/run/salesforce-llm-gateway/pid" ]; then
            PID=$(cat /var/run/salesforce-llm-gateway/pid)
            log_info "Service started successfully (PID: $PID)"
            echo "📊 Service logs: /var/log/salesforce-llm-gateway/"
            echo "📍 Process ID: $PID"
        else
            log_error "Service failed to start"
            exit 1
        fi
    else
        # Development: start in foreground
        cd src && exec $GUNICORN_CMD llm_endpoint_server:app
    fi
}

# Stop service (for production)
stop_service() {
    if [ "$ENVIRONMENT" == "production" ] && [ -f "/var/run/salesforce-llm-gateway/pid" ]; then
        echo "🛑 Stopping service..."
        PID=$(cat /var/run/salesforce-llm-gateway/pid)
        kill $PID
        rm -f /var/run/salesforce-llm-gateway/pid
        log_info "Service stopped"
    else
        log_warning "No running service found or not in production mode"
    fi
}

# Show service status
show_status() {
    if [ "$ENVIRONMENT" == "production" ] && [ -f "/var/run/salesforce-llm-gateway/pid" ]; then
        PID=$(cat /var/run/salesforce-llm-gateway/pid)
        if ps -p $PID > /dev/null; then
            log_info "Service is running (PID: $PID)"
            echo "🌐 Service endpoint: http://localhost:8000"
        else
            log_error "Service is not running (stale PID file)"
        fi
    else
        log_warning "Service status not available or not in production mode"
    fi
}

# Main execution
main() {
    echo "🚀 Starting Salesforce LLM Endpoint Service - $ENVIRONMENT Mode"
    echo "================================================================="
    
    # Parse command line arguments
    case "${1:-start}" in
        start)
            check_dependencies || setup_virtualenv
            setup_production_dirs
            validate_config
            start_service
            ;;
        stop)
            stop_service
            ;;
        status)
            show_status
            ;;
        restart)
            stop_service
            sleep 2
            main start
            ;;
        *)
            echo "Usage: $0 {start|stop|status|restart}"
            echo "  Environment variables:"
            echo "    ENVIRONMENT=development|production"
            exit 1
            ;;
    esac
}

# Handle signals gracefully
trap 'echo ""; log_warning "Received interrupt signal, shutting down..."; stop_service; exit 0' INT TERM

# Execute main function with all arguments
main "$@"