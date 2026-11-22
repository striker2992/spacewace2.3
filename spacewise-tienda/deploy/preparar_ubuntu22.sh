#!/usr/bin/env bash
# ==============================================================================
# Script de preparación inicial para Ubuntu Server 22.04 LTS
# Instala Docker, Docker Compose Plugin, UFW y herramientas esenciales.
# Uso:
#   sudo bash deploy/preparar_ubuntu22.sh
# ==============================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Por favor ejecuta este script con permisos de superusuario (sudo):"
    echo "  sudo bash $0"
    exit 1
fi

echo "» Actualizando repositorios y paquetes del sistema..."
apt-get update -qq
apt-get upgrade -y -qq

echo "» Instalando paquetes base y dependencias de Docker..."
apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw \
    net-tools

# Configuración del repositorio oficial de Docker
echo "» Configurando clave GPG y repositorio oficial de Docker..."
mkdir -p /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "» Instalando Docker Engine y Docker Compose..."
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Habilitar e iniciar servicio Docker
systemctl enable --now docker

# Agregar el usuario que invocó sudo al grupo docker para usar docker sin sudo
USUARIO_ACTUAL="${SUDO_USER:-$USER}"
if [ "$USUARIO_ACTUAL" != "root" ]; then
    echo "» Agregando al usuario '$USUARIO_ACTUAL' al grupo docker..."
    usermod -aG docker "$USUARIO_ACTUAL"
fi

echo "» Configurando cortafuegos UFW básico..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo "========================================================================"
echo " Instalación completada exitosamente en Ubuntu 22.04"
echo " Docker: $(docker --version)"
echo " Docker Compose: $(docker compose version)"
echo ""
echo " Recuerda cerrar sesión y volver a entrar o ejecutar 'newgrp docker'"
echo " para usar Docker sin necesidad de 'sudo'."
echo "========================================================================"
