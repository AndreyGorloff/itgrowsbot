#!/bin/bash

# Exit on error
set -e

echo "Running collectstatic..."
python manage.py collectstatic --noinput --clear --verbosity 2

echo "Setting permissions..."
chmod -R 755 /app/staticfiles || true
chmod -R 755 /app/static || true
