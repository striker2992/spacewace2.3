from django.urls import path

from . import views_tienda as v

app_name = "tienda"

urlpatterns = [
    path("carrito/", v.CarritoView.as_view(), name="carrito"),
    path("carrito/agregar/<int:pk>/", v.agregar_al_carrito, name="agregar"),
    path("carrito/item/<int:pk>/actualizar/", v.actualizar_cantidad, name="actualizar"),
    path("carrito/item/<int:pk>/eliminar/", v.eliminar_item, name="eliminar_item"),
    path("carrito/checkout/", v.CheckoutView.as_view(), name="checkout"),
    path("pedidos/", v.MisPedidosView.as_view(), name="mis_pedidos"),
    path("pedidos/<int:pk>/", v.MiPedidoDetalleView.as_view(), name="detalle_pedido"),
    path("pedidos/<int:pk>/gracias/", v.ConfirmacionView.as_view(), name="confirmacion"),
    path("cotizaciones/", v.MisCotizacionesView.as_view(), name="mis_cotizaciones"),
    path("cotizaciones/solicitar/", v.solicitar_cotizacion, name="solicitar_cotizacion"),
    path("cotizaciones/<int:pk>/", v.MiCotizacionDetalleView.as_view(), name="detalle_cotizacion"),
    path("cotizaciones/<int:pk>/pdf/", v.mi_cotizacion_pdf, name="pdf_cotizacion"),
    path("cotizaciones/<int:pk>/enlace/", v.renovar_enlace, name="renovar_enlace"),
    path("cotizaciones/<int:pk>/comprar/", v.ComprarCotizacionView.as_view(), name="comprar_cotizacion"),
]
