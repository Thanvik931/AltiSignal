"""
CellStat model — H3-aggregated statistics per altitude band.
ModelRun — ML model metadata.
"""
from django.contrib.gis.db import models


class CellStat(models.Model):
    """
    Aggregated signal statistics for one H3 hexagon at one altitude band.
    Updated by Celery tasks after new measurements arrive.

    FR-7: GET /cells?bbox=&altitude= returns these records.
    FR-8: gap view uses ground_rsrp vs altitude_rsrp difference.
    """
    h3_index = models.CharField(max_length=20, db_index=True)
    altitude_band = models.CharField(max_length=3, db_index=True)

    # Geometry for spatial queries (centroid of H3 hex)
    centroid = models.PointField(srid=4326, null=True)

    # Aggregated metrics
    count = models.PositiveIntegerField(default=0)
    mean_rsrp = models.FloatField(null=True)
    p10_rsrp = models.FloatField(null=True, help_text="10th percentile RSRP")
    p50_rsrp = models.FloatField(null=True, help_text="Median RSRP")
    variance_rsrp = models.FloatField(null=True)
    mean_rsrq = models.FloatField(null=True)
    mean_sinr = models.FloatField(null=True)
    fraction_below_threshold = models.FloatField(
        null=True,
        help_text="Fraction of readings where RSRP < LINK_LOSS_RSRP_THRESHOLD",
    )
    confidence = models.FloatField(
        null=True,
        help_text="Statistical confidence score 0–1 based on sample count",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cell_stats"
        unique_together = [("h3_index", "altitude_band")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"CellStat(h3={self.h3_index}, band={self.altitude_band}, mean_rsrp={self.mean_rsrp})"


class ModelRun(models.Model):
    """Tracks ML model training runs."""
    version = models.CharField(max_length=50, unique=True)
    training_date = models.DateTimeField()
    auc_score = models.FloatField(null=True)
    baseline_auc = models.FloatField(null=True)
    n_training_samples = models.PositiveIntegerField(default=0)
    feature_list = models.JSONField(default=list)
    hyperparameters = models.JSONField(default=dict)
    model_path = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "model_runs"
        ordering = ["-training_date"]

    def __str__(self):
        return f"ModelRun(v={self.version}, AUC={self.auc_score})"


class RouteQuery(models.Model):
    """Logs route-risk query requests and results."""
    route_geometry = models.LineStringField(srid=4326)
    altitude_band = models.CharField(max_length=3)
    result = models.JSONField(default=dict)
    model_run = models.ForeignKey(
        ModelRun, null=True, on_delete=models.SET_NULL, related_name="route_queries"
    )
    latency_ms = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "route_queries"
        ordering = ["-created_at"]
