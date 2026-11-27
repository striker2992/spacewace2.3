"""Validaciones de los datos que se ingresan en los formularios.

Cada función recibe el valor ya limpio por Django y lanza ValidationError con un
mensaje para el usuario. Las que normalizan (RUT, teléfono) devuelven el valor
en su formato estándar.
"""

import os
import re
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

# Letras con tildes y ñ, para nombres de personas
_LETRAS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
_RE_NOMBRE_PERSONA = re.compile(rf"^[{_LETRAS}]+(?:[ '\-.][{_LETRAS}]+)*\.?$")
# Nombres de empresas, contenedores, direcciones: letras, números y signos comunes
_RE_TEXTO = re.compile(rf"^[{_LETRAS}0-9 .,:;'’\"&()/#°º\-+]+$")
_RE_SOLO_LETRAS = re.compile(rf"^[{_LETRAS} ]+$")
_RE_HTML_TAGS = re.compile(r"<\s*[^>]+>")
_RE_DANGEROUS_TOKENS = re.compile(r"(?i)(javascript\s*:|onload\s*=|onerror\s*=|onclick\s*=|script|iframe|object|embed)")


def validar_nombre_persona(valor):
    """Solo letras, espacios, guion, apóstrofo y punto (ej.: María José, O'Higgins)."""
    valor = " ".join(valor.split())
    if not _RE_NOMBRE_PERSONA.match(valor):
        raise ValidationError("Usa solo letras (sin números ni símbolos).")
    return valor


def validar_texto(valor):
    """Texto de una línea: letras, números y signos de puntuación comunes; al menos una letra."""
    valor = " ".join(valor.split())
    if not _RE_TEXTO.match(valor):
        raise ValidationError("Contiene caracteres no permitidos (por ejemplo < > { } $ % * = @).")
    if not re.search(rf"[{_LETRAS}]", valor):
        raise ValidationError("Debe incluir letras, no solo números o símbolos.")
    return valor


def validar_solo_letras(valor):
    valor = " ".join(valor.split())
    if not _RE_SOLO_LETRAS.match(valor):
        raise ValidationError("Usa solo letras.")
    return valor


def _digito_verificador(cuerpo):
    suma, factor = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


def validar_rut(valor):
    """RUT chileno con dígito verificador. Devuelve el formato 12.345.678-5."""
    limpio = re.sub(r"[.\-\s]", "", valor).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise ValidationError("Ingresa un RUT válido, por ejemplo 12.345.678-5.")
    cuerpo, dv = limpio[:-1], limpio[-1]
    if _digito_verificador(cuerpo) != dv:
        raise ValidationError("El RUT no es válido: el dígito verificador no coincide.")
    return f"{int(cuerpo):,}".replace(",", ".") + f"-{dv}"


def validar_telefono(valor):
    """Solo números, con + inicial opcional y espacios. Entre 8 y 12 dígitos."""
    valor = " ".join(valor.split())
    if not re.fullmatch(r"\+?[0-9 ]+", valor):
        raise ValidationError("Usa solo números (puede empezar con +), por ejemplo +56 9 1234 5678.")
    digitos = re.sub(r"\D", "", valor)
    if not 8 <= len(digitos) <= 12:
        raise ValidationError("El teléfono debe tener entre 8 y 12 dígitos.")
    return valor


def validar_texto_multilinea(valor):
    """Texto multilínea seguro (notas, motivo, resolución, especificaciones).
    Permite saltos de línea y signos de puntuación, pero rechaza etiquetas HTML y scripts.
    """
    if not valor:
        return valor
    texto = valor.replace("\r\n", "\n").replace("\r", "\n").strip()
    if _RE_HTML_TAGS.search(texto) or _RE_DANGEROUS_TOKENS.search(texto) or "<" in texto or ">" in texto:
        raise ValidationError("No se permiten etiquetas HTML ni scripts en el texto.")
    if not re.search(rf"[{_LETRAS}0-9]", texto):
        raise ValidationError("El texto debe contener información legible.")
    return texto


