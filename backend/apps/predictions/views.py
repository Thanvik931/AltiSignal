"""
Route-risk prediction view.
FR-9: POST /route-risk — GeoJSON LineString + altitude → risk per segment.
"""
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.conf import settings

from .serializers import RouteRiskRequestSerializer, RouteRiskResponseSerializer
from .services import compute_route_risk
from apps.cells.models import RouteQuery


class RouteRiskView(APIView):
    """
    POST /api/v1/predictions/route-risk/

    Accepts a GeoJSON LineString route and altitude band,
    returns link-loss probability per segment, overall risk, and worst segment.
    FR-9
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RouteRiskRequestSerializer,
        responses={200: RouteRiskResponseSerializer},
        summary="Predict link-loss risk for a planned drone route",
        description="Input a GeoJSON LineString and altitude band. "
                    "Returns risk per segment, overall probability, and the worst segment.",
    )
    def post(self, request):
        serializer = RouteRiskRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        route_geojson = serializer.validated_data["route"]
        altitude_band = serializer.validated_data["altitude_band"]

        t0 = time.monotonic()
        result = compute_route_risk(route_geojson, altitude_band)
        latency_ms = int((time.monotonic() - t0) * 1000)

        # Log the query
        from django.contrib.gis.geos import GEOSGeometry
        try:
            geom = GEOSGeometry(str(route_geojson))
            RouteQuery.objects.create(
                route_geometry=geom,
                altitude_band=altitude_band,
                result=result,
                latency_ms=latency_ms,
            )
        except Exception:
            pass  # Non-critical

        response_serializer = RouteRiskResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data)
