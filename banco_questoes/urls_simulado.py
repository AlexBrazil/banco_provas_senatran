from django.urls import path
from . import views_simulado

app_name = "simulado"

urlpatterns = [
    path("", views_simulado.simulado_config, name="config"),
    path("iniciar/", views_simulado.simulado_iniciar, name="iniciar"),
    path("questao/", views_simulado.simulado_questao, name="questao"),
    path("responder/", views_simulado.simulado_responder, name="responder"),
    path("resultado/", views_simulado.simulado_resultado, name="resultado"),
    #endpoint AJAX
    path("api/modulos/", views_simulado.api_modulos_por_curso, name="api_modulos"),
    path("api/stats/", views_simulado.api_stats, name="api_stats"),
]
