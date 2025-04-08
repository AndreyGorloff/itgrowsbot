#!/bin/bash

# Make scripts executable
chmod +x docker-entrypoint.sh

# Build and start containers
docker-compose up --build -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Show logs
docker-compose logs -f 