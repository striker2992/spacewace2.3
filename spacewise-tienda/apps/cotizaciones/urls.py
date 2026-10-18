from django.urls import path

from . import views

app_name = "cotizaciones"

urlpatterns = [
    path("", views.CotizacionLista.as_view(), name="lista"),
    path("nueva/", views.cotizacion_crear, name="crear"),
    path("<int:pk>/", views.CotizacionDetalle.as_view(), name="detalle"),
    path("<int:pk>/editar/", views.cotizacion_editar, name="editar"),
    path("<int:pk>/estado/", views.cotizacion_estado, name="estado"),
    path("<int:pk>/eliminar/", views.CotizacionEliminar.as_view(), name="eliminar"),
]
