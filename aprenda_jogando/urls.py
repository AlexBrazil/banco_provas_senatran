from django.urls import path

from . import views


app_name = "aprenda_jogando"

urlpatterns = [
    path("", views.index, name="index"),
]

