from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    path("", views.ClienteLista.as_view(), name="lista"),
    path("nuevo/", views.ClienteCrear.as_view(), name="crear"),
    path("<int:pk>/", views.ClienteDetalle.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.ClienteEditar.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.ClienteEliminar.as_view(), name="eliminar"),
]
