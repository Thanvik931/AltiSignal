from django.urls import path
from .views import RouteRiskView

urlpatterns = [
    path("route-risk/", RouteRiskView.as_view(), name="route-risk"),
]
