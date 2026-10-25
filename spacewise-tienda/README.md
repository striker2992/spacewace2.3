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
| `/cotizaciones/` | Cliente: historial de sus cotizaciones con su estado; `/cotizaciones/solicitar/` para pedir una nueva. Descarga el PDF y la **compra** (`/cotizaciones/<id>/comprar/`) con los precios valorizados cuando está aprobada |
| `/pedidos/<id>/garantia/` | Cliente: solicitar garantía de un pedido despachado o completado; `/garantias/` lista sus solicitudes y la resolución |
| `/c/<código>/` | **Público.** Enlace único para ver el estado y detalle de una cotización sin iniciar sesión (sin datos personales ni PDF). El cliente y el equipo lo copian o lo regeneran desde el detalle |
| `/accounts/registro/` | Crear cuenta de cliente (User + perfil con RUT, teléfono, empresa, dirección) |
| `/accounts/clave/olvide/` | Recuperar la contraseña con un enlace por correo |
| `/accounts/perfil/` | Mi perfil: editar datos de cuenta, contacto y facturación; `/accounts/perfil/clave/` cambia la contraseña |
| `/panel/`        | Panel del equipo interno: totales, resumen de cotizaciones y últimos pedidos |
| `/panel/contenedores/` | Agregar, editar y eliminar contenedores (precio, stock, foto, visibilidad) |
| `/panel/contenedores/servicios/` | Servicios adicionales (transporte, instalación, etc.) que se muestran en el catálogo y se agregan a las cotizaciones |
| `/panel/pedidos/` | Revisar pedidos web y cambiar su estado |
| `/panel/cotizaciones/` | Bandeja: solicitudes de clientes por valorizar y cotizaciones en curso; aprobar/rechazar y descargar el PDF formal |
| `/panel/garantias/` | Bandeja de garantías: revisar solicitudes y registrar la resolución (aprobada/rechazada) |
| `/panel/clientes/` | CRUD de clientes con su actividad |
| `/panel/reportes/` | Reporte mensual: ventas, cotizaciones procesadas, más vendidos/cotizados, clientes frecuentes y los últimos 12 meses; descarga en CSV (Excel) |
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
python manage.py test                 # todas (las de navegador se saltan si no hay Playwright)
python manage.py test --exclude-tag e2e   # solo las rápidas
```

Pruebas en navegador real (responsive, doble clic al pagar, dos clientes y la última unidad, XSS,
«Atrás» tras cerrar sesión). Son opcionales:

```bash
pip install playwright
playwright install chromium
python manage.py test --tag e2e
```

## Seguridad de las cuentas

- Tras **5 intentos fallidos** de inicio de sesión (por cuenta e IP) o 20 desde una misma IP, se bloquea
  por 15 minutos. El login de `/admin/` pasa por el mismo control.
- **¿Olvidaste tu contraseña?** envía un enlace válido por 2 horas y de un solo uso. En desarrollo el
  correo se muestra en la consola; para enviarlo de verdad configura `EMAIL_*` en `.env`.
- La sesión se cierra tras **8 horas sin actividad** (`DJANGO_SESSION_HORAS`).
- Con `DJANGO_DEBUG=0` el servidor no arranca si `DJANGO_SECRET_KEY` es la de ejemplo.
- Si alguien se registra con el correo de una ficha creada por el equipo, se le pide contactar al
  ejecutivo: el acceso se activa desde la ficha (así nadie toma una ficha ajena con solo saber el correo).
- Nota: el bloqueo de intentos se guarda en la memoria del proceso. Con varios procesos en producción,
  configura un caché compartido (`CACHES`).

## Despliegue (demo)

El proyecto ya trae lo necesario para producción: WhiteNoise sirve el CSS/JS, `gunicorn` como
servidor, HTTPS configurable y errores en los logs del hosting.

### Pasos para cualquier hosting

1. Crear la base MySQL (`utf8mb4`) y anotar host, nombre, usuario y clave.
2. Subir el código (clonar el repositorio) e instalar: `pip install -r requirements.txt`.
3. Crear el `.env` del servidor a partir de `.env.example` con, al menos:
   ```
   DJANGO_DEBUG=0
   DJANGO_SECRET_KEY=<generada, ver abajo>
   DJANGO_ALLOWED_HOSTS=<tu-dominio>
   DJANGO_HTTPS=1
   DJANGO_PROXY_SALTOS=1
   DB_NAME=... DB_USER=... DB_PASSWORD=... DB_HOST=... DB_PORT=3306
   ```
   Clave secreta: `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`
4. Preparar:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py seed --clave-equipo "<clave segura para admin y vendedores>"   # opcional: datos de demo
   python manage.py check --deploy
   ```
   `check --deploy` puede avisar de `SECURE_HSTS_INCLUDE_SUBDOMAINS` y `SECURE_HSTS_PRELOAD`: se dejan
   apagados a propósito (en dominios compartidos como `*.pythonanywhere.com` no corresponde activarlos).
