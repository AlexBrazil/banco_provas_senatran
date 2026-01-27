from django.urls import path
from .views_webhooks import openpix_webhook

urlpatterns = [
    path("openpix/", openpix_webhook, name="openpix_webhook"),
]
