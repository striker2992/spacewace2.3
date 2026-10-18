from django.urls import path

from . import views

app_name = "vendedores"

urlpatterns = [
    path("pedidos/", views.PedidoLista.as_view(), name="pedidos"),
    path("pedidos/<int:pk>/", views.PedidoDetalle.as_view(), name="detalle_pedido"),
    path("pedidos/<int:pk>/estado/", views.pedido_cambiar_estado, name="pedido_estado"),
]
