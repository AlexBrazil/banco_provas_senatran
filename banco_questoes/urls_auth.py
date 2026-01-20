from __future__ import annotations

from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views

from . import views_auth


urlpatterns = [
    path("login/", views_auth.EmailLoginView.as_view(), name="login"),
    path("logout/", views_auth.EmailLogoutView.as_view(), name="logout"),
    path("registrar/", views_auth.registrar, name="register"),
    path(
        "senha/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "senha/reset/feito/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "senha/reset/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "senha/reset/completo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
