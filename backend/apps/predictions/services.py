"""
Route risk computation service.
Uses CellStat data as a baseline model (Weekend 5 will add the learned model).
"""
from django.conf import settings
from apps.cells.models import CellStat
from apps.cells.h3_utils import latlng_to_cell


RISK_LEVELS = {
    (0.0, 0.2): "LOW",
    (0.2, 0.4): "MEDIUM",
    (0.4, 1.0): "HIGH",
}


def _risk_level(prob: float) -> str:
    for (lo, hi), label in RISK_LEVELS.items():
        if lo <= prob < hi:
            return label
    return "HIGH"


def _interpolate_points(start, end, n_points=5):
    """Linear interpolation between two (lon, lat) points."""
    lons = [start[0] + (end[0] - start[0]) * i / (n_points - 1) for i in range(n_points)]
    lats = [start[1] + (end[1] - start[1]) * i / (n_points - 1) for i in range(n_points)]
    return list(zip(lons, lats))


def compute_route_risk(route_geojson: dict, altitude_band: str) -> dict:
    """
    Baseline model: for each route segment, look up H3 cells along the segment
    and return the fraction_below_threshold as link-loss probability.
    If no data, return UNKNOWN.
    """
    resolution = getattr(settings, "H3_RESOLUTION", 8)
    threshold = getattr(settings, "LINK_LOSS_RSRP_THRESHOLD", -110)
    coords = route_geojson["coordinates"]

    segments = []
    for i in range(len(coords) - 1):
        start = coords[i]
        end = coords[i + 1]

        # Sample H3 cells along this segment
        interp_pts = _interpolate_points(start, end, n_points=10)
        h3_indices = list({
            latlng_to_cell(lat, lon, resolution)
            for lon, lat in interp_pts
        })

        # Look up CellStat records
        cell_stats = CellStat.objects.filter(
            h3_index__in=h3_indices,
            altitude_band=altitude_band,
        )

        if cell_stats.exists():
            fractions = [c.fraction_below_threshold for c in cell_stats if c.fraction_below_threshold is not None]
            mean_rsrps = [c.mean_rsrp for c in cell_stats if c.mean_rsrp is not None]
            prob = float(sum(fractions) / len(fractions)) if fractions else 0.0
            mean_rsrp = float(sum(mean_rsrps) / len(mean_rsrps)) if mean_rsrps else None
            data_coverage = len(cell_stats) / max(len(h3_indices), 1)
            risk_level = _risk_level(prob)
        else:
            prob = 0.0
            mean_rsrp = None
            data_coverage = 0.0
            risk_level = "UNKNOWN"

        segments.append({
            "segment_index": i,
            "start_lon": start[0],
            "start_lat": start[1],
            "end_lon": end[0],
            "end_lat": end[1],
            "h3_indices": h3_indices,
            "link_loss_probability": round(prob, 4),
            "mean_rsrp": round(mean_rsrp, 2) if mean_rsrp else None,
            "data_coverage": round(data_coverage, 3),
            "risk_level": risk_level,
        })

    # Overall risk = max segment risk
    known_probs = [s["link_loss_probability"] for s in segments if s["risk_level"] != "UNKNOWN"]
    overall = max(known_probs) if known_probs else 0.0

    worst_idx = None
    if segments:
        worst_idx = max(range(len(segments)), key=lambda i: segments[i]["link_loss_probability"])

    return {
        "altitude_band": altitude_band,
        "overall_risk": round(overall, 4),
        "worst_segment_index": worst_idx,
        "segments": segments,
        "model_version": "baseline-v1",
        "advisory": (
            "AltiSignal results are advisory only. "
            "Always comply with local regulations and perform independent safety checks."
        ),
    }
