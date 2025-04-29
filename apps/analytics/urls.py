"""Analytics URL patterns."""

from django.urls import path

from . import views

app_name = "analytics"

urlpatterns = [
    path("usage/", views.usage_summary, name="usage_summary"),
]
