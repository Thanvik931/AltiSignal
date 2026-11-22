from django.urls import path
from .views import CellStatListView, GapView

urlpatterns = [
    path("", CellStatListView.as_view(), name="cells-list"),
    path("gap/", GapView.as_view(), name="cells-gap"),
]
