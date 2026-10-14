from django.urls import path

from . import views

app_name = "vendedores"

urlpatterns = [
    path("", views.VendedorLista.as_view(), name="lista"),
    path("nuevo/", views.VendedorCrear.as_view(), name="crear"),
    path("<int:pk>/editar/", views.VendedorEditar.as_view(), name="editar"),
    path("pedidos/", views.PedidoLista.as_view(), name="pedidos"),
    path("pedidos/<int:pk>/", views.PedidoDetalle.as_view(), name="detalle_pedido"),
    path("pedidos/<int:pk>/estado/", views.pedido_cambiar_estado, name="pedido_estado"),
]
