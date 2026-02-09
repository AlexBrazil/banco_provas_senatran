from django.urls import path

from . import views


app_name = "aprova_plus"

urlpatterns = [
    path("", views.index, name="index"),
]

