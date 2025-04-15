import os
import logging
import json
import hashlib
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache
from openai import OpenAI, APIError
from ..models import OpenAISettings
from .ollama_service import OllamaService
import requests

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Сервис для работы с OpenAI API и локальной LLM моделью
    """
    
    def __init__(self):
        self.ollama_service = OllamaService()
        self.settings = OpenAISettings.get_active()
        self.cache_timeout = 24 * 60 * 60  # 24 hours
        self.ollama_url = "http://localhost:11434/api/generate"
        self.ollama_model = "tinyllama"
    
    @staticmethod
    def get_client():
        """Get OpenAI client with settings from database."""
        openai_settings = OpenAISettings.get_active()
        if not openai_settings or not openai_settings.api_key:
            raise ValueError("OpenAI API key not configured")
        
        return OpenAI(api_key=openai_settings.api_key)

    @staticmethod
    def _get_cache_key(prompt: str) -> str:
        """Generate a safe cache key using MD5 hash."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _generate_with_openai(self, prompt: str, api_key: Optional[str] = None) -> Optional[str]:
        """Try to generate content using OpenAI API."""
        try:
            client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates content in Russian."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
                presence_penalty=0.6,
                frequency_penalty=0.6,
                top_p=0.9
            )
            
            return response.choices[0].message.content
        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating content with OpenAI: {str(e)}")
            return None

    def _generate_with_ollama(self, prompt: str) -> Optional[str]:
        """Generate content using local Ollama model."""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json().get("response")
        except Exception as e:
            logger.error(f"Error generating content with Ollama: {str(e)}")
            return None

    def generate_content(self, prompt: str, api_key: Optional[str] = None) -> Optional[str]:
        """Generate content using OpenAI API with fallback to Ollama."""
        cache_key = self._get_cache_key(prompt)
        
        # Try to get from cache first
        cached_content = cache.get(cache_key)
        if cached_content:
            logger.info("Using cached content")
            return cached_content

        # Try OpenAI first
        content = self._generate_with_openai(prompt, api_key)
        
        # If OpenAI fails, try Ollama
        if content is None:
            logger.info("Falling back to Ollama model")
            content = self._generate_with_ollama(prompt)

        if content:
            # Cache the result
            cache.set(cache_key, content, self.cache_timeout)
            return content

        return None

    def get_available_models(self) -> list:
        """
        Получает список доступных моделей
        """
        try:
            # Получаем модели OpenAI
            client = self.get_client()
            openai_models = [model.id for model in client.models.list().data]
            
            # Получаем модели Ollama
            ollama_models = self.ollama_service.get_available_models()
            
            return {
                "openai": openai_models,
                "ollama": ollama_models
            }
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return {"openai": [], "ollama": []}

    @classmethod
    def get_settings(cls):
        """
        Получение активных настроек OpenAI
        """
        openai_settings = OpenAISettings.get_active()
        if not openai_settings:
            raise ValueError("OpenAI settings not configured. Please configure OpenAI settings in admin panel.")
        return openai_settings

    def generate_article(self, topic, use_local: Optional[bool] = None):
        """
        Генерирует статью на основе заданного топика
        """
        try:
            # Определяем, какую модель использовать
            should_use_local = use_local if use_local is not None else (
                self.settings.use_local_model if self.settings else False
            )
            
            if should_use_local:
                content = self.ollama_service.generate_content(topic=topic)
            else:
                openai_settings = self.get_settings()
                client = self.get_client()
                
                prompt = f"""
                Напиши информативную статью на тему "{topic}".
                Статья должна быть структурированной, с заголовками и подзаголовками.
                Используй маркированные списки где это уместно.
                Статья должна быть написана в формате HTML.
                """
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {"role": "system", "content": "Ты - опытный копирайтер, который пишет информативные статьи."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.settings.max_tokens if self.settings else 500,
                    temperature=self.settings.temperature if self.settings else 0.7,
                    presence_penalty=self.settings.presence_penalty if self.settings else 0.6,
                    frequency_penalty=self.settings.frequency_penalty if self.settings else 0.6,
                    top_p=self.settings.top_p if self.settings else 0.9
                )
                
                content = response.choices[0].message.content
            
            # Извлекаем заголовок из первого h1 или h2 тега
            title = topic
            if "<h1>" in content:
                title = content.split("<h1>")[1].split("</h1>")[0]
            elif "<h2>" in content:
                title = content.split("<h2>")[1].split("</h2>")[0]
            
            return {
                'title': title,
                'content': content
            }
        except Exception as e:
            logger.error(f"Error generating article: {str(e)}")
            # Если произошла ошибка с OpenAI, пробуем использовать локальную модель
            if not use_local:
                logger.info("Trying to use local model as fallback...")
                return self.generate_article(topic, use_local=True)
            raise 