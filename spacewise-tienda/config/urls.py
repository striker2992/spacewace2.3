from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.clientes.views import CambiarClaveView, PerfilView, RegistroView
from apps.contenedores.views import CatalogoView, ContenedorDetalleView
from apps.core.views import LoginView, dashboard, inicio

urlpatterns = [
    # Django Admin: no se enlaza desde ninguna pantalla; queda solo para mantenimiento.
    path("admin/", admin.site.urls),
    # Cuentas
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/registro/", RegistroView.as_view(), name="registro"),
    path("accounts/perfil/", PerfilView.as_view(), name="perfil"),
    path("accounts/perfil/clave/", CambiarClaveView.as_view(), name="cambiar_clave"),
    # Inicio: el equipo interno va al panel; el resto ve el catálogo
    path("", inicio, name="inicio"),
    path("catalogo/", CatalogoView.as_view(), name="catalogo"),
    path("catalogo/<int:pk>/", ContenedorDetalleView.as_view(), name="detalle_contenedor"),
    # Tienda del cliente: /carrito/, /checkout/, /pedidos/
    path("", include("apps.cotizaciones.urls_tienda")),
    # Panel del equipo interno (admins y vendedores)
    path("panel/", dashboard, name="dashboard"),
    path("panel/contenedores/", include("apps.contenedores.urls")),
    path("panel/clientes/", include("apps.clientes.urls")),
    path("panel/cotizaciones/", include("apps.cotizaciones.urls")),
    path("panel/", include("apps.vendedores.urls")),  # /panel/pedidos/
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
