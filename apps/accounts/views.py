"""Account views — registration, profile, API key management."""

import hashlib
import secrets

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import APIKey
from .serializers import (
    APIKeyCreateSerializer,
    APIKeySerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserProfileSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class APIKeyListCreateView(APIView):
    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        return Response(APIKeySerializer(keys, many=True).data)

    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_key = f"dm_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = APIKey.objects.create(
            user=request.user,
            name=serializer.validated_data["name"],
            key_hash=key_hash,
            prefix=raw_key[:8],
            expires_at=serializer.validated_data.get("expires_at"),
        )

        data = APIKeySerializer(api_key).data
        data["key"] = raw_key  # Only shown once
        return Response(data, status=status.HTTP_201_CREATED)


class APIKeyDestroyView(generics.DestroyAPIView):
    serializer_class = APIKeySerializer
    lookup_field = "id"

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)
