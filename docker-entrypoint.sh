#!/bin/bash

# Exit on error
set -e

# Wait for database
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is available!"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis is available!"

# Wait for Ollama
echo "Waiting for Ollama..."
while ! nc -z ollama 11434; do
  sleep 0.1
done
echo "Ollama is available!"

# Run migrations
echo "Running migrations..."
python manage.py migrate

# Create superuser if not exists
echo "Creating superuser if not exists..."
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# Run collectstatic script
echo "Running collectstatic script..."
/app/collectstatic.sh

# Start gunicorn
echo "Starting gunicorn..."
exec gunicorn itgrowsbot.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 60 