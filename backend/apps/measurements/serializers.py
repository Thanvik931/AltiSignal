"""
Serializers for the measurements app.
FR-6: POST /measurements — batch accept + validate.
"""
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import Point
from .models import Measurement, AltitudeBand


class MeasurementSerializer(serializers.ModelSerializer):
    longitude = serializers.FloatField(write_only=True)
    latitude = serializers.FloatField(write_only=True)

    class Meta:
        model = Measurement
        fields = [
            "id", "timestamp", "longitude", "latitude", "altitude", "altitude_band",
            "rsrp", "rsrq", "sinr", "cell_id", "pci", "band", "network_type",
            "device_model", "operator", "h3_index", "created_at",
        ]
        read_only_fields = ["id", "h3_index", "created_at"]

    def validate_rsrp(self, value):
        if not (-140.0 <= value <= -40.0):
            raise serializers.ValidationError(
                f"RSRP {value} dBm is outside plausible range [-140, -40]."
            )
        return value

    def validate_longitude(self, value):
        if not (-180.0 <= value <= 180.0):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def validate_latitude(self, value):
        if not (-90.0 <= value <= 90.0):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate(self, attrs):
        lon = attrs.pop("longitude")
        lat = attrs.pop("latitude")
        attrs["location"] = Point(lon, lat, srid=4326)
        return attrs


class MeasurementBatchSerializer(serializers.Serializer):
    """FR-3: Accept readings in batches."""
    readings = MeasurementSerializer(many=True)

    def validate_readings(self, value):
        if not value:
            raise serializers.ValidationError("Batch must contain at least one reading.")
        if len(value) > 1000:
            raise serializers.ValidationError("Maximum 1000 readings per batch.")
        return value

    def create(self, validated_data):
        contributor = self.context["request"].user
        readings = validated_data["readings"]
        objs = [
            Measurement(contributor=contributor, **reading)
            for reading in readings
        ]
        return Measurement.objects.bulk_create(objs, batch_size=200)


class MeasurementReadSerializer(GeoFeatureModelSerializer):
    """GeoJSON output for measurement reads."""
    class Meta:
        model = Measurement
        geo_field = "location"
        fields = [
            "id", "timestamp", "altitude", "altitude_band",
            "rsrp", "rsrq", "sinr", "h3_index",
        ]
