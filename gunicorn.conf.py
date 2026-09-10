# Keep full-document extraction and bounded provider work within one worker.
timeout = 1200
graceful_timeout = 120
# Every open event stream holds one request thread for its whole (bounded)
# lifetime, so the pool must outlast several concurrent viewers or Render's
# health check fails and restarts the instance mid-review. The work is
# I/O-bound, so idle gthread threads are cheap.
worker_class = "gthread"
threads = 16
