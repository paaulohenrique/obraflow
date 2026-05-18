from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(source="company.id", read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "email", "name", "role", "company_id", "is_active", "created_at", "updated_at"]
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "name", "role", "password"]

    def create(self, validated_data):
        # company is injected by the view from request.user.company
        return User.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
