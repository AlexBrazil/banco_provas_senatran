from django.urls import path
from . import views_simulado

app_name = "simulado"

urlpatterns = [
    path("", views_simulado.simulado_config, name="config"),
    path("iniciar/", views_simulado.simulado_iniciar, name="iniciar"),
    path("questao/", views_simulado.simulado_questao, name="questao"),
    path("responder/", views_simulado.simulado_responder, name="responder"),
    path("resultado/", views_simulado.simulado_resultado, name="resultado"),
]