def validar_fecha_no_pasada(valor, max_dias=730):
    if valor:
        hoy = timezone.localdate()
        if valor < hoy:
            raise ValidationError("La fecha no puede ser anterior a hoy.")
        if valor > hoy + timedelta(days=max_dias):
            raise ValidationError(f"La fecha no puede ser superior a {max_dias // 365} años en el futuro.")
    return valor


def validar_fecha_sensata(valor):
    """Valida que una fecha esté en un rango comercial razonable (entre 2020 y hoy + 2 años)."""
    if valor:
        hoy = timezone.localdate()
        if valor.year < 2020:
            raise ValidationError("El año no puede ser anterior a 2020.")
        if valor > hoy + timedelta(days=730):
            raise ValidationError("La fecha no puede ser superior a 2 años en el futuro.")
    return valor


def validar_imagen_archivo(archivo):
    """Valida tamaño máximo (5MB) y extensión permitida para subida de imágenes."""
    if not archivo:
        return archivo
    max_mb = 5
    if hasattr(archivo, "size") and archivo.size > max_mb * 1024 * 1024:
        raise ValidationError(f"La imagen no puede pesar más de {max_mb} MB.")
    if hasattr(archivo, "name"):
        ext = os.path.splitext(archivo.name)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise ValidationError("Formato no compatible. Usa JPG, PNG o WEBP.")
    return archivo


def validar_cantidad(valor):
    try:
        val = int(valor)
        if not (1 <= val <= 10000):
            raise ValidationError("La cantidad debe estar entre 1 y 10.000.")
        return val
    except (ValueError, TypeError):
        raise ValidationError("Ingresa una cantidad entera válida.")


def validar_precio(valor):
    try:
        val = Decimal(str(valor))
        if val < 0 or val > Decimal("999999999.99"):
            raise ValidationError("El precio debe ser mayor o igual a 0 y menor a 1.000 millones.")
        return val
    except Exception:
        raise ValidationError("Ingresa un precio válido.")


# ---------------------------------------------------------------------------
# Atributos HTML: el navegador también impide escribir lo que no corresponde
# ---------------------------------------------------------------------------
FILTROS = {
    "rut": {"data-filtro": "rut", "inputmode": "text", "maxlength": "12", "placeholder": "12.345.678-5"},
    "telefono": {"data-filtro": "telefono", "inputmode": "tel", "maxlength": "16", "placeholder": "+56 9 1234 5678"},
    "letras": {"data-filtro": "letras"},
    "positivo": {"min": "1"},  # precios: mayor que cero
    "cantidad": {"min": "1"},
}


def configurar_campos(form, **tipos):
    """Aplica límites a los campos numéricos y filtros de escritura a los de texto.

    Uso: configurar_campos(self, rut="rut", telefono="telefono", first_name="letras", precio="positivo")
    Los IntegerField y DecimalField quedan con mínimo, paso entero y sin letras.
    """
    for nombre, campo in form.fields.items():
        attrs = campo.widget.attrs
        if isinstance(campo, (forms.IntegerField, forms.DecimalField)):
            minimo = campo.min_value if campo.min_value is not None else 0
            attrs.setdefault("min", str(minimo))
            attrs["step"] = "1"
            attrs["inputmode"] = "numeric"
            attrs["data-filtro"] = "entero"
        if nombre in tipos:
            attrs.update(FILTROS[tipos[nombre]])



class ValidacionMixin:
    """Mixin para formularios: valida y normaliza campos, y configura el HTML.

    - `validaciones`: {campo: función} que se aplican si el campo trae un valor.
    - `filtros`: {campo: tipo} de FILTROS para limitar lo que se puede escribir.
    Los campos numéricos se configuran solos (sin negativos ni letras).
    Va antes de forms.Form / forms.ModelForm en la herencia.
    """

    validaciones = {}
    filtros = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configurar_campos(self, **self.filtros)

    def clean(self):
        cleaned = super().clean()
        for campo, funcion in self.validaciones.items():
            valor = cleaned.get(campo)
            if valor in (None, ""):
                continue
            try:
                cleaned[campo] = funcion(valor)
            except ValidationError as e:
                self.add_error(campo, e)
        return cleaned
