# Production-ready gunicorn configuration
import multiprocessing
import os

# Environment-specific settings
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    # Production optimizations for sync Flask app
    workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
    worker_class = "sync" # ✅ WSGI support for Flask app
    timeout = 1200 # Increased to 20 minutes for token refresh safety
    max_requests = 1000 # Prevent memory leaks
    max_requests_jitter = 100 # Stagger restarts
    preload_app = True # Load app before forking
    
    # Security settings
    limit_request_line = 4096
    limit_request_fields = 100
    limit_request_field_size = 8190
    
    # Logging
    accesslog = "/var/log/salesforce-llm-gateway/access.log"
    errorlog = "/var/log/salesforce-llm-gateway/error.log"
    loglevel = "info"
    
else:
    # Development settings
    workers = 2
    worker_class = "sync" # Keep sync for development simplicity
    timeout = 600 # Increased to 10 minutes to accommodate long-running Salesforce requests
    max_requests = 0
    preload_app = False
    
    # Logging
    accesslog = "-"
    errorlog = "-"
    loglevel = "debug"

# Common settings
bind = "0.0.0.0:8000"
worker_connections = 2000  # Increased for better concurrency
keepalive = 30  # Extended for long-running requests

# Process management (only in production)
if ENVIRONMENT == 'production':
    pidfile = "/var/run/salesforce-llm-gateway/pid"
    user = "www-data"
    group = "www-data"

# Minimal startup hook - initialization now handled in app code
def when_ready(server):
    """Minimal startup initialization."""
    server.log.info("Server ready for requests")
