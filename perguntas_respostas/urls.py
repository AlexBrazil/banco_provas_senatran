from django.urls import path

from . import views


app_name = "perguntas_respostas"

urlpatterns = [
    path("", views.index, name="index"),
    path("iniciar/", views.iniciar_estudo, name="iniciar"),
    path("estudar/<str:sessao_id>/", views.estudar, name="estudar"),
    path("preferencias/tempo/", views.salvar_tempo_preferencia, name="salvar_tempo"),
]
