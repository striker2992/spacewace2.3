from django import forms
from django.forms import inlineformset_factory

from apps.core.validators import (
    ValidacionMixin, validar_fecha_no_pasada, validar_nombre_persona, validar_rut, validar_telefono, validar_texto,
)

from .models import Cotizacion, CotizacionItem, CotizacionServicio, Pedido


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ["cliente", "fecha", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class CotizacionItemForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

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


class CotizacionServicioForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    precio_unitario = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2
    )

    class Meta:
        model = CotizacionServicio
        fields = ["servicio", "cantidad", "precio_unitario"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servicio"].queryset = self.fields["servicio"].queryset.filter(activo=True)

    def clean(self):
        cleaned = super().clean()
        servicio = cleaned.get("servicio")
        if servicio and cleaned.get("precio_unitario") in (None, ""):
            cleaned["precio_unitario"] = servicio.precio
        return cleaned


ServicioFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionServicio,
    form=CotizacionServicioForm,
    extra=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# Solicitud de cotización hecha por el cliente desde la tienda (sin precios:
# se toman del catálogo como referencia y el equipo los confirma al valorizar)
# ---------------------------------------------------------------------------
class SolicitudForm(ValidacionMixin, forms.ModelForm):
    validaciones = {"fecha_requerida": validar_fecha_no_pasada, "direccion_entrega": validar_texto}

    class Meta:
        model = Cotizacion
        fields = ["fecha_requerida", "direccion_entrega", "notas"]
        labels = {"notas": "Comentarios o requerimientos"}
        widgets = {
            "fecha_requerida": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={
                "rows": 3, "placeholder": "Uso que le darás, modificaciones, acceso al terreno, etc."
            }),
        }


class SolicitudItemForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    class Meta:
        model = CotizacionItem
        fields = ["contenedor", "cantidad"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contenedor"].queryset = self.fields["contenedor"].queryset.filter(activo=True)


class SolicitudServicioForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    class Meta:
        model = CotizacionServicio
        fields = ["servicio", "cantidad"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servicio"].queryset = self.fields["servicio"].queryset.filter(activo=True)


SolicitudItemFormSet = inlineformset_factory(
    Cotizacion, CotizacionItem, form=SolicitudItemForm,
    extra=0, min_num=1, validate_min=True, can_delete=False,
)
SolicitudServicioFormSet = inlineformset_factory(
    Cotizacion, CotizacionServicio, form=SolicitudServicioForm, extra=0, can_delete=False,
)


class CheckoutForm(ValidacionMixin, forms.Form):
    """Confirmación de compra: entrega, contacto y datos de facturación del cliente."""

    validaciones = {
        "nombre": validar_nombre_persona, "rut": validar_rut, "razon_social": validar_texto,
        "direccion_entrega": validar_texto, "telefono_contacto": validar_telefono,
    }
    filtros = {"nombre": "letras", "rut": "rut", "telefono_contacto": "telefono"}

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
