"""
API Router — wires all app-level routers into /api/v1/
Supports both namespaced routes and direct PRD paths (e.g. /route-risk and /gap).
"""
from django.urls import path, include
from apps.cells.views import GapView
from apps.predictions.views import RouteRiskView

urlpatterns = [
    # Measurements
    path("measurements/", include("apps.measurements.urls")),

    # Cell statistics & Gap analysis (supports /cells/, /cells/gap/, and direct /gap/)
    path("cells/", include("apps.cells.urls")),
    path("gap/", GapView.as_view(), name="gap-direct"),

    # Predictions (supports /predictions/route-risk/ and direct /route-risk/)
    path("predictions/", include("apps.predictions.urls")),
    path("route-risk/", RouteRiskView.as_view(), name="route-risk-direct"),

    # Contributors & Profiles
    path("contributors/", include("apps.accounts.contributor_urls")),
]
