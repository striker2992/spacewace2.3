from decimal import Decimal
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.core.validators import (
    ValidacionMixin,
    validar_fecha_no_pasada,
    validar_fecha_sensata,
    validar_nombre_persona,
    validar_rut,
    validar_telefono,
    validar_texto,
    validar_texto_multilinea,
)

from .models import Cotizacion, CotizacionItem, CotizacionServicio, Pedido


class CotizacionForm(ValidacionMixin, forms.ModelForm):
    validaciones = {
        "fecha": validar_fecha_sensata,
        "notas": validar_texto_multilinea,
    }

    class Meta:
        model = Cotizacion
        fields = ["cliente", "fecha", "notas"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={"rows": 3, "maxlength": "2000"}),
        }


class CotizacionItemForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    cantidad = forms.IntegerField(
        min_value=1,
        max_value=10000,
        initial=1,
        widget=forms.NumberInput(attrs={"min": "1", "max": "10000", "step": "1", "data-filtro": "entero"}),
    )
    precio_unitario = forms.DecimalField(
        required=False, min_value=0, max_value=Decimal("999999999.99"), max_digits=12, decimal_places=2
    )

    class Meta:
        model = CotizacionItem
        fields = ["contenedor", "cantidad", "precio_unitario"]

    def clean(self):
        cleaned = super().clean()
        contenedor = cleaned.get("contenedor")
        if contenedor and cleaned.get("precio_unitario") in (None, ""):
            cleaned["precio_unitario"] = contenedor.precio
        return cleaned


class BaseCotizacionItemFormSet(BaseInlineFormSet):
    """Evita duplicar el mismo contenedor en múltiples filas de la cotización."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        contenedores = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            c = form.cleaned_data.get("contenedor")
            if c:
                if c.pk in contenedores:
                    raise forms.ValidationError(
                        f"El contenedor «{c.nombre}» está repetido en más de una fila. Ajusta la cantidad en una sola fila."
                    )
                contenedores.add(c.pk)


ItemFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=CotizacionItemForm,
    formset=BaseCotizacionItemFormSet,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)


class CotizacionServicioForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    cantidad = forms.IntegerField(
        min_value=1,
        max_value=10000,
        initial=1,
        widget=forms.NumberInput(attrs={"min": "1", "max": "10000", "step": "1", "data-filtro": "entero"}),
    )
    precio_unitario = forms.DecimalField(
        required=False, min_value=0, max_value=Decimal("999999999.99"), max_digits=12, decimal_places=2
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


class BaseCotizacionServicioFormSet(BaseInlineFormSet):
    """Evita duplicar el mismo servicio en múltiples filas."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        servicios = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            s = form.cleaned_data.get("servicio")
            if s:
                if s.pk in servicios:
                    raise forms.ValidationError(
                        f"El servicio «{s.nombre}» está repetido. Ajusta la cantidad en una sola fila."
                    )
                servicios.add(s.pk)


ServicioFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionServicio,
    form=CotizacionServicioForm,
    formset=BaseCotizacionServicioFormSet,
    extra=0,
    can_delete=True,
)


# ---------------------------------------------------------------------------
# Solicitud de cotización hecha por el cliente desde la tienda (sin precios:
# se toman del catálogo como referencia y el equipo los confirma al valorizar)
# ---------------------------------------------------------------------------
class SolicitudForm(ValidacionMixin, forms.ModelForm):
    validaciones = {
        "fecha_requerida": validar_fecha_no_pasada,
        "direccion_entrega": validar_texto,
        "notas": validar_texto_multilinea,
    }

    direccion_entrega = forms.CharField(
        label="Dirección de entrega",
        min_length=5,
        max_length=255,
        required=False,
    )

    class Meta:
        model = Cotizacion
        fields = ["fecha_requerida", "direccion_entrega", "notas"]
        labels = {"notas": "Comentarios o requerimientos"}
        widgets = {
            "fecha_requerida": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(attrs={
                "rows": 3,
                "maxlength": "1000",
                "placeholder": "Uso que le darás, modificaciones, acceso al terreno, etc.",
            }),
        }


class SolicitudItemForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    cantidad = forms.IntegerField(
        min_value=1,
        max_value=1000,
        initial=1,
        widget=forms.NumberInput(attrs={"min": "1", "max": "1000", "step": "1", "data-filtro": "entero"}),
    )

    class Meta:
        model = CotizacionItem
        fields = ["contenedor", "cantidad"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contenedor"].queryset = self.fields["contenedor"].queryset.filter(activo=True)


class BaseSolicitudItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        contenedores = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            c = form.cleaned_data.get("contenedor")
            if c:
                if c.pk in contenedores:
                    raise forms.ValidationError(
                        f"El contenedor «{c.nombre}» está repetido en tu solicitud. Por favor ajusta la cantidad en una sola fila."
                    )
                contenedores.add(c.pk)


class SolicitudServicioForm(ValidacionMixin, forms.ModelForm):
    filtros = {"cantidad": "cantidad"}

    cantidad = forms.IntegerField(
        min_value=1,
        max_value=1000,
        initial=1,
        widget=forms.NumberInput(attrs={"min": "1", "max": "1000", "step": "1", "data-filtro": "entero"}),
    )

    class Meta:
        model = CotizacionServicio
        fields = ["servicio", "cantidad"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["servicio"].queryset = self.fields["servicio"].queryset.filter(activo=True)


class BaseSolicitudServicioFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        servicios = set()
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            s = form.cleaned_data.get("servicio")
            if s:
                if s.pk in servicios:
                    raise forms.ValidationError(
                        f"El servicio «{s.nombre}» está repetido en tu solicitud. Ajusta la cantidad en una sola fila."
                    )
                servicios.add(s.pk)


SolicitudItemFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionItem,
    form=SolicitudItemForm,
    formset=BaseSolicitudItemFormSet,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=False,
)
SolicitudServicioFormSet = inlineformset_factory(
    Cotizacion,
    CotizacionServicio,
    form=SolicitudServicioForm,
    formset=BaseSolicitudServicioFormSet,
    extra=0,
    can_delete=False,
)


class CheckoutForm(ValidacionMixin, forms.Form):
    """Confirmación de compra: entrega, contacto y datos de facturación del cliente."""

    validaciones = {
        "nombre": validar_nombre_persona,
        "rut": validar_rut,
        "razon_social": validar_texto,
        "direccion_entrega": validar_texto,
        "telefono_contacto": validar_telefono,
        "notas": validar_texto_multilinea,
    }
    filtros = {"nombre": "letras", "rut": "rut", "telefono_contacto": "telefono"}

    nombre = forms.CharField(label="Nombre del contacto", min_length=2, max_length=150)
    rut = forms.CharField(label="RUT", max_length=20)
    razon_social = forms.CharField(label="Empresa / Razón social", max_length=150, required=False)
    direccion_entrega = forms.CharField(label="Dirección de entrega", min_length=5, max_length=255)
    telefono_contacto = forms.CharField(label="Teléfono de contacto", max_length=30)
    metodo_contacto = forms.ChoiceField(
        label="¿Cómo prefieres que te contactemos?", choices=Pedido.MetodoContacto.choices
    )
    notas = forms.CharField(
        label="Notas para el pedido",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": "1000"}),
    )
