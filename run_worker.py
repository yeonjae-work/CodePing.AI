#!/usr/bin/env python3
"""Direct Celery worker runner script."""

import os
import sys

# Set environment variables
os.environ['CELERY_ALWAYS_EAGER'] = 'false'

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from shared.config.celery_app import celery_app

if __name__ == "__main__":
    # Run worker directly
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--queues=celery,webhook_queue,webhook'
    ]) 