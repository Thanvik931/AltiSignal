from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Contributor


@admin.register(Contributor)
class ContributorAdmin(UserAdmin):
    list_display = ["username", "email", "role", "reputation_weight", "total_measurements", "is_flagged", "created_at"]
    list_filter = ["role", "is_flagged", "is_staff"]
    fieldsets = UserAdmin.fieldsets + (
        ("AltiSignal", {"fields": ("role", "reputation_weight", "bio", "organisation", "total_measurements", "is_flagged")}),
    )
