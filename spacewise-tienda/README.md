# SpaceWise

Plataforma Django para gestionar clientes, cotizaciones, compras y contenedores.
(Resultado de unir los repos `wiseee` y `spacewiseTest`.)

## Puesta en marcha

Requiere **MySQL** instalado y en ejecución.

```bash
python -m venv venv
venv\Scripts\activate        # Windows  (en Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt      # incluye Pillow (fotos) y mysqlclient

copy .env.example .env        # Linux/Mac: cp .env.example .env
# edita .env: DJANGO_SECRET_KEY y tus datos de MySQL (DB_USER, DB_PASSWORD...)

mysql -u root -p -e "CREATE DATABASE spacewise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
python manage.py migrate
python manage.py seed          # opcional: datos de demo + usuario admin / admin1234
python manage.py runserver
```

Abre http://127.0.0.1:8000/catalogo/ (público). Equipo interno: http://127.0.0.1:8000/accounts/login/ con `seed`: `admin` / `admin1234` (cámbiala).
Cliente de prueba para la tienda: `camila@ejemplo.cl` / `demo1234` (los clientes inician sesión con su correo).
Sin `seed`, crea tu usuario con `python manage.py createsuperuser`.

## Configuración (`.env`)

Toda la configuración local va en `.env` (plantilla: `.env.example`):

| Variable | Para qué |
|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta de Django |
| `DJANGO_DEBUG` | `1` en desarrollo, `0` en producción |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a MySQL |
| `PEDIDOS_NOTIFY_EMAILS` | Correos que reciben aviso de pedidos nuevos |

El archivo `.env` está en `.gitignore`: **nunca subas contraseñas al repositorio**.

## Módulos

| Ruta             | Qué hace                                                             |
|------------------|----------------------------------------------------------------------|
| `/`              | Clientes y visitas ven el catálogo; el equipo interno va al panel   |
| `/catalogo/`     | **Público.** Tarjetas con filtros y botón **Agregar al carrito**; `/catalogo/<id>/` es la ficha. El equipo interno ve **Cotizar** en vez de comprar |
| `/carrito/`      | **Público.** Carrito en sesión; al iniciar sesión se fusiona con el del usuario |
| `/carrito/checkout/` | Requiere login. Confirma entrega/contacto y crea el pedido |
| `/pedidos/`      | Historial de pedidos del cliente |
| `/cotizaciones/` | Cliente: historial de sus cotizaciones con su estado; `/cotizaciones/solicitar/` para pedir una nueva. Descarga el PDF cuando está aprobada |
| `/accounts/registro/` | Crear cuenta de cliente (User + perfil con RUT, teléfono, empresa, dirección) |
| `/panel/`        | Panel del equipo interno: totales, resumen de cotizaciones y últimos pedidos |
| `/panel/contenedores/` | Agregar, editar y eliminar contenedores (precio, stock, foto, visibilidad) |
| `/panel/contenedores/servicios/` | Servicios adicionales (transporte, instalación, etc.) que se muestran en el catálogo y se agregan a las cotizaciones |
| `/panel/pedidos/` | Revisar pedidos web y cambiar su estado |
| `/panel/cotizaciones/` | Bandeja: solicitudes de clientes por valorizar y cotizaciones en curso; aprobar/rechazar y descargar el PDF formal |
| `/panel/clientes/` | CRUD de clientes con su actividad |
| `/admin/`        | Django Admin: no se enlaza desde la app, solo para mantenimiento |

El equipo interno (admins y vendedores) **no puede comprar** en la tienda: carrito y checkout lo devuelven al panel.

### Pedidos de la tienda

Estados: `pendiente → en proceso → despachado → completado`, o `cancelado` (solo antes de despachar).
Al confirmar se descuenta el stock; al cancelar se devuelve. Los cambios de estado (panel interno y Django Admin)
pasan por `apps/cotizaciones/servicios.py`. Para recibir un correo por cada pedido nuevo define
`PEDIDOS_NOTIFY_EMAILS` en `.env`.

**Permisos:** solo el equipo interno (staff o vendedor activo) entra a clientes, cotizaciones, compras,
contenedores, vendedores y pedidos web. Los clientes registrados solo ven la tienda y sus propios pedidos.

Al **aprobar** una cotización se crea automáticamente una compra pendiente por cada contenedor cotizado.

## Pruebas

```bash
python manage.py test
```

## Estructura

```
spacewise-tienda/
├── manage.py
├── requirements.txt          # atajo a requirements/base.txt
├── requirements/
│   └── base.txt              # dependencias (Django, Pillow, reportlab, mysqlclient)
├── .env.example              # plantilla de configuración local
├── config/                   # settings, urls, wsgi
├── apps/                     # apps de Django (una por módulo)
│   ├── core/                 # dashboard, mixins, templatetags, comando `seed`
│   ├── clientes/
│   ├── contenedores/         # administración + catálogo
│   ├── cotizaciones/
│   ├── operaciones/          # compras, ventas y devoluciones
│   └── vendedores/
├── templates/                # base.html + una carpeta por módulo
├── static/                   # css/ y js/
```
