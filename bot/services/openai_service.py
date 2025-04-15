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
import httpx

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Сервис для работы с OpenAI API и локальной LLM моделью
    """
    
    def __init__(self):
        self.ollama_service = OllamaService()
        self.settings = OpenAISettings.get_active()
        self.cache_timeout = 24 * 60 * 60  # 24 hours
        self.ollama_url = os.getenv('OLLAMA_API_URL', 'http://ollama:11434')
        self.default_ollama_model = "tinyllama"  # Default model if none specified
    
    @staticmethod
    def get_client(api_key: Optional[str] = None):
        """Get OpenAI client with settings from database."""
        openai_settings = OpenAISettings.get_active()
        if not openai_settings or not (api_key or openai_settings.api_key):
            raise ValueError("OpenAI API key not configured in admin panel")
        
        return OpenAI(api_key=api_key or openai_settings.api_key)

    @staticmethod
    def _get_cache_key(prompt: str) -> str:
        """Generate a safe cache key using MD5 hash."""
        return hashlib.md5(prompt.encode()).hexdigest()

    def _generate_with_openai(self, prompt: str, api_key: str) -> str:
        """
        Генерирует контент с использованием OpenAI API
        """
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        
        client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        response = client.post(
            "/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that generates content in Russian."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
                "top_p": self.settings.top_p,
                "presence_penalty": self.settings.presence_penalty,
                "frequency_penalty": self.settings.frequency_penalty
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]

    def _generate_with_ollama(self, prompt: str) -> str:
        """
        Генерирует контент с использованием локальной модели Ollama
        """
        client = httpx.Client(base_url=self.ollama_url)
        
        # Get model name from settings
        model_name = self.ollama_service._get_model_name()
        logger.info(f"Using model {model_name} for content generation")
        
        try:
            # First check if model is available
            if not self.ollama_service.is_model_available(model_name):
                logger.warning(f"Model {model_name} not found, attempting to pull...")
                success = self.ollama_service.pull_model(model_name)
                if not success:
                    raise Exception(f"Failed to load model {model_name}")
            
            response = client.post(
                "/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.settings.temperature if self.settings else 0.7,
                        "top_p": self.settings.top_p if self.settings else 0.9,
                        "num_predict": self.settings.max_tokens if self.settings else 500
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = response.text
                if "model not found" in error_msg.lower():
                    raise Exception(f"Model {model_name} not found. Please ensure the model is loaded in Ollama.")
                raise Exception(f"Ollama API error: {error_msg}")
            
            return response.json()["response"]
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Ollama service: {str(e)}")
        except Exception as e:
            raise Exception(f"Error generating content with Ollama: {str(e)}")

    def generate_content(self, prompt: str, api_key: Optional[str] = None) -> Optional[str]:
        """
        Генерирует контент с использованием OpenAI API или локальной модели
        """
        try:
            # Get settings if not provided
            if not self.settings:
                self.settings = OpenAISettings.get_active()
            
            # Try OpenAI first if API key is available and use_local_model is False
            if (api_key or (self.settings and self.settings.api_key)) and not (self.settings and self.settings.use_local_model):
                try:
                    return self._generate_with_openai(prompt, api_key or self.settings.api_key)
                except Exception as e:
                    logger.warning(f"OpenAI generation failed, falling back to local model: {str(e)}")
                    if not self.settings or not self.settings.use_local_model:
                        logger.info("Attempting fallback to local model due to OpenAI failure")
            
            # Use local model if explicitly configured or as fallback
            try:
                logger.info("Using local model for content generation")
                return self._generate_with_ollama(prompt)
            except Exception as e:
                logger.error(f"Local model generation failed: {str(e)}")
                if self.settings and self.settings.use_local_model:
                    # If local model was explicitly configured but failed, don't try OpenAI
                    return None
                
                # If we got here, both OpenAI and local model failed
                raise Exception("Both OpenAI and local model generation failed")
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
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
            if not topic:
                raise ValueError("Topic cannot be empty")
                
            # Определяем, какую модель использовать
            should_use_local = use_local if use_local is not None else (
                self.settings.use_local_model if self.settings else False
            )
            
            prompt = f"""
            Напиши информативную статью на тему "{topic}".
            Статья должна быть структурированной, с заголовками и подзаголовками.
            Используй маркированные списки где это уместно.
            Статья должна быть написана в формате HTML.
            """
            
            if should_use_local:
                content = self.ollama_service.generate_content(prompt=prompt)
                if not content:
                    raise ValueError("Local model failed to generate content")
            else:
                openai_settings = self.get_settings()
                client = self.get_client()
                
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
                
                if not response.choices:
                    raise ValueError("OpenAI API returned no choices")
                    
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("OpenAI API returned empty content")
            
            # Извлекаем заголовок из первого h1 или h2 тега
            title = topic
            if content and "<h1>" in content:
                title = content.split("<h1>")[1].split("</h1>")[0]
            elif content and "<h2>" in content:
                title = content.split("<h2>")[1].split("</h2>")[0]
            
            if not content:
                raise ValueError("Generated content is empty")
            
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