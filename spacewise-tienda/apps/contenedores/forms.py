from django import forms

from apps.core.validators import ValidacionMixin, validar_solo_letras, validar_texto

from .models import Contenedor, Servicio


class ContenedorForm(ValidacionMixin, forms.ModelForm):
    validaciones = {"nombre": validar_texto, "ubicacion": validar_texto}
    filtros = {"precio": "positivo"}

    class Meta:
        model = Contenedor
        fields = [
            "nombre", "tipo", "condicion", "estado", "precio", "stock", "ubicacion",
            "descripcion", "especificaciones", "imagen", "activo",
        ]
        labels = {"estado": "Disponibilidad", "activo": "Visible en el catálogo"}
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "especificaciones": forms.Textarea(attrs={"rows": 4}),
        }


class ServicioForm(ValidacionMixin, forms.ModelForm):
    validaciones = {"nombre": validar_texto, "unidad": validar_solo_letras}
    filtros = {"precio": "positivo", "unidad": "letras"}

    class Meta:
        model = Servicio
        fields = ["nombre", "precio", "unidad", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}
