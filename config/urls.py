"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from banco_questoes.urls_simulado import urlpatterns as simulado_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("banco_questoes.urls_auth")),
    path("menu/", include("menu.urls", namespace="menu")),
    path("perguntas-respostas/", include("perguntas_respostas.urls", namespace="perguntas_respostas")),
    path("apostila-cnh/", include("apostila_cnh.urls", namespace="apostila_cnh")),
    path("simulacao-prova-detran/", include("simulacao_prova.urls", namespace="simulacao_prova")),
    path("manual-aulas-praticas/", include("manual_pratico.urls", namespace="manual_pratico")),
    path("aprenda-jogando/", include("aprenda_jogando.urls", namespace="aprenda_jogando")),
    path("oraculo/", include("oraculo.urls", namespace="oraculo")),
    path("aprova-plus/", include("aprova_plus.urls", namespace="aprova_plus")),
    path("simulado/", include("banco_questoes.urls_simulado", namespace="simulado")),
    path("", include((simulado_urlpatterns, "simulado_legacy"), namespace="simulado_legacy")),
    path("payments/", include("payments.urls")),
]
