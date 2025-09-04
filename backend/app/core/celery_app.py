"""
Celery configuration for background tasks
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "hackops",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_tasks",
        "app.workers.analytics_tasks",
        "app.workers.submission_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_reject_on_worker_lost=True,
    worker_disable_rate_limits=True,
    result_expires=3600,  # Results expire after 1 hour
)

# Task routing
celery_app.conf.task_routes = {
    "app.workers.email_tasks.*": {"queue": "email"},
    "app.workers.analytics_tasks.*": {"queue": "analytics"},
    "app.workers.submission_tasks.*": {"queue": "submissions"},
}

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-sessions": {
        "task": "app.workers.cleanup_tasks.cleanup_expired_sessions",
        "schedule": 3600.0,  # Every hour
    },
    "generate-analytics-reports": {
        "task": "app.workers.analytics_tasks.generate_daily_reports", 
        "schedule": 86400.0,  # Daily
    },
}
