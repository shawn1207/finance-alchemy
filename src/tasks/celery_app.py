"""Celery application setup."""

from celery import Celery
from src.config import get_settings

# Get settings singleton
settings = get_settings()

# Create Celery instance
celery_app = Celery(
    "finance_alchemy_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.tasks.analysis_tasks"],  # Path to the module where tasks are defined
)

# Celery configuration
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,  # Store results for 1 hour
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Shanghai',
    enable_utc=True,
)

if __name__ == "__main__":
    celery_app.start()
