"""
Measurement model — core raw data collected by Android agents.
"""
from django.contrib.gis.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import h3


class AltitudeBand(models.TextChoices):
    GROUND = "0", "Ground (~0 m)"
    BAND_30 = "30", "30 m"
    BAND_60 = "60", "60 m"
    BAND_90 = "90", "90 m"
    BAND_120 = "120", "120 m"


def classify_altitude_band(altitude_m: float) -> str:
    """Classify raw barometric altitude into a band label."""
    if altitude_m < 15:
        return AltitudeBand.GROUND
    elif altitude_m < 45:
        return AltitudeBand.BAND_30
    elif altitude_m < 75:
        return AltitudeBand.BAND_60
    elif altitude_m < 105:
        return AltitudeBand.BAND_90
    else:
        return AltitudeBand.BAND_120


class Measurement(models.Model):
    """
    One signal sample uploaded by a contributor.

    FR-1: RSRP, RSRQ, SINR, cell_id, PCI, band, GPS lat/lon, barometric altitude @ 1 Hz
    FR-2: Altitude band tagged automatically or declared by contributor
    FR-5: Contributor ID attached
    """
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="measurements",
    )
    timestamp = models.DateTimeField(db_index=True)
    location = models.PointField(
        geography=True,
        srid=4326,
        help_text="GPS fix as WGS84 point (longitude, latitude).",
    )
    altitude = models.FloatField(
        help_text="Barometric altitude above ground in metres.",
        validators=[MinValueValidator(-500.0), MaxValueValidator(1000.0)],
    )
    altitude_band = models.CharField(
        max_length=3,
        choices=AltitudeBand.choices,
        db_index=True,
    )

    # Cellular metrics
    rsrp = models.FloatField(
        help_text="Reference Signal Received Power (dBm). Valid: -140 to -40.",
        validators=[MinValueValidator(-140.0), MaxValueValidator(-40.0)],
    )
    rsrq = models.FloatField(
        help_text="Reference Signal Received Quality (dB). Valid: -20 to -3.",
        null=True, blank=True,
        validators=[MinValueValidator(-20.0), MaxValueValidator(0.0)],
    )
    sinr = models.FloatField(
        help_text="Signal to Interference + Noise Ratio (dB).",
        null=True, blank=True,
        validators=[MinValueValidator(-20.0), MaxValueValidator(40.0)],
    )
    cell_id = models.CharField(max_length=20, blank=True)
    pci = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Physical Cell Identity (0–1007 for LTE).",
        validators=[MaxValueValidator(1007)],
    )
    band = models.CharField(
        max_length=10, blank=True,
        help_text="e.g. 'B3', 'B40', 'n78'",
    )
    network_type = models.CharField(
        max_length=10, blank=True,
        help_text="e.g. 'LTE', 'NR' (5G NR)",
    )

    # Device metadata
    device_model = models.CharField(max_length=100, blank=True)
    operator = models.CharField(max_length=50, blank=True)

    # H3 index (computed on save)
    h3_index = models.CharField(max_length=20, blank=True, db_index=True)

    # Quality control
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "measurements"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["altitude_band", "h3_index"]),
            models.Index(fields=["contributor", "timestamp"]),
            models.Index(fields=["is_flagged"]),
        ]

    def save(self, *args, **kwargs):
        # Auto-classify altitude band if not set
        if not self.altitude_band:
            self.altitude_band = classify_altitude_band(self.altitude)
        # Compute H3 index
        if self.location:
            resolution = getattr(settings, "H3_RESOLUTION", 8)
            self.h3_index = h3.latlng_to_cell(
                self.location.y, self.location.x, resolution
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Measurement({self.contributor_id}, {self.altitude_band}m, RSRP={self.rsrp})"

    @property
    def is_link_loss(self) -> bool:
        threshold = getattr(settings, "LINK_LOSS_RSRP_THRESHOLD", -110)
        return self.rsrp < threshold
