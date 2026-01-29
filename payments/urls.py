from django.urls import path

from . import views


app_name = "payments"

urlpatterns = [
    path("upgrade/free/", views.upgrade_free, name="upgrade_free"),
    path("upgrade/free/check/", views.upgrade_free_check, name="upgrade_free_check"),
    path("webhook/abacatepay/", views.webhook_abacatepay, name="webhook_abacatepay"),
]
