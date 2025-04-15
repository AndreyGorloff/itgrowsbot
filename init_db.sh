#!/bin/bash

# Ждем, пока PostgreSQL запустится
echo "Waiting for PostgreSQL to start..."
sleep 5

# Создаем базу данных
PGPASSWORD=postgres psql -h db -p 5432 -U postgres -c "CREATE DATABASE itgrowsbot;"

# Применяем миграции
python manage.py migrate

# Создаем суперпользователя
python manage.py createsuperuser --noinput \
    --username=admin \
    --email=admin@example.com

echo "Database initialization completed!" 