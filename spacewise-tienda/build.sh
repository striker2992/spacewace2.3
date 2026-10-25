#!/usr/bin/env bash
# Paso de construcción para hostings como Render o Railway (desde la carpeta spacewise-tienda).
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
