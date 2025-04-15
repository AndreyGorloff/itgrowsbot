#!/bin/bash

# Ждем, пока Ollama запустится
echo "Waiting for Ollama to start..."
sleep 10

# Загружаем модель llama2
echo "Pulling llama2 model..."
curl -X POST http://localhost:11434/api/pull -d '{"name": "llama2"}'

# Проверяем, что модель загружена
echo "Checking if model is available..."
curl http://localhost:11434/api/tags

echo "Ollama initialization complete!" 