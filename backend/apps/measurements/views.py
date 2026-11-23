"""
Views for the measurements app.
FR-6: POST /measurements — batch accept, validate, store.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.contrib.gis.geos import Polygon

from .models import Measurement
from .serializers import MeasurementBatchSerializer, MeasurementReadSerializer
from apps.cells.tasks import trigger_aggregation


class MeasurementBatchView(APIView):
    """
    POST /api/v1/measurements/
    Accept a batch of signal measurements from the Android agent.

    FR-3: Buffer & upload in batches.
    FR-5: Contributor ID auto-attached from JWT.
    FR-6: Validate (coordinate ranges, plausible RSRP, timestamp sanity).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MeasurementBatchSerializer,
        responses={201: {"type": "object", "properties": {
            "accepted": {"type": "integer"},
            "rejected": {"type": "integer"},
            "errors": {"type": "array"},
        }}},
        summary="Upload a batch of signal measurements",
        description="Accepts up to 1000 readings per request. Each reading is validated "
                    "before storage. Returns count of accepted/rejected readings.",
    )
    def post(self, request):
        serializer = MeasurementBatchSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"accepted": 0, "rejected": 0, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = serializer.save()

        # Trigger background H3 aggregation for affected cells
        h3_indices = list({m.h3_index for m in created if m.h3_index})
        altitude_bands = list({m.altitude_band for m in created})
        try:
            trigger_aggregation.delay(h3_indices, altitude_bands)
        except Exception:
            # Celery/Redis might be offline in development or unit tests; continue safely
            pass

        # Update contributor total_measurements
        request.user.__class__.objects.filter(pk=request.user.pk).update(
            total_measurements=request.user.total_measurements + len(created)
        )

        return Response(
            {
                "accepted": len(created),
                "rejected": 0,
                "message": f"{len(created)} readings stored successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class MeasurementListView(APIView):
    """
    GET /api/v1/measurements/?bbox=lon1,lat1,lon2,lat2&altitude=60&limit=200
    Returns measurements within a bounding box filtered by altitude band.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("bbox", str, description="lon_min,lat_min,lon_max,lat_max"),
            OpenApiParameter("altitude", str, description="Altitude band: 0,30,60,90,120"),
            OpenApiParameter("limit", int, description="Max results (default 200)"),
        ],
        responses={200: MeasurementReadSerializer(many=True)},
        summary="List measurements within a bounding box",
    )
    def get(self, request):
        qs = Measurement.objects.filter(is_flagged=False).select_related("contributor")

        bbox_param = request.query_params.get("bbox")
        if bbox_param:
            try:
                parts = [float(p) for p in bbox_param.split(",")]
                if len(parts) != 4:
                    raise ValueError("bbox must contain exactly 4 values")
                bbox = Polygon.from_bbox(parts)
                qs = qs.filter(location__within=bbox)
            except Exception:
                return Response(
                    {"error": "bbox must be lon_min,lat_min,lon_max,lat_max"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        altitude = request.query_params.get("altitude")
        if altitude:
            qs = qs.filter(altitude_band=altitude)

        try:
            limit = min(int(request.query_params.get("limit", 200)), 1000)
        except (ValueError, TypeError):
            limit = 200
        qs = qs[:limit]

        serializer = MeasurementReadSerializer(qs, many=True)
        return Response(serializer.data)


class MeasurementFlagView(APIView):
    """
    PATCH /api/v1/measurements/<pk>/flag/
    Admin: flag a suspicious measurement.
    FR (from user story 6): Admin can flag and remove suspicious contributions.
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            m = Measurement.objects.get(pk=pk)
        except Measurement.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        reason = request.data.get("reason", "Flagged by admin")
        m.is_flagged = True
        m.flag_reason = reason
        m.save(update_fields=["is_flagged", "flag_reason"])
        return Response({"flagged": True, "reason": reason})
