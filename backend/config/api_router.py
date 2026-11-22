"""
API Router — wires all app-level routers into /api/v1/
"""
from django.urls import path, include

urlpatterns = [
    path("measurements/", include("apps.measurements.urls")),
    path("cells/", include("apps.cells.urls")),
    path("predictions/", include("apps.predictions.urls")),
    path("contributors/", include("apps.accounts.contributor_urls")),
]
