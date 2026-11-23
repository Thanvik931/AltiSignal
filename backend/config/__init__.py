# This exposes the Celery app so Django's auto-reloader
# picks it up and @shared_task works across all apps.
from config.celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
