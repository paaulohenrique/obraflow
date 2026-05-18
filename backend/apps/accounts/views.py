from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer, UserCreateSerializer, ChangePasswordSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserCreateView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        # New users belong to the same company as the admin creating them
        serializer.save(company=self.request.user.company)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    search_fields = ["name", "email"]
    filterset_fields = ["role", "is_active"]
    ordering_fields = ["name", "email", "created_at", "role"]
    ordering = ["name"]

    def get_queryset(self):
        return User.objects.filter(company=self.request.user.company)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            raise ValidationError({"old_password": "Senha atual incorreta."})
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return Response({"detail": "Senha alterada com sucesso."})
