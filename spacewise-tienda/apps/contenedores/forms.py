from django import forms

from .models import Contenedor


class ContenedorForm(forms.ModelForm):
    class Meta:
        model = Contenedor
        fields = [
            "nombre", "tipo", "condicion", "precio", "stock", "ubicacion",
            "descripcion", "especificaciones", "imagen", "activo",
        ]
        labels = {"condicion": "Estado", "activo": "Visible en el catálogo"}
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "especificaciones": forms.Textarea(attrs={"rows": 4}),
        }
