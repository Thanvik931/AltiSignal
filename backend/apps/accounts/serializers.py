"""
Auth serializers and views for accounts.
FR-10: JWT auth with contributor and admin roles.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

Contributor = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model = Contributor
        fields = ["username", "email", "password", "password2", "organisation"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return Contributor.objects.create_user(**validated_data)


class ContributorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contributor
        fields = [
            "id", "username", "email", "role", "reputation_weight",
            "bio", "organisation", "total_measurements", "is_flagged", "created_at",
        ]
        read_only_fields = ["id", "role", "reputation_weight", "total_measurements", "is_flagged", "created_at"]
