# Use Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-traditional \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Make scripts executable
RUN chmod +x /app/docker-entrypoint.sh /app/collectstatic.sh

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/static

# Install Django admin static files
RUN pip install --no-cache-dir django-admin-interface

# Set Django settings for static files collection
ENV DJANGO_SETTINGS_MODULE=itgrowsbot.settings

# Set entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run collectstatic script
CMD ["/app/collectstatic.sh"]

# Run gunicorn
CMD ["gunicorn", "itgrowsbot.wsgi:application", "--bind", "0.0.0.0:8000"] 