"""Gunicorn configuration for GV POWERS corporate website.

Usage on the Ubuntu server:
    gunicorn -c gunicorn.conf.py app:app
"""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", max(2, multiprocessing.cpu_count() * 2 + 1)))
worker_class = "sync"
timeout = 60
keepalive = 5

# Logging
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "/var/log/gvpowers/access.log")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "/var/log/gvpowers/error.log")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Process safety
max_requests = 1200
max_requests_jitter = 100

# Security & reliability
forwarded_allow_ips = "127.0.0.1"
proxy_allow_ips = "127.0.0.1"
