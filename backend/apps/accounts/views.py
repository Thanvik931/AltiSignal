"""
Auth views: register, profile, stats.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer, ContributorProfileSerializer
from apps.measurements.models import Measurement


class RegisterView(APIView):
    """POST /api/v1/auth/register/"""
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: ContributorProfileSerializer},
        summary="Register a new contributor",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            ContributorProfileSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    """GET/PATCH /api/v1/contributors/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ContributorProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ContributorProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ContributorStatsView(APIView):
    """
    GET /api/v1/contributors/me/stats/
    User story 5: contributor sees their total measurements and areas needing data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        user = request.user
        by_band = (
            Measurement.objects
            .filter(contributor=user, is_flagged=False)
            .values("altitude_band")
            .annotate(count=Count("id"))
            .order_by("altitude_band")
        )
        return Response({
            "total_measurements": user.total_measurements,
            "by_altitude_band": list(by_band),
            "reputation_weight": user.reputation_weight,
        })
