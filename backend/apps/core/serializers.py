from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer that exposes standard audit fields as read-only."""

    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        abstract = True
