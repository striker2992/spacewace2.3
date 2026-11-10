# Guía: SpaceWise en un servidor del iLab (Proxmox)

El iLab del DEI entrega máquinas virtuales (VM) en un clúster Proxmox. Estas VM son
**desechables**: si algo sale mal se borran y se clonan de nuevo. Por eso la instalación de
SpaceWise es un único script que deja todo funcionando.

> El sitio queda visible **dentro de la red de la universidad** (eduroam / intranet), no desde
> internet. Se entra por `http://IP-de-la-VM/`.

---

## 1 · Crear la VM (una sola vez)

1. Entra al **Portal iLab** desde la intranet con tu cuenta iLab y luego al **Cluster iLab**,
   eligiendo en *Realm* tu laboratorio (**iLab-Bode**).
2. En **Pool View → Cloud_Templates**, clic derecho sobre **`t3.micro-noble`** (Ubuntu 24.04)
   → **Clone**. Si existe `t3.small-noble` (2 GB de RAM), mejor. Nombre único, por ejemplo
   `spacewise`; tipo **Linked Clone**.
3. Deja la VM **apagada**. En **Cloud-Init** pon tu usuario y una contraseña
   (**guárdala: no se puede recuperar**) y presiona **Regenerate Image**.
4. En **Hardware → Add → Network Device**, conéctala a la **VLAN 3031 (iLab-Bode)**.
5. **Enciéndela**, espera un minuto y **reiníciala** una vez.
6. Anota la **IP** que aparece en el resumen de la VM.

## 2 · Instalar SpaceWise (un comando)

Conéctate por SSH (o usa **Console** en Proxmox):
```bash
ssh tu-usuario@IP-de-la-VM
```
y ejecuta:
```bash
curl -fsSL https://raw.githubusercontent.com/striker2992/spacewace2.3/main/spacewise-tienda/deploy/instalar_servidor.sh -o instalar.sh
sudo bash instalar.sh
```
Tarda unos minutos. Al final muestra:
```
✓ SpaceWise está funcionando
  Dirección:  http://10.x.x.x/
  Equipo:     admin, ana, luis y marta  /  contraseña: ...
  Tienda:     camila@ejemplo.cl / demo1234
```
**Anota la contraseña del equipo** (también queda en `/root/spacewise_clave_equipo.txt`, solo
legible con `sudo`).

### Qué hace el script
1. Instala Python, MySQL, Nginx y lo necesario (si el proxy caché de `apt` del iLab falla, lo quita,
   como indica su guía).
2. Crea la base `spacewise_db` y un usuario de MySQL con contraseña aleatoria.
3. Descarga SpaceWise en `/opt/spacewise`, crea el entorno de Python e instala las dependencias.
4. Genera el `.env` de producción (clave secreta aleatoria, `DEBUG=0`, IP de la VM permitida).
5. Ejecuta las migraciones, prepara los archivos estáticos y carga los datos de demostración con una
   contraseña aleatoria para el equipo.
6. Deja SpaceWise como servicio (`spacewise`) que **arranca solo** al reiniciar la VM, detrás de
   Nginx en el puerto 80.
7. Comprueba que el sitio responda.

## 3 · Uso diario

| Para… | Comando (en la VM) |
|---|---|
| Actualizar a la última versión de GitHub | `sudo bash /opt/spacewise/repo/spacewise-tienda/deploy/instalar_servidor.sh` |
| Ver si está funcionando | `systemctl status spacewise` |
| Ver los registros / errores | `journalctl -u spacewise -f` |
| Reiniciar la aplicación | `sudo systemctl restart spacewise` |
| Cambiar una contraseña | `cd /opt/spacewise/repo/spacewise-tienda && sudo -u spacewise /opt/spacewise/venv/bin/python manage.py changepassword admin` |
| Desbloquear una cuenta | `… manage.py desbloquear_cuenta <usuario>` (mismo prefijo que la fila anterior) |
| Respaldar la base | `sudo mysqldump spacewise_db > respaldo.sql` |

Actualizar **no borra datos**: conserva la base, las fotos y el `.env`.

## 4 · Si algo falla

| Problema | Qué hacer |
|---|---|
| `apt-get update falló` | La VM no tiene salida a internet o la VLAN no es la correcta: revisa el paso 1.4 |
| `git clone` o `pip` fallan | La VM no llega a GitHub o a PyPI: consulta a sysadmin.dei@usm.cl |
| `SpaceWise no respondió` | `journalctl -u spacewise -n 50` y comparte el mensaje con el equipo |
| No abre desde tu notebook | Debes estar en **eduroam** o la red de la universidad; usa la IP con `http://` (no `https://`) |
| Se arruinó la configuración | La VM es desechable: bórrala, clónala de nuevo (paso 1) y vuelve a ejecutar el script |

Soporte del iLab: **sysadmin.dei@usm.cl**.
