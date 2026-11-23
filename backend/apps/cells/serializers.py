"""
Serializers for CellStat.
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import CellStat


class CellStatSerializer(GeoFeatureModelSerializer):
    """GeoJSON Feature for one H3 cell's aggregated stats."""
    class Meta:
        model = CellStat
        geo_field = "centroid"
        fields = [
            "id", "h3_index", "altitude_band", "count",
            "mean_rsrp", "p10_rsrp", "p50_rsrp", "variance_rsrp",
            "mean_rsrq", "mean_sinr",
            "fraction_below_threshold", "confidence", "updated_at",
        ]


class GapCellSerializer(serializers.Serializer):
    """Represents a gap cell: ground says good, altitude says bad."""
    h3_index = serializers.CharField()
    altitude_band = serializers.CharField()
    ground_rsrp = serializers.FloatField()
    altitude_rsrp = serializers.FloatField()
    delta_rsrp = serializers.FloatField()
    lon = serializers.FloatField(allow_null=True, required=False)
    lat = serializers.FloatField(allow_null=True, required=False)
    confidence = serializers.FloatField(allow_null=True, required=False)
