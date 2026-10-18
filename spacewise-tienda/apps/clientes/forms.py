from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from apps.core.validators import ValidacionMixin, validar_nombre_persona, validar_rut, validar_telefono, validar_texto

from .models import Cliente

User = get_user_model()


def correo_disponible(email, excepto=None):
    """Normaliza el correo y valida que ninguna otra cuenta lo use (es el dato para iniciar sesión)."""
    email = email.strip().lower()
    otros = User.objects.filter(email__iexact=email) | User.objects.filter(username__iexact=email)
    if excepto is not None:
        otros = otros.exclude(pk=excepto.pk)
    if otros.exists():
        raise forms.ValidationError("Ya existe una cuenta con ese correo.")
    return email


class ClienteForm(ValidacionMixin, forms.ModelForm):
    """Ficha del cliente para el equipo interno. Opcionalmente crea su acceso a la tienda
    (usuario = correo) o le asigna una contraseña nueva."""

    validaciones = {
        "nombre": validar_texto, "rut": validar_rut, "razon_social": validar_texto,
        "telefono": validar_telefono, "direccion": validar_texto,
    }
    filtros = {"rut": "rut", "telefono": "telefono"}

    password1 = forms.CharField(
        label="Contraseña", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Repetir contraseña", required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = Cliente
        fields = [
            "nombre", "rut", "razon_social", "email", "telefono", "direccion", "informacion_general",
        ]
        widgets = {"informacion_general": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].max_length = 150  # cabe en User.username
        if self.instance.usuario_id:
            self.fields["password1"].label = "Nueva contraseña"
            self.fields["password1"].help_text = "Déjala en blanco para mantener la actual."
        else:
            self.fields["password1"].help_text = (
                "Opcional. Si la escribes, el cliente podrá entrar a la tienda con su correo y esta contraseña."
            )

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        email = cleaned.get("email")
        if not p1 and not p2:
            if email and self.instance.usuario_id:
                self._validar_correo(email)
            return cleaned
        if p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
            return cleaned
        if not email:
            self.add_error("email", "El correo es obligatorio para crear el acceso a la tienda.")
            return cleaned
        self._validar_correo(email)
        try:
            validate_password(p1, user=self.instance.usuario if self.instance.usuario_id else None)
        except forms.ValidationError as e:
            self.add_error("password1", e)
        return cleaned

    def _validar_correo(self, email):
        try:
            self.cleaned_data["email"] = correo_disponible(email, excepto=self.instance.usuario)
        except forms.ValidationError as e:
            self.add_error("email", e)

    @transaction.atomic
    def save(self, commit=True):
        cliente = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        usuario = cliente.usuario
        if usuario is None and password:
            usuario = User(username=cliente.email, email=cliente.email)
        if usuario is not None:
            # El correo es el dato de acceso: se mantiene igual en la cuenta.
            if cliente.email:
                # Si la cuenta usaba el correo como usuario, se actualiza junto con él.
                if usuario.pk is None or usuario.username.lower() == usuario.email.lower():
                    usuario.username = cliente.email
                usuario.email = cliente.email
            if password:
                usuario.set_password(password)
            usuario.save()
            cliente.usuario = usuario
        cliente.save()
        return cliente


class RegistroForm(ValidacionMixin, UserCreationForm):
    """Crea el User y su perfil Cliente (RUT, teléfono, empresa, dirección) en un solo paso."""

    validaciones = {
        "first_name": validar_nombre_persona, "last_name": validar_nombre_persona, "rut": validar_rut,
        "telefono": validar_telefono, "razon_social": validar_texto, "direccion": validar_texto,
    }
    filtros = {"first_name": "letras", "last_name": "letras", "rut": "rut", "telefono": "telefono"}

    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Correo", max_length=150, help_text="Lo usarás para iniciar sesión.")
    rut = forms.CharField(label="RUT", max_length=20)
    telefono = forms.CharField(label="Teléfono", max_length=30)
    razon_social = forms.CharField(label="Empresa / Razón social", max_length=150, required=False)
    direccion = forms.CharField(label="Dirección de entrega", max_length=255, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email")

    field_order = [
        "email", "first_name", "last_name", "rut", "telefono",
        "razon_social", "direccion", "password1", "password2",
    ]

    def clean_email(self):
        return correo_disponible(self.cleaned_data["email"])

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email  # se inicia sesión con el correo
        user.save()
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
