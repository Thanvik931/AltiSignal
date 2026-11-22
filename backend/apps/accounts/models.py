"""
Contributor (custom user) model for AltiSignal.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class ContributorRole(models.TextChoices):
    CONTRIBUTOR = "contributor", "Contributor"
    ADMIN = "admin", "Admin"
    RESEARCHER = "researcher", "Researcher"


class Contributor(AbstractUser):
    """
    Extended user model. Each contributor collects and uploads measurements.
    Reputation weight is used in future aggregation to down-weight suspect readings.
    """
    role = models.CharField(
        max_length=20,
        choices=ContributorRole.choices,
        default=ContributorRole.CONTRIBUTOR,
    )
    reputation_weight = models.FloatField(
        default=1.0,
        help_text="Multiplier applied to this contributor's readings (0.0–1.0). "
                  "Reduced for flagged or low-quality contributors.",
    )
    bio = models.TextField(blank=True)
    organisation = models.CharField(max_length=200, blank=True)
    total_measurements = models.PositiveIntegerField(default=0)
    is_flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "contributors"
        verbose_name = "Contributor"
        verbose_name_plural = "Contributors"

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_admin_user(self):
        return self.role == ContributorRole.ADMIN or self.is_staff
