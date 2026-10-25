from django import forms

from apps.core.validators import ValidacionMixin, configurar_campos

from .models import Garantia


class SolicitudGarantiaForm(ValidacionMixin, forms.Form):
    """El cliente indica el motivo y cuántos contenedores de cada línea del pedido están afectados."""

    motivo = forms.CharField(
        label="¿Qué problema presenta?", min_length=10, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Ej.: filtración de agua en el techo del contenedor"}),
    )

    def __init__(self, *args, pedido, **kwargs):
        self.items = list(pedido.items.select_related("contenedor"))
        super().__init__(*args, **kwargs)
        for item in self.items:
            self.fields[self._campo(item)] = forms.IntegerField(
                label=item.contenedor.nombre, min_value=0, max_value=item.cantidad, initial=0, required=False,
                help_text=f"Compraste {item.cantidad}",
            )
        if len(self.items) == 1:  # con un solo contenedor se asume que es ese
            self.initial[self._campo(self.items[0])] = self.items[0].cantidad
        configurar_campos(self)  # los campos de cantidad se agregaron después del mixin

    @staticmethod
    def _campo(item):
        return f"cantidad_{item.pk}"

    def campos_cantidad(self):
        return [(item, self[self._campo(item)]) for item in self.items]

    def clean(self):
        cleaned = super().clean()
        if not any(cleaned.get(self._campo(i)) for i in self.items):
            raise forms.ValidationError("Indica al menos un contenedor afectado.")
        return cleaned

    def cantidades(self):
        return [(item, self.cleaned_data.get(self._campo(item)) or 0) for item in self.items]


class ResolverGarantiaForm(forms.Form):
    estado = forms.ChoiceField(
        label="Decisión", widget=forms.RadioSelect,
        choices=[(Garantia.Estado.APROBADA, "Aprobar"), (Garantia.Estado.RECHAZADA, "Rechazar")],
    )
    resolucion = forms.CharField(
        label="Resolución para el cliente", min_length=10, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Ej.: se coordinará una visita técnica el lunes"}),
    )
