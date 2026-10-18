"""PDF formal de una cotización (RQ02 para el equipo, RQ11 para el cliente)."""

from datetime import timedelta
from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL = colors.HexColor("#2563eb")
GRIS = colors.HexColor("#6b7280")
LINEA = colors.HexColor("#e5e7eb")
FONDO = colors.HexColor("#f3f4f6")
VALIDEZ_DIAS = 15


def pesos(valor):
    """4200 -> "$4.200" (separador de miles chileno, sin decimales)."""
    return "$" + f"{round(valor):,}".replace(",", ".")


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontSize=20, leading=24, alignment=0, spaceAfter=2),
        "normal": ParagraphStyle("normal", parent=base["Normal"], fontSize=9.5, leading=13),
        "chico": ParagraphStyle("chico", parent=base["Normal"], fontSize=8.5, leading=11, textColor=GRIS),
        "seccion": ParagraphStyle("seccion", parent=base["Heading3"], fontSize=11, spaceBefore=10, spaceAfter=4),
        "derecha": ParagraphStyle("derecha", parent=base["Normal"], fontSize=9.5, leading=13, alignment=TA_RIGHT),
    }


def generar_pdf(cot):
    """Devuelve los bytes del PDF de la cotización `cot` (con items y servicios)."""
    e = _estilos()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Cotización {cot.numero}", author="SpaceWise",
    )
    ancho = doc.width
    partes = []

    # Encabezado: empresa a la izquierda, número y fechas a la derecha
    emitida = timezone.localdate()
    encabezado = Table(
        [[
            [Paragraph("<font color='#2563eb'><b>SpaceWise</b></font>", e["titulo"]),
             Paragraph("Venta y arriendo de contenedores", e["chico"])],
            [Paragraph(f"<b>COTIZACIÓN {cot.numero}</b>", e["derecha"]),
             Paragraph(f"Fecha: {cot.fecha:%d/%m/%Y}", e["derecha"]),
             Paragraph(f"Emitido: {emitida:%d/%m/%Y}", e["derecha"]),
             Paragraph(f"Estado: {cot.get_estado_display()}", e["derecha"])],
        ]],
        colWidths=[ancho * 0.6, ancho * 0.4],
    )
    encabezado.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, AZUL),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    partes += [encabezado, Spacer(1, 8)]

    # Cliente
    c = cot.cliente
    datos_cliente = [f"<b>{c.nombre}</b>"]
    if c.razon_social:
        datos_cliente.append(c.razon_social)
    datos_cliente.append("RUT: " + (c.rut or "—"))
    contacto = " · ".join(x for x in [c.email, c.telefono] if x)
    if contacto:
        datos_cliente.append(contacto)
    entrega = cot.direccion_entrega or c.direccion
    if entrega:
        datos_cliente.append(f"Entrega: {entrega}")
    if cot.fecha_requerida:
        datos_cliente.append(f"Fecha requerida: {cot.fecha_requerida:%d/%m/%Y}")
    partes += [Paragraph("Cliente", e["seccion"]), Paragraph("<br/>".join(datos_cliente), e["normal"])]

    # Detalle: contenedores y servicios en una sola tabla
    filas = [["Descripción", "Cant.", "Precio unit.", "Subtotal"]]
    for i in cot.items.all():
        filas.append([
            Paragraph(f"{i.contenedor.nombre}<br/><font size=8 color='#6b7280'>{i.contenedor.get_tipo_display()} · "
                      f"{i.contenedor.get_condicion_display()}</font>", e["normal"]),
            i.cantidad, pesos(i.precio_unitario), pesos(i.subtotal),
        ])
    for s in cot.servicios.all():
        filas.append([
            Paragraph(f"{s.servicio.nombre}<br/><font size=8 color='#6b7280'>Servicio · por {s.servicio.unidad}</font>",
                      e["normal"]),
            s.cantidad, pesos(s.precio_unitario), pesos(s.subtotal),
        ])
    filas.append(["", "", Paragraph("<b>Total</b>", e["derecha"]), Paragraph(f"<b>{pesos(cot.total)}</b>", e["derecha"])])

    detalle = Table(filas, colWidths=[ancho * 0.52, ancho * 0.1, ancho * 0.19, ancho * 0.19], repeatRows=1)
    detalle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, FONDO]),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINEA),
        ("LINEABOVE", (0, -1), (-1, -1), 1, AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    partes += [Paragraph("Detalle", e["seccion"]), detalle]

    if cot.notas:
        partes += [Paragraph("Observaciones", e["seccion"]),
                   Paragraph(cot.notas.replace("\n", "<br/>"), e["normal"])]

    # Condiciones
    vence = cot.fecha + timedelta(days=VALIDEZ_DIAS)
    vendedor = (cot.vendedor.user.get_full_name() or cot.vendedor.user.username) if cot.vendedor else None
    condiciones = [
        f"Cotización válida por {VALIDEZ_DIAS} días (hasta el {vence:%d/%m/%Y}), sujeta a disponibilidad de stock.",
        "Valores en pesos chilenos.",
    ]
    if vendedor:
        condiciones.append(f"Ejecutivo de venta: {vendedor}.")
    partes += [Spacer(1, 6), Paragraph("Condiciones", e["seccion"]),
               Paragraph("<br/>".join(condiciones), e["chico"])]

    doc.build(partes)
    return buffer.getvalue()


def respuesta_pdf(cot):
    """HttpResponse para descargar el PDF con un nombre de archivo claro."""
    resp = HttpResponse(generar_pdf(cot), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="cotizacion-{cot.numero}.pdf"'
    return resp
