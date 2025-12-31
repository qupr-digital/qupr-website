bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
keepalive = 5
timeout = 30
graceful_timeout = 30

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# Process naming
proc_name = "quprdigital"

# Server mechanics
daemon = False
pidfile = "gunicorn.pid"
