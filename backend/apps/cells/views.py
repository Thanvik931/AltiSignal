"""
Views for cells and gap detection.
FR-7: GET /cells?bbox=&altitude=
FR-8: GET /gap?bbox=&altitude=
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.gis.geos import Polygon
from django.conf import settings

from .models import CellStat
from .serializers import CellStatSerializer, GapCellSerializer
from apps.cells.h3_utils import cell_to_latlng


class CellStatListView(APIView):
    """
    GET /api/v1/cells/?bbox=lon1,lat1,lon2,lat2&altitude=60
    Returns aggregated H3 cell statistics. Used to colour the map.
    FR-7
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("bbox", str, description="lon_min,lat_min,lon_max,lat_max"),
            OpenApiParameter("altitude", str, description="Altitude band: 0,30,60,90,120"),
        ],
        responses={200: CellStatSerializer(many=True)},
        summary="Get H3 cell statistics for map colouring",
    )
    def get(self, request):
        qs = CellStat.objects.all()

        bbox_param = request.query_params.get("bbox")
        if bbox_param:
            try:
                parts = [float(p) for p in bbox_param.split(",")]
                if len(parts) != 4:
                    raise ValueError("bbox must have exactly 4 values")
                bbox = Polygon.from_bbox(parts)
                qs = qs.filter(centroid__within=bbox)
            except Exception:
                return Response(
                    {"error": "bbox must be lon_min,lat_min,lon_max,lat_max"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        altitude = request.query_params.get("altitude")
        if altitude:
            qs = qs.filter(altitude_band=altitude)

        serializer = CellStatSerializer(qs[:500], many=True)
        return Response(serializer.data)


class GapView(APIView):
    """
    GET /api/v1/cells/gap/?bbox=lon1,lat1,lon2,lat2&altitude=60
    Returns cells where ground-level RSRP and the specified altitude RSRP
    differ by more than GAP_THRESHOLD_DBM (default 10 dBm).
    FR-8
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("bbox", str, description="lon_min,lat_min,lon_max,lat_max"),
            OpenApiParameter("altitude", str, description="Target altitude band: 30,60,90,120"),
        ],
        responses={200: GapCellSerializer(many=True)},
        summary="Gap view: cells where ground map looks good but altitude data says bad",
    )
    def get(self, request):
        gap_threshold = getattr(settings, "GAP_THRESHOLD_DBM", 10)

        bbox_param = request.query_params.get("bbox")
        altitude = request.query_params.get("altitude", "60")

        # Ground-level stats
        ground_qs = CellStat.objects.filter(altitude_band="0")
        alt_qs = CellStat.objects.filter(altitude_band=altitude)

        if bbox_param:
            try:
                parts = [float(p) for p in bbox_param.split(",")]
                if len(parts) != 4:
                    raise ValueError("bbox must have exactly 4 values")
                bbox = Polygon.from_bbox(parts)
                ground_qs = ground_qs.filter(centroid__within=bbox)
                alt_qs = alt_qs.filter(centroid__within=bbox)
            except Exception:
                return Response(
                    {"error": "bbox must be lon_min,lat_min,lon_max,lat_max"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Build lookup by H3 index
        ground_map = {c.h3_index: c for c in ground_qs if c.mean_rsrp is not None}
        alt_map = {c.h3_index: c for c in alt_qs if c.mean_rsrp is not None}

        gap_cells = []
        for h3_idx, alt_cell in alt_map.items():
            ground_cell = ground_map.get(h3_idx)
            if not ground_cell:
                continue
            delta = ground_cell.mean_rsrp - alt_cell.mean_rsrp
            if delta >= gap_threshold:
                lat, lon = None, None
                if alt_cell.centroid:
                    lon = alt_cell.centroid.x
                    lat = alt_cell.centroid.y
                else:
                    try:
                        lat, lon = cell_to_latlng(h3_idx)
                    except Exception:
                        pass
                gap_cells.append({
                    "h3_index": h3_idx,
                    "altitude_band": altitude,
                    "ground_rsrp": round(ground_cell.mean_rsrp, 2),
                    "altitude_rsrp": round(alt_cell.mean_rsrp, 2),
                    "delta_rsrp": round(delta, 2),
                    "lon": lon,
                    "lat": lat,
                    "confidence": min(
                        ground_cell.confidence or 0,
                        alt_cell.confidence or 0,
                    ),
                })

        gap_cells.sort(key=lambda x: x["delta_rsrp"], reverse=True)
        return Response(GapCellSerializer(gap_cells, many=True).data)
