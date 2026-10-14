from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import Cliente

User = get_user_model()


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nombre", "rut", "razon_social", "email", "telefono", "direccion", "informacion_general",
        ]
        widgets = {"informacion_general": forms.Textarea(attrs={"rows": 4})}


class RegistroForm(UserCreationForm):
    """Crea el User y su perfil Cliente (RUT, teléfono, empresa, dirección) en un solo paso."""

    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Correo")
    rut = forms.CharField(label="RUT", max_length=20)
    telefono = forms.CharField(label="Teléfono", max_length=30)
    razon_social = forms.CharField(label="Empresa / Razón social", max_length=150, required=False)
    direccion = forms.CharField(label="Dirección de entrega", max_length=255, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")

    field_order = [
        "username", "first_name", "last_name", "email", "rut", "telefono",
        "razon_social", "direccion", "password1", "password2",
    ]

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=True)
        d = self.cleaned_data
        Cliente.objects.create(
            usuario=user,
            nombre=user.get_full_name(),
            rut=d["rut"],
            razon_social=d.get("razon_social", ""),
            email=user.email,
            telefono=d["telefono"],
            direccion=d.get("direccion", ""),
        )
        return user
