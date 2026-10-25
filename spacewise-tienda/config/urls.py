from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.clientes.views import CambiarClaveView, PerfilView, RegistroView
from apps.contenedores.views import CatalogoView, ContenedorDetalleView
from apps.cotizaciones.views_tienda import cotizacion_publica
from django.views.generic import RedirectView

from apps.core.views import LoginView, OlvideClaveView, dashboard, inicio, reporte_mensual

urlpatterns = [
    # Django Admin: no se enlaza desde ninguna pantalla; queda solo para mantenimiento.
    # Su login pasa por el nuestro, que tiene límite de intentos.
    path("admin/login/", RedirectView.as_view(url="/accounts/login/?next=/admin/", query_string=False)),
    path("admin/", admin.site.urls),
    # Cuentas
    path("accounts/login/", LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/registro/", RegistroView.as_view(), name="registro"),
    path("accounts/perfil/", PerfilView.as_view(), name="perfil"),
    path("accounts/perfil/clave/", CambiarClaveView.as_view(), name="cambiar_clave"),
    # ¿Olvidaste tu contraseña?
    path("accounts/clave/olvide/", OlvideClaveView.as_view(), name="olvide_clave"),
    path("accounts/clave/enviada/", auth_views.PasswordResetDoneView.as_view(), name="clave_enviada"),
    path(
        "accounts/clave/restablecer/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(success_url="/accounts/clave/lista/"),
        name="password_reset_confirm",
    ),
    path("accounts/clave/lista/", auth_views.PasswordResetCompleteView.as_view(), name="clave_lista"),
    # Inicio: el equipo interno va al panel; el resto ve el catálogo
    path("", inicio, name="inicio"),
    path("catalogo/", CatalogoView.as_view(), name="catalogo"),
    path("catalogo/<int:pk>/", ContenedorDetalleView.as_view(), name="detalle_contenedor"),
    # RQ05: enlace único de una cotización (sin iniciar sesión)
    path("c/<str:token>/", cotizacion_publica, name="cotizacion_publica"),
    # Tienda del cliente: /carrito/, /checkout/, /pedidos/
    path("", include("apps.cotizaciones.urls_tienda")),
    # Panel del equipo interno (admins y vendedores)
    path("panel/", dashboard, name="dashboard"),
    path("panel/reportes/", reporte_mensual, name="reportes"),
    path("panel/contenedores/", include("apps.contenedores.urls")),
    path("panel/clientes/", include("apps.clientes.urls")),
    path("panel/cotizaciones/", include("apps.cotizaciones.urls")),
    path("panel/", include("apps.vendedores.urls")),  # /panel/pedidos/
    path("", include("apps.operaciones.urls")),  # garantías (cliente y panel)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
