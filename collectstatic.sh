#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Create static directories if they don't exist
mkdir -p static
mkdir -p staticfiles

# Remove existing static files
echo "Cleaning existing static files..."
rm -rf staticfiles/*

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear --verbosity 2

# Set proper permissions
echo "Setting permissions..."
chmod -R 755 staticfiles
chmod -R 755 static

# Start the server with static files serving enabled
echo "Starting server..."
python manage.py runserver 0.0.0.0:8000 --insecure 