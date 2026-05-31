from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from .views import LoginView, MeView, UserCreateView, UserListView, ChangePasswordView

urlpatterns = [
    # JWT
    path("token/", LoginView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # Users
    path("me/", MeView.as_view(), name="user-me"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/create/", UserCreateView.as_view(), name="user-create"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
