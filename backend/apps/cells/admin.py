from django.contrib import admin
from .models import CellStat, ModelRun, RouteQuery


@admin.register(CellStat)
class CellStatAdmin(admin.ModelAdmin):
    list_display = ["h3_index", "altitude_band", "count", "mean_rsrp", "fraction_below_threshold", "confidence", "updated_at"]
    list_filter = ["altitude_band"]
    search_fields = ["h3_index"]


@admin.register(ModelRun)
class ModelRunAdmin(admin.ModelAdmin):
    list_display = ["version", "training_date", "auc_score", "baseline_auc", "is_active", "n_training_samples"]
    list_filter = ["is_active"]


@admin.register(RouteQuery)
class RouteQueryAdmin(admin.ModelAdmin):
    list_display = ["id", "altitude_band", "latency_ms", "created_at"]
