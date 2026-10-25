from django.urls import path

from . import views

app_name = "garantias"

urlpatterns = [
    # Cliente
    path("pedidos/<int:pk>/garantia/", views.solicitar, name="solicitar"),
    path("garantias/", views.MisGarantiasView.as_view(), name="mis_garantias"),
    path("garantias/<int:pk>/", views.MiGarantiaDetalleView.as_view(), name="mi_garantia"),
    # Equipo interno
    path("panel/garantias/", views.GarantiaLista.as_view(), name="lista"),
    path("panel/garantias/<int:pk>/", views.GarantiaDetalle.as_view(), name="detalle"),
    path("panel/garantias/<int:pk>/resolver/", views.resolver, name="resolver"),
]
