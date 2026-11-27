from decimal import Decimal
from django import forms

from apps.core.validators import (
    ValidacionMixin,
    validar_imagen_archivo,
    validar_solo_letras,
    validar_texto,
    validar_texto_multilinea,
)

from .models import Contenedor, Servicio


class ContenedorForm(ValidacionMixin, forms.ModelForm):
    validaciones = {
        "nombre": validar_texto,
        "ubicacion": validar_texto,
        "descripcion": validar_texto_multilinea,
        "especificaciones": validar_texto_multilinea,
    }
    filtros = {"precio": "positivo"}

    precio = forms.DecimalField(
        min_value=1,
        max_value=Decimal("999999999.99"),
        decimal_places=2,
        label="Precio unitario",
        widget=forms.NumberInput(attrs={"min": "1", "step": "1", "data-filtro": "entero"}),
    )
    stock = forms.IntegerField(
        min_value=0,
        max_value=10000,
        label="Stock",
        widget=forms.NumberInput(attrs={"min": "0", "step": "1", "data-filtro": "entero"}),
    )

    class Meta:
        model = Contenedor
        fields = [
            "nombre", "tipo", "condicion", "estado", "precio", "stock", "ubicacion",
            "descripcion", "especificaciones", "imagen", "activo",
        ]
        labels = {"estado": "Disponibilidad", "activo": "Visible en el catálogo"}
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3, "maxlength": "2000"}),
            "especificaciones": forms.Textarea(attrs={"rows": 4, "maxlength": "3000"}),
        }

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if imagen:
            return validar_imagen_archivo(imagen)
        return imagen


class ServicioForm(ValidacionMixin, forms.ModelForm):
    validaciones = {
        "nombre": validar_texto,
        "unidad": validar_solo_letras,
        "descripcion": validar_texto_multilinea,
    }
    filtros = {"precio": "positivo", "unidad": "letras"}

    precio = forms.DecimalField(
        min_value=1,
        max_value=Decimal("999999999.99"),
        decimal_places=2,
        label="Precio referencial",
        widget=forms.NumberInput(attrs={"min": "1", "step": "1", "data-filtro": "entero"}),
    )

    class Meta:
        model = Servicio
        fields = ["nombre", "precio", "unidad", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3, "maxlength": "2000"})}
