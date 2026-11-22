from django.urls import path
from .views import MeasurementBatchView, MeasurementListView, MeasurementFlagView

urlpatterns = [
    path("", MeasurementBatchView.as_view(), name="measurements-batch"),
    path("list/", MeasurementListView.as_view(), name="measurements-list"),
    path("<int:pk>/flag/", MeasurementFlagView.as_view(), name="measurements-flag"),
]
