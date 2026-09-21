#!/bin/sh
set -e
PORT="${PORT:-8080}"
echo "Starting budget app on 0.0.0.0:${PORT}"

i=1
while [ "$i" -le 30 ]; do
  if python manage.py migrate --noinput; then
    break
  fi
  echo "Database not ready, retry $i/30..."
  i=$((i + 1))
  sleep 2
done

python manage.py collectstatic --noinput
exec gunicorn server.wsgi:application --bind "0.0.0.0:${PORT}" --workers 2 --timeout 120
