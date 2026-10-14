from django import forms
from django.forms import inlineformset_factory

from .models import Cotizacion, CotizacionItem, Pedido


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ["cliente", "fecha", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class CotizacionItemForm(forms.ModelForm):
    precio_unitario = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2
    )

    class Meta:
        model = CotizacionItem
        fields = ["contenedor", "cantidad", "precio_unitario"]

    def clean(self):
        cleaned = super().clean()
        contenedor = cleaned.get("contenedor")
        if contenedor and cleaned.get("precio_unitario") in (None, ""):
            # Si no se indica precio, se usa el precio de catálogo
            cleaned["precio_unitario"] = contenedor.precio
        return cleaned


ItemFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=CotizacionItemForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class CheckoutForm(forms.Form):
    """Confirmación de compra: entrega, contacto y datos de facturación del cliente."""

    nombre = forms.CharField(label="Nombre del contacto", max_length=150)
    rut = forms.CharField(label="RUT", max_length=20)
    razon_social = forms.CharField(label="Empresa / Razón social", max_length=150, required=False)
    direccion_entrega = forms.CharField(label="Dirección de entrega", max_length=255)
    telefono_contacto = forms.CharField(label="Teléfono de contacto", max_length=30)
    metodo_contacto = forms.ChoiceField(
        label="¿Cómo prefieres que te contactemos?", choices=Pedido.MetodoContacto.choices
    )
    notas = forms.CharField(
        label="Notas para el pedido", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
