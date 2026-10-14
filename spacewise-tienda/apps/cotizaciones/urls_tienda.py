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
]
