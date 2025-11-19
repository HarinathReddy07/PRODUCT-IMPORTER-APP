"""
Celery application configuration for async task processing.
"""
from celery import Celery
from config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Create Celery instance
celery_app = Celery(
    "product_importer",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

