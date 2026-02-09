from django.urls import path

from . import views


app_name = "manual_pratico"

urlpatterns = [
    path("", views.index, name="index"),
]

