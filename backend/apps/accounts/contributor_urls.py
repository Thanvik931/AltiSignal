"""Contributor-facing URLs."""
from django.urls import path
from .views import ProfileView, ContributorStatsView

urlpatterns = [
    path("me/", ProfileView.as_view(), name="contributor-profile"),
    path("me/stats/", ContributorStatsView.as_view(), name="contributor-stats"),
]
