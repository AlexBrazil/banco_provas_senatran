from django.urls import path

from . import views


app_name = "oraculo"

urlpatterns = [
    path("", views.index, name="index"),
]

