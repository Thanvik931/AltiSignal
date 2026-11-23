"""
Serializers for route-risk prediction.
"""
from rest_framework import serializers


class RouteRiskRequestSerializer(serializers.Serializer):
    """
    Input: a GeoJSON LineString and altitude band.
    Example:
        {
          "route": {"type": "LineString", "coordinates": [[78.3, 17.4], [78.4, 17.5]]},
          "altitude_band": "90"
        }
    """
    route = serializers.JSONField(
        help_text="GeoJSON LineString geometry object",
    )
    altitude_band = serializers.ChoiceField(
        choices=["0", "30", "60", "90", "120"],
        help_text="Altitude band in metres",
    )

    def validate_route(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("route must be a GeoJSON object.")
        if value.get("type") != "LineString":
            raise serializers.ValidationError("route must be a GeoJSON LineString.")
        coords = value.get("coordinates", [])
        if len(coords) < 2:
            raise serializers.ValidationError("LineString must have at least 2 coordinates.")
        for c in coords:
            if len(c) < 2:
                raise serializers.ValidationError("Each coordinate must have [lon, lat].")
            lon, lat = c[0], c[1]
            if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                raise serializers.ValidationError(f"Invalid coordinate: [{lon}, {lat}]")
        return value


class SegmentRiskSerializer(serializers.Serializer):
    segment_index = serializers.IntegerField()
    start_lon = serializers.FloatField()
    start_lat = serializers.FloatField()
    end_lon = serializers.FloatField()
    end_lat = serializers.FloatField()
    h3_indices = serializers.ListField(child=serializers.CharField())
    link_loss_probability = serializers.FloatField()
    mean_rsrp = serializers.FloatField(allow_null=True, required=False)
    data_coverage = serializers.FloatField(help_text="Fraction of segment H3 cells with data")
    risk_level = serializers.CharField(help_text="LOW / MEDIUM / HIGH / UNKNOWN")


class RouteRiskResponseSerializer(serializers.Serializer):
    altitude_band = serializers.CharField()
    overall_risk = serializers.FloatField()
    worst_segment_index = serializers.IntegerField(allow_null=True, required=False)
    segments = SegmentRiskSerializer(many=True)
    model_version = serializers.CharField()
    advisory = serializers.CharField()