5. Arrancar: `gunicorn config.wsgi` (ya está en el `Procfile`) o el servidor WSGI del hosting.
6. Probar: catálogo con estilos, fotos, iniciar sesión, una compra y el PDF.

Con `DJANGO_DEBUG=0` el servidor no arranca si falta una `DJANGO_SECRET_KEY` propia, y `seed` no corre
sin `--clave-equipo` (las claves de ejemplo están publicadas en este README). La cliente de demo
`camila@ejemplo.cl / demo1234` sí se crea, para mostrar la tienda.

### Según el hosting

- **PythonAnywhere**. Ojo: desde el 15-01-2026 las cuentas gratuitas **nuevas no incluyen MySQL**
  (lo tienen el plan Developer, 10 USD/mes, y las cuentas gratuitas creadas antes de esa fecha). Las web
  apps gratuitas vencen al mes si no se pulsa *Run until 1 month from today* en la pestaña *Web*.
  1. *Databases*: define la clave de MySQL y crea la base `spacewise`. En `.env`:
     `DB_HOST=<usuario>.mysql.pythonanywhere-services.com`, `DB_NAME=<usuario>$spacewise`, `DB_USER=<usuario>`.
     (Esa dirección solo funciona desde PythonAnywhere.)
  2. Consola Bash: `git clone` del repositorio, `mkvirtualenv --python=python3.12 spacewise` y
     `pip install -r requirements.txt` dentro de `spacewise-tienda`.
  3. `.env` con lo de arriba más `DJANGO_HTTPS=1`, `DJANGO_HTTPS_REDIRIGIR=0`, `DJANGO_IP_CABECERA=X-Real-IP`
     y `DJANGO_SERVIR_MEDIA=0`; luego `migrate`, `collectstatic` y `seed --clave-equipo ...`.
  4. *Web* → *Add a new web app* → *Manual configuration* (misma versión de Python). Virtualenv: el creado.
     En el archivo WSGI deja solo:
     ```python
     import os, sys
     sys.path.insert(0, "/home/<usuario>/spacewace2.3/spacewise-tienda")
     os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
     from django.core.wsgi import get_wsgi_application
     application = get_wsgi_application()
     ```
  5. *Static files*: `/static/` → `/home/<usuario>/spacewace2.3/spacewise-tienda/staticfiles` y
     `/media/` → `/home/<usuario>/spacewace2.3/spacewise-tienda/media`. Activa *Force HTTPS* y pulsa *Reload*.
  6. Correos: las cuentas gratuitas solo pueden usar el SMTP de Gmail (con clave de aplicación).
  No usa `gunicorn` ni el `Procfile`. Tras cada `git pull`: `migrate`, `collectstatic` y *Reload*.
- **Render / Railway**: directorio raíz `spacewise-tienda`, comando de build `./build.sh`, comando de
  inicio el del `Procfile`; las variables del `.env` van en el panel del servicio. MySQL va aparte
  (Railway lo ofrece; en Render hay que usar un MySQL externo). **Ojo:** su disco se borra en cada
  despliegue, así que las fotos subidas desde el panel se pierden; para una demo basta con volver a subirlas.

Antes de presentar: en otros hostings confirma cuántos proxies hay delante (`DJANGO_PROXY_SALTOS`,
casi siempre 1) y, si quieres que lleguen los correos de «¿Olvidaste tu contraseña?», configura `EMAIL_*`.

## Estructura

```
spacewise-tienda/
├── manage.py
├── requirements.txt          # atajo a requirements/base.txt
├── Procfile / build.sh       # despliegue (gunicorn, collectstatic, migrate)
├── requirements/
│   └── base.txt              # dependencias (Django, Pillow, reportlab, mysqlclient)
├── .env.example              # plantilla de configuración local
├── config/                   # settings, urls, wsgi
├── apps/                     # apps de Django (una por módulo)
│   ├── core/                 # dashboard, mixins, templatetags, comando `seed`
│   ├── clientes/
│   ├── contenedores/         # administración + catálogo
│   ├── cotizaciones/
│   ├── operaciones/          # postventa: garantías de los pedidos
│   └── vendedores/
├── templates/                # base.html + una carpeta por módulo
├── static/                   # css/ y js/
```
