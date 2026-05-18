"""
Celery Task Queue Configuration
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange

from app.core.config import settings


# Create Celery application instance
celery_app = Celery(
    "telegram_football_manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.match_simulation",
        "app.tasks.weekly_updates",
        "app.tasks.ai_manager",
    ]
)


# Celery Configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=4,  # Number of tasks to prefetch per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,
    
    # Task routing
    task_routes={
        "app.tasks.match_simulation.*": {"queue": "matches"},
        "app.tasks.weekly_updates.*": {"queue": "updates"},
        "app.tasks.ai_manager.*": {"queue": "ai"},
    },
    
    # Task time limits
    task_time_limit=300,  # Hard time limit: 5 minutes
    task_soft_time_limit=240,  # Soft time limit: 4 minutes
    
    # Task retry settings
    task_acks_late=True,  # Acknowledge task after execution (not before)
    task_reject_on_worker_lost=True,  # Reject task if worker crashes
    
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        "weekly-update": {
            "task": "app.tasks.weekly_updates.process_weekly_update",
            "schedule": crontab(day_of_week=1, hour=0, minute=0),  # Every Monday at midnight
        },
        "cleanup-expired-results": {
            "task": "app.tasks.maintenance.cleanup_expired_results",
            "schedule": crontab(hour=2, minute=0),  # Every day at 2 AM
        },
    },
)


# Define task queues with priorities
celery_app.conf.task_queues = (
    Queue(
        "matches",
        Exchange("matches"),
        routing_key="matches",
        priority=10,  # High priority for match simulations
    ),
    Queue(
        "updates",
        Exchange("updates"),
        routing_key="updates",
        priority=5,  # Medium priority for weekly updates
    ),
    Queue(
        "ai",
        Exchange("ai"),
        routing_key="ai",
        priority=3,  # Lower priority for AI tasks
    ),
    Queue(
        "default",
        Exchange("default"),
        routing_key="default",
        priority=1,  # Lowest priority for misc tasks
    ),
)


# Task base class with common configuration
class BaseTask(celery_app.Task):
    """Base task class with common error handling and logging"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add random jitter to retry delays
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails after all retries"""
        print(f"Task {self.name} failed: {exc}")
        # TODO: Add proper logging and alerting
        super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        print(f"Task {self.name} retrying: {exc}")
        super().on_retry(exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        print(f"Task {self.name} succeeded")
        super().on_success(retval, task_id, args, kwargs)


# Set default task base class
celery_app.Task = BaseTask


def get_celery_app() -> Celery:
    """
    Get Celery application instance
    
    Returns:
        Celery: Celery application instance
    """
    return celery_app
