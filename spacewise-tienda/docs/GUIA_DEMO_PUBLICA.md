# Guía: publicar SpaceWise desde tu PC (demo pública)

Esta guía deja SpaceWise funcionando en tu computador con Windows y lo publica en internet
con un túnel de Cloudflare (gratis, sin cuenta). Tu PC hace de servidor con tu propio MySQL:
el sitio funciona mientras el PC esté encendido y la ventana de la demo abierta.

---

## Parte 1 · Instalar los programas (una sola vez)

1. **Git:** <https://git-scm.com/download/win>
2. **Python 3.12 o superior:** <https://www.python.org/downloads/>
   (al instalar, marca **«Add python.exe to PATH»**).
3. **MySQL Server 8 + MySQL Workbench:** <https://dev.mysql.com/downloads/installer/>
   (anota la contraseña que le pongas a `root`).
4. **Cloudflare Tunnel.** En PowerShell:
   ```powershell
   winget install --id Cloudflare.cloudflared
   ```
   Luego **cierra PowerShell y ábrelo de nuevo**.

## Parte 2 · Preparar el proyecto (una sola vez)

5. **Clonar el proyecto**
   ```powershell
   cd $HOME\Desktop
   git clone https://github.com/striker2992/spacewace2.3
   cd spacewace2.3\spacewise-tienda
   ```

6. **Entorno virtual y dependencias**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   Si aparece *«la ejecución de scripts está deshabilitada»*: ejecuta
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, responde **S** y repite la segunda línea.

7. **Configuración**
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   Cambia `DB_PASSWORD=` por tu contraseña de MySQL, deja `DJANGO_DEBUG=1` y guarda.
   (Ojo: el Bloc de notas a veces lo guarda como `.env.txt`; revisa con `Get-ChildItem -Force .env*`.)

8. **Crear la base de datos.** En MySQL Workbench, conectado como `root`, ejecuta:
   ```sql
   CREATE DATABASE spacewise_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

9. **Crear las tablas y cargar los datos de demo**
   ```powershell
   python manage.py migrate
   python manage.py seed
   ```

10. **Cambiar las contraseñas del equipo** (obligatorio: las de ejemplo están publicadas en el
    README y, si no las cambias, el script no publica)
    ```powershell
    python manage.py changepassword admin
    python manage.py changepassword ana
    python manage.py changepassword luis
    python manage.py changepassword marta
    ```

## Parte 3 · Publicar (cada vez que quieras mostrarlo)

11. **Revisa la red.** Las redes de universidades y empresas suelen bloquear el túnel
    (puerto 7844). Si estás en una de ellas, **conecta el PC a la zona Wi-Fi de tu celular**.
12. Abre la carpeta `Desktop\spacewace2.3\spacewise-tienda` y haz **doble clic en
    `demo_publica.bat`**.
13. Espera hasta que aparezca:
    ```
    SpaceWise está publicado en:  https://palabras-al-azar.trycloudflare.com
    ```
    Esa es la dirección para compartir. **Deja la ventana abierta** mientras dure la demo.
    La dirección cambia cada vez que se abre el túnel.
14. **Prueba desde el celular con datos móviles** (sin Wi-Fi):
    - Tienda: `camila@ejemplo.cl` / `demo1234`
    - Panel: `admin` con la contraseña del paso 10
15. **Para apagar:** presiona **Ctrl + C** en la ventana negra y ciérrala.

## Las siguientes veces

```powershell
cd $HOME\Desktop\spacewace2.3\spacewise-tienda
.\venv\Scripts\Activate.ps1
git pull
pip install -r requirements.txt
python manage.py migrate
```
Luego, doble clic en `demo_publica.bat`.

## Qué hace `demo_publica.bat`

Activa el entorno virtual y ejecuta `demo_publica.py`, que:

1. Revisa que `cloudflared` esté instalado.
2. Aplica la configuración de producción **solo mientras corre** (tu `.env` no cambia).
3. Crea una clave secreta propia (`.demo_secret_key`, no se sube a GitHub).
4. Ejecuta `collectstatic` y `migrate`.
5. No publica si alguna cuenta del equipo sigue con una contraseña de ejemplo.
6. Levanta el servidor solo para tu PC (`127.0.0.1:8000`) y abre el túnel por HTTP/2.
7. Muestra la dirección pública y, si la red bloquea el túnel, te sugiere cambiar de red.
8. Con **Ctrl + C** apaga el túnel y el servidor.

Todo lo que hagan los visitantes (cuentas, cotizaciones, pedidos) queda en **tu** base MySQL.
Antes de presentar conviene respaldarla:
```powershell
mysqldump -u root -p spacewise_db > respaldo_antes_demo.sql
```

## Si algo falla

| Mensaje | Qué hacer |
|---|---|
| `No se encontró cloudflared` | Repite el paso 4 y abre una ventana nueva de PowerShell |
| `No se publica: estas cuentas del equipo usan una contraseña de ejemplo` | Ejecuta los `changepassword` que indica (paso 10) |
| `Esta red está bloqueando la conexión del túnel` | Conéctate a la zona Wi-Fi del celular y vuelve a abrir la demo |
| `Access denied for user 'root'` | Revisa `DB_PASSWORD` en el `.env` (y que no se llame `.env.txt`) |
| `Unknown database 'spacewise_db'` | Falta el paso 8 |
| `Tu cuenta está bloqueada por 15 minutos…` | Espera 15 minutos, o un administrador la libera en **Panel → Cuentas bloqueadas** (o `python manage.py desbloquear_cuenta admin`) |
| `Can't connect to MySQL server` | Inicia MySQL desde «Servicios» de Windows o desde Workbench |
| La ventana se cierra o no aparece la dirección | Haz una captura de lo que muestra y compártela con el equipo |

**Antes del día de la presentación**, haz una prueba completa en el mismo lugar y la misma red
donde vas a presentar.
