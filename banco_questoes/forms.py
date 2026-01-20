from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class RegistroForm(UserCreationForm):
    username = forms.EmailField(label="Email")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def clean_username(self) -> str:
        email = (self.cleaned_data.get("username") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email obrigatorio.")
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email ja cadastrado.")
        return email

    def save(self, commit: bool = True):
        user = super().save(commit=False)
        email = (self.cleaned_data.get("username") or "").strip().lower()
        user.username = email
        user.email = email
        if commit:
            user.save()
        return user
