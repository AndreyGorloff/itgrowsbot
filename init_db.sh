#!/bin/bash

# Ждем, пока PostgreSQL запустится
echo "Waiting for PostgreSQL to start..."
sleep 5

# Создаем базу данных
PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -c "CREATE DATABASE itgrowsbot;"

# Применяем миграции
docker-compose exec web python manage.py migrate

# Создаем суперпользователя
docker-compose exec web python manage.py createsuperuser --noinput \
    --username=admin \
    --email=admin@example.com

echo "Database initialization completed!" 