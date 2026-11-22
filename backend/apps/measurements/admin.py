from django.contrib import admin
from .models import Measurement


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ["id", "contributor", "timestamp", "altitude_band", "rsrp", "h3_index", "is_flagged"]
    list_filter = ["altitude_band", "is_flagged", "network_type", "operator"]
    search_fields = ["contributor__username", "h3_index", "cell_id"]
    readonly_fields = ["h3_index", "created_at"]
    actions = ["flag_selected"]

    @admin.action(description="Flag selected measurements")
    def flag_selected(self, request, queryset):
        queryset.update(is_flagged=True, flag_reason="Bulk flagged by admin")
