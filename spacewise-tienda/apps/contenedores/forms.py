from django import forms

from .models import Contenedor, Servicio


class ContenedorForm(forms.ModelForm):
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


class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ["nombre", "precio", "unidad", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}
