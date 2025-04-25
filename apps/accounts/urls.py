"""Account URL patterns."""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("api-keys/", views.APIKeyListCreateView.as_view(), name="api_keys"),
    path("api-keys/<uuid:id>/", views.APIKeyDestroyView.as_view(), name="api_key_delete"),
]
