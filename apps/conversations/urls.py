"""Conversation URL patterns."""

from django.urls import path

from . import views

app_name = "conversations"

urlpatterns = [
    path("", views.ConversationListCreateView.as_view(), name="conversation_list"),
    path("<uuid:id>/", views.ConversationDetailView.as_view(), name="conversation_detail"),
    path("chat/", views.chat, name="chat"),
]
