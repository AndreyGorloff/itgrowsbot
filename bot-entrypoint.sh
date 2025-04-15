#!/bin/bash

# Wait for postgres
echo "Waiting for postgres..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Set up Django
export DJANGO_SETTINGS_MODULE=itgrowsbot.settings
export PYTHONPATH=/app

# Start bot
echo "Starting bot..."
exec "$@" 