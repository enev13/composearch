#!/bin/sh
set -e

# Effective-mode visibility: a deploy missing PRODUCTION=True is obvious in the logs
python3 manage.py shell -c "from django.conf import settings; print('Startup: PRODUCTION=%s DEBUG=%s DB=%s' % (settings.PRODUCTION, settings.DEBUG, settings.DATABASES['default']['ENGINE']))"

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

# Full reset is opt-in: data (stats, admin edits, users) survives restarts by default
if [ "${RESET_DB_ON_START:-false}" = "true" ]; then
  python3 manage.py flush --no-input
fi

# Seed fixtures only into an empty DB so existing distributors are never overwritten
python3 manage.py shell -c "import sys; from search.models import DistributorSourceModel; sys.exit(0 if DistributorSourceModel.objects.exists() else 1)" \
  || python3 manage.py loaddata distributors.json

# Create the admin superuser from DJANGO_SUPERUSER_* env vars, only when missing
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python3 manage.py shell -c "import os, sys; from django.contrib.auth import get_user_model; sys.exit(0 if get_user_model().objects.filter(username=os.environ['DJANGO_SUPERUSER_USERNAME']).exists() else 1)" \
    || python3 manage.py createsuperuser --noinput
fi

exec uvicorn composearch.asgi:application --host 0.0.0.0 --port "${PORT:-8000}" --timeout-graceful-shutdown 25