#!/bin/sh
set -e

if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres..."
    python << END
import socket
import time
import os

host = os.environ.get('SQL_HOST', 'localhost')
port = int(os.environ.get('SQL_PORT', 5432))

while True:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            break
    except:
        pass
    time.sleep(0.1)
END
    echo "PostgreSQL started"
fi

echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"