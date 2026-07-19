"""
gunicorn.conf.py
----------------
Production Gunicorn configuration.

Start with:
    gunicorn -c gunicorn.conf.py wsgi:app
"""

import multiprocessing
import os

# ── Binding ───────────────────────────────────────────────────────────────────
host  = os.environ.get("HOST", "0.0.0.0")
port  = os.environ.get("PORT", "8000")
bind  = f"{host}:{port}"

# ── Workers ───────────────────────────────────────────────────────────────────
# For video streaming, fewer workers with longer timeouts is better.
workers     = int(os.environ.get("WEB_CONCURRENCY", max(2, multiprocessing.cpu_count())))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "sync")  # or "gevent"
threads     = int(os.environ.get("GUNICORN_THREADS", 2))

# ── Timeouts ──────────────────────────────────────────────────────────────────
# Video downloads can take a long time — use a generous timeout.
timeout      = int(os.environ.get("GUNICORN_TIMEOUT", 300))   # 5 minutes
keepalive    = int(os.environ.get("GUNICORN_KEEPALIVE", 5))
graceful_timeout = 30

# ── Logging ───────────────────────────────────────────────────────────────────
loglevel     = os.environ.get("LOG_LEVEL", "info").lower()
accesslog    = "-"    # stdout
errorlog     = "-"    # stderr
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s '
    '"%(f)s" "%(a)s" %(D)sµs'
)

# ── Process naming ────────────────────────────────────────────────────────────
proc_name    = "social-video-downloader"

# ── Security ──────────────────────────────────────────────────────────────────
limit_request_line   = 4094
limit_request_fields = 100
