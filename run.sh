#!/bin/sh
set -e

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput
python3 manage.py flush --no-input
python3 manage.py loaddata distributors.json
# Recreate the admin superuser (wiped by flush) when its credentials are configured
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python3 manage.py createsuperuser --noinput
fi
uvicorn composearch.asgi:application --host 0.0.0.0 --port "${PORT:-8000}"