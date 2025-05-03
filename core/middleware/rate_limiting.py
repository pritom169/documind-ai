"""Token-bucket rate limiter middleware backed by Redis."""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Per-user rate limiting using a sliding window counter in Redis.

    - Anonymous: 20 req/min
    - Authenticated: 100 req/min
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only rate-limit API endpoints
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        if hasattr(request, "user") and request.user.is_authenticated:
            key = f"ratelimit:user:{request.user.id}"
            limit = 100
        else:
            ip = self._get_client_ip(request)
            key = f"ratelimit:anon:{ip}"
            limit = 20

        window = 60  # seconds
        now = time.time()
        window_key = f"{key}:{int(now // window)}"

        current = cache.get(window_key, 0)
        if current >= limit:
            return JsonResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status=429,
            )

        cache.set(window_key, current + 1, timeout=window)

        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(max(0, limit - current - 1))
        return response

    @staticmethod
    def _get_client_ip(request) -> str:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
