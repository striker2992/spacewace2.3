from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.clientes.views import RegistroView
from apps.contenedores.views import CatalogoView, ContenedorDetalleView
from apps.core.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Cuentas
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/registro/", RegistroView.as_view(), name="registro"),
    # Catálogo público / Ruta principal
    path("", CatalogoView.as_view(), name="catalogo"),
    path("catalogo/<int:pk>/", ContenedorDetalleView.as_view(), name="detalle_contenedor"),
    # Tienda del cliente: /carrito/, /checkout/, /pedidos/
    path("", include("apps.cotizaciones.urls_tienda")),
    # URLs internas de contenedores si aplican
    path("contenedores/", include("apps.contenedores.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)