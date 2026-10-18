from django.urls import path

from . import views

app_name = "contenedores"

# Administración interna. El catálogo público se monta en config/urls.py (/catalogo/).
urlpatterns = [
    path("", views.ContenedorLista.as_view(), name="lista"),
    path("nuevo/", views.ContenedorCrear.as_view(), name="crear"),
    path("<int:pk>/editar/", views.ContenedorEditar.as_view(), name="editar"),
    path("<int:pk>/eliminar/", views.ContenedorEliminar.as_view(), name="eliminar"),
    path("servicios/", views.ServicioLista.as_view(), name="servicio_lista"),
    path("servicios/nuevo/", views.ServicioCrear.as_view(), name="servicio_crear"),
    path("servicios/<int:pk>/editar/", views.ServicioEditar.as_view(), name="servicio_editar"),
    path("servicios/<int:pk>/eliminar/", views.ServicioEliminar.as_view(), name="servicio_eliminar"),
]
