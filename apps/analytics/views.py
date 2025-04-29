"""Analytics views — usage dashboards."""

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UsageEvent


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def usage_summary(request):
    """Return usage summary for the authenticated user."""
    days = int(request.query_params.get("days", 30))
    since = timezone.now() - timezone.timedelta(days=days)

    events = UsageEvent.objects.filter(user=request.user, created_at__gte=since)

    summary = events.aggregate(
        total_queries=Count("id", filter=Count("id", filter=None) and None) or Count("id"),
        total_input_tokens=Sum("input_tokens"),
        total_output_tokens=Sum("output_tokens"),
        avg_latency_ms=Avg("latency_ms"),
    )

    daily_usage = (
        events.annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(count=Count("id"), tokens=Sum("input_tokens") + Sum("output_tokens"))
        .order_by("date")
    )

    by_type = (
        events.values("event_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return Response(
        {
            "period_days": days,
            "summary": summary,
            "daily_usage": list(daily_usage),
            "by_event_type": list(by_type),
        }
    )
