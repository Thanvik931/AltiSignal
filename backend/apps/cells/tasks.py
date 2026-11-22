"""
Celery tasks for H3 aggregation.
FR-7, FR-8: Aggregate measurements into CellStat after each batch upload.
"""
from celery import shared_task
from django.db import transaction
from django.contrib.gis.geos import Point
import numpy as np
import h3
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def trigger_aggregation(self, h3_indices: list, altitude_bands: list):
    """
    Triggered after a measurement batch upload.
    Recomputes CellStat for affected (h3_index, altitude_band) pairs.
    """
    try:
        from apps.measurements.models import Measurement
        from apps.cells.models import CellStat
        from django.conf import settings

        threshold = getattr(settings, "LINK_LOSS_RSRP_THRESHOLD", -110)

        for h3_idx in h3_indices:
            for band in altitude_bands:
                _aggregate_cell(h3_idx, band, threshold, Measurement, CellStat)

        logger.info(
            "Aggregation complete: %d cells x %d bands",
            len(h3_indices), len(altitude_bands),
        )
    except Exception as exc:
        logger.exception("Aggregation task failed: %s", exc)
        raise self.retry(exc=exc)


def _aggregate_cell(h3_idx, altitude_band, threshold, Measurement, CellStat):
    """Compute aggregated stats for one (H3, altitude_band) pair."""
    readings = Measurement.objects.filter(
        h3_index=h3_idx,
        altitude_band=altitude_band,
        is_flagged=False,
    ).values_list("rsrp", "rsrq", "sinr")

    rsrp_vals = [r[0] for r in readings if r[0] is not None]
    rsrq_vals = [r[1] for r in readings if r[1] is not None]
    sinr_vals = [r[2] for r in readings if r[2] is not None]

    if not rsrp_vals:
        return

    n = len(rsrp_vals)
    arr = np.array(rsrp_vals)
    fraction_below = float(np.mean(arr < threshold))
    # Confidence: sigmoid-like function, saturates at 1.0 around 100 readings
    confidence = float(min(1.0, n / 100.0))

    # H3 centroid
    lat, lon = h3.cell_to_latlng(h3_idx)
    centroid = Point(lon, lat, srid=4326)

    with transaction.atomic():
        CellStat.objects.update_or_create(
            h3_index=h3_idx,
            altitude_band=altitude_band,
            defaults={
                "centroid": centroid,
                "count": n,
                "mean_rsrp": float(np.mean(arr)),
                "p10_rsrp": float(np.percentile(arr, 10)),
                "p50_rsrp": float(np.percentile(arr, 50)),
                "variance_rsrp": float(np.var(arr)),
                "mean_rsrq": float(np.mean(rsrq_vals)) if rsrq_vals else None,
                "mean_sinr": float(np.mean(sinr_vals)) if sinr_vals else None,
                "fraction_below_threshold": fraction_below,
                "confidence": confidence,
            },
        )
