from django.urls import path

from . import views


app_name = "apostila_cnh"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/documento/ativo/", views.api_documento_ativo, name="api_documento_ativo"),
    path("api/documento/ativo/pdf/", views.api_documento_ativo_pdf, name="api_documento_ativo_pdf"),
    path("api/progresso/", views.api_progresso, name="api_progresso"),
    path("api/busca/", views.api_busca, name="api_busca"),
]
