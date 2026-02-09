from django.urls import path

from . import views


app_name = "perguntas_respostas"

urlpatterns = [
    path("", views.index, name="index"),
]

