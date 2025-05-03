"""Celery application configuration."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("documind")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "cleanup-expired-documents": {
        "task": "apps.documents.tasks.cleanup_expired_documents",
        "schedule": crontab(hour=2, minute=0),
    },
    "update-collection-stats": {
        "task": "apps.analytics.tasks.update_collection_stats",
        "schedule": crontab(minute="*/30"),
    },
}
