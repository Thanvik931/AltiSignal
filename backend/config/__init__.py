from django.contrib import admin
from django.apps import apps
from config.celery import app as celery_app

__all__ = ("celery_app",)
