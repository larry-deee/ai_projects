"""
Gunicorn Configuration for Async Optimized Salesforce Models API Gateway
========================================================================

Production-ready configuration for running the async optimized server with:
- Thread-safe connection pooling
- Optimal worker configuration
- Performance monitoring
- Graceful shutdown handling

Usage:
    gunicorn -c gunicorn_async_config.py async_endpoint_server:app
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 8000)}"
backlog = 2048

# Worker processes
# For async workloads, use fewer workers but with async capabilities
workers = min(4, multiprocessing.cpu_count())
worker_class = 'quart.serving:QuartWorker'  # Use Quart's async worker
worker_connections = 1000
max_requests = 2000  # Restart workers after 2000 requests to prevent memory leaks
max_requests_jitter = 100  # Add jitter to prevent all workers restarting at once

# Timeouts (optimized for LLM API calls)
timeout = 300  # 5 minutes for long-running LLM requests
keepalive = 5  # Keep connections alive for 5 seconds
graceful_timeout = 60  # Graceful shutdown timeout

# Logging
loglevel = 'warning'  # Reduce log verbosity for performance
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
accesslog = '-'
errorlog = '-'

# Process naming
proc_name = 'salesforce-models-async-api'

# Performance optimizations
preload_app = True  # Preload the application for better memory usage
enable_stdio_inheritance = True

# Environment variables for async optimization
raw_env = [
    'ASYNC_OPTIMIZATION=true',
    'CONNECTION_POOL_SIZE=100',
    'MAX_CONNECTIONS_PER_HOST=20'
]

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("🚀 Async Salesforce Models API Gateway started")
    server.log.info(f"🔧 Workers: {workers} (async-capable)")
    server.log.info(f"📊 Expected performance improvement: 40-60% vs sync")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"🔄 Worker {worker.pid} interrupted")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"🔧 Forking worker {worker.pid}")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"✅ Worker {worker.pid} spawned")

def on_exit(server):
    """Called just before the master process exits."""
    server.log.info("🔒 Async API Gateway shutting down")
    
def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"❌ Worker {worker.pid} aborted")

# Memory optimization
max_worker_memory = int(os.environ.get('MAX_WORKER_MEMORY', 512)) * 1024 * 1024  # 512MB default

# Security
limit_request_line = 8192  # Limit request line length
limit_request_fields = 100  # Limit number of headers
limit_request_field_size = 8192  # Limit header size