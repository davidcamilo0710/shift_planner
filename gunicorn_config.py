#!/usr/bin/env python3
"""
Gunicorn configuration for DigitalOcean App Platform deployment.
Optimized for shift processing workloads with long-running tasks.
"""

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Cap at 4 workers for memory efficiency
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings - important for long-running optimization tasks
timeout = 300  # 5 minutes for processing large files
keepalive = 5
graceful_timeout = 30

# Logging
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'planificador-turnos-api'

# Application
module_name = "api:app"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Memory management
preload_app = True
max_requests_jitter = 100

# Worker process lifecycle
def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Planificador de Turnos API is ready to serve requests")

def worker_int(worker):
    """Called when a worker receives the SIGINT or SIGQUIT signal."""
    worker.log.info("Worker received INT or QUIT signal, shutting down gracefully")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker {worker.pid} is about to be forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} has been forked")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} received SIGABRT signal")

# SSL (not used for App Platform, but kept for completeness)
keyfile = None
certfile = None