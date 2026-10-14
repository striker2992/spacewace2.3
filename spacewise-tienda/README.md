# SpaceWise

Plataforma Django para gestionar clientes, cotizaciones, compras y contenedores.
(Resultado de unir los repos `wiseee` y `spacewiseTest`.)

## Puesta en marcha

```bash
python -m venv venv
venv\Scripts\activate        # Windows  (en Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt      # incluye Pillow (fotos de contenedores)

python manage.py migrate
python manage.py seed          # opcional: datos de demo + usuario admin / admin1234
python manage.py runserver
```

Abre http://127.0.0.1:8000/catalogo/ (público). Equipo interno: http://127.0.0.1:8000/accounts/login/ con `seed`: `admin` / `admin1234` (cámbiala).
Cliente de prueba para la tienda: `cliente` / `demo1234`.
Sin `seed`, crea tu usuario con `python manage.py createsuperuser`.

Por defecto usa **SQLite** (archivo `db.sqlite3`), así que no necesitas instalar nada más.

## Configuración (opcional)

Copia `.env.example` a `.env` y ajusta lo que necesites (clave secreta, DEBUG, hosts, base de datos).
El archivo `.env` está en `.gitignore`: **nunca subas contraseñas al repositorio**.

### Usar MySQL en vez de SQLite

1. Crea la base: `CREATE DATABASE spacewise CHARACTER SET utf8mb4;`
2. `pip install -r requirements/mysql.txt`
3. En `.env`: `DB_ENGINE=mysql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
4. `python manage.py migrate`

## Módulos

| Ruta             | Qué hace                                                             |
|------------------|----------------------------------------------------------------------|
| `/`              | Dashboard con totales, resumen de cotizaciones y últimas solicitudes |
| `/clientes/`     | CRUD + detalle con historial y actividad                             |
| `/cotizaciones/` | Cotizaciones con varios contenedores; aprobar/rechazar               |
| `/catalogo/`     | **Público.** Tarjetas con filtros (tipo, tamaño, estado, precio, stock) y botón **Agregar al carrito**; `/catalogo/<id>/` es la ficha |
| `/carrito/`      | **Público.** Carrito en sesión; al iniciar sesión se fusiona con el del usuario |
| `/carrito/checkout/` | Requiere login (`/accounts/login/?next=...`). Confirma entrega/contacto y crea el pedido |
| `/pedidos/`      | Historial de pedidos del cliente |
| `/accounts/registro/` | Crear cuenta de cliente (User + perfil con RUT, teléfono, empresa, dirección) |
| `/vendedores/pedidos/` | Panel interno: revisar pedidos web y cambiar su estado |
| `/compras/`      | Ventas, compras y devoluciones                                       |
| `/contenedores/` | Administración de contenedores (precio, stock, ubicación)            |
| `/vendedores/`   | Equipo comercial (cada vendedor es un usuario)                       |
| `/admin/`        | Panel de administración de Django                                    |

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
wiseee/
├── manage.py
├── requirements.txt          # atajo a requirements/base.txt
├── requirements/
│   ├── base.txt              # dependencias mínimas (Django)
│   └── mysql.txt             # extra opcional para MySQL
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
└── docs/legacy_spacewiseTest/  # esquema SQL original (solo referencia)
```
