# Guía de Despliegue con Docker en Ubuntu Server 22.04 LTS

Esta guía explica paso a paso cómo desplegar **SpaceWise** utilizando **Docker** y **Docker Compose** en un servidor limpio con **Ubuntu Server 22.04 LTS**.

---

## 1. Preparar el Servidor Ubuntu 22.04

Conéctate a tu servidor vía SSH:
```bash
ssh usuario@ip-del-servidor
```

Clona o sube el repositorio al servidor, por ejemplo en `/opt/spacewise`:
```bash
sudo mkdir -p /opt/spacewise
sudo chown -R $USER:$USER /opt/spacewise
git clone <URL_DE_TU_REPOSITORIO> /opt/spacewise/repo
cd /opt/spacewise/repo/spacewise-tienda
```

Ejecuta el script automático de preparación de Ubuntu 22.04 (instala Docker oficial, Docker Compose y configura el firewall UFW):
```bash
sudo bash deploy/preparar_ubuntu22.sh
```
> *Nota: Cierra la sesión SSH y vuelve a conectarte (o ejecuta `newgrp docker`) para que tu usuario ejecute `docker` sin `sudo`.*

---

## 2. Configurar Variables de Entorno

Dentro del directorio `spacewise-tienda/`, crea el archivo `.env` a partir de la plantilla:
```bash
cp .env.docker.example .env
nano .env
```

Configura principalmente:
- `DJANGO_SECRET_KEY`: Genera una clave aleatoria segura con:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
- `DJANGO_ALLOWED_HOSTS`: La IP pública o dominio de tu servidor (ej. `mi-tienda.com,192.168.1.50`).
- `DB_PASSWORD` y `DB_ROOT_PASSWORD`: Contraseñas seguras para la base de datos MySQL.
- `SEED_DATABASE=1`: Opcional, ponlo en `1` la primera vez si deseas cargar los datos de demostración y usuarios iniciales (`admin` / `admin1234`).

---

## 3. Construir y Levantar los Contenedores

Ejecuta Docker Compose:
```bash
docker compose up -d --build
```

El script de inicio (`entrypoint.sh`):
1. Espera a que el contenedor de MySQL esté completamente saludable y listo.
2. Corre las migraciones (`python manage.py migrate`).
3. Recolecta los archivos estáticos (`python manage.py collectstatic`).
4. Si `SEED_DATABASE=1`, carga los datos iniciales.
5. Inicia Gunicorn sirviendo la aplicación en el puerto `8000`.

Para revisar los logs en tiempo real:
```bash
docker compose logs -f
```

Para crear un superusuario manualmente (si no usaste el seed):
```bash
docker compose exec web python manage.py createsuperuser
```

---

## 4. Configurar Nginx y Certificado SSL (Recomendado para Producción)

Para servir la aplicación en el puerto 80/443 con certificado HTTPS (Let's Encrypt):

### A. Instalar Nginx y Certbot en Ubuntu:
```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### B. Activar el VirtualHost de SpaceWise:
```bash
sudo cp deploy/nginx-spacewise.conf /etc/nginx/sites-available/spacewise
```
Edita `/etc/nginx/sites-available/spacewise` y coloca tu dominio en la línea `server_name`.

Habilita el sitio:
```bash
sudo ln -s /etc/nginx/sites-available/spacewise /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### C. Generar Certificado SSL Gratuito:
```bash
sudo certbot --nginx -d tu-dominio.com -d www.tu-dominio.com
```

Luego de activar HTTPS, en tu archivo `.env`:
- Cambia `DJANGO_HTTPS=1`.
- Ejecuta `docker compose up -d` para aplicar los cambios.

---

## 5. Mantenimiento y Operaciones Frecuentes

### Actualizar a una nueva versión del código:
```bash
cd /opt/spacewise/repo/spacewise-tienda
git pull
docker compose up -d --build
```

### Respaldo de Base de Datos MySQL:
```bash
docker compose exec -T db mysqldump -u root -p"$DB_ROOT_PASSWORD" spacewise_db > backup_$(date +%F).sql
```

### Restaurar Respaldo de Base de Datos:
```bash
docker compose exec -T db mysql -u root -p"$DB_ROOT_PASSWORD" spacewise_db < backup.sql
```

### Detener los contenedores:
```bash
docker compose down
```
*(Los datos de MySQL y los archivos subidos en `media/` se mantendrán a salvo en los volúmenes persistentes de Docker).*
