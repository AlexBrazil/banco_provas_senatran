from django.urls import path

from . import views


app_name = "apostila_cnh"

urlpatterns = [
    path("", views.index, name="index"),
]

