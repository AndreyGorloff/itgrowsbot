import os
import logging
import requests
from typing import Optional, Tuple
from django.core.cache import cache
from ..models import OpenAISettings, Settings
import hashlib
import json

logger = logging.getLogger(__name__)

class OllamaService:
    """
    Сервис для работы с локальной LLM моделью через Ollama
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Инициализация сервиса Ollama
        
        Args:
            settings: Настройки для генерации
        """
        self.api_url = os.getenv('OLLAMA_API_URL', 'http://ollama:11434')
        self.settings = settings
        self.default_ollama_model = "tinyllama"  # Default model if none specified
        
    def _get_model_name(self) -> str:
        """
        Получает имя модели из настроек или использует значение по умолчанию
        
        Returns:
            str: Имя модели для использования
        """
        if not self.settings:
            self.settings = OpenAISettings.get_active()
        
        if not self.settings:
            logger.warning("No OpenAISettings found, using default model")
            return self.default_ollama_model
            
        if not self.settings.use_local_model:
            logger.warning("Local model usage is disabled in settings")
            return self.default_ollama_model
            
        model_name = self.settings.local_model_name
        if not model_name:
            logger.warning("No local model name configured in settings, using default model")
            return self.default_ollama_model
            
        return model_name

    def _get_cache_key(self, topic: str, language: str) -> str:
        """
        Генерирует безопасный ключ кэша
        """
        key_string = f"ollama_{topic}_{language}".encode('utf-8')
        return f"ollama_content_{hashlib.md5(key_string).hexdigest()}"
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Проверяет доступность модели в Ollama
        
        Args:
            model_name: Название модели для проверки
            
        Returns:
            bool: True если модель доступна
        """
        try:
            available_models = self.get_available_models()
            return model_name in available_models
        except Exception as e:
            logger.error(f"Error checking model availability: {str(e)}")
            return False
            
    def ensure_model_loaded(self, model_name: str) -> Tuple[bool, str]:
        """
        Проверяет наличие модели и пытается загрузить её при необходимости
        
        Returns:
            Tuple[bool, str]: (успех, сообщение об ошибке)
        """
        if not self.is_model_available(model_name):
            logger.info(f"Model {model_name} not found, attempting to pull...")
            success = self.pull_model(model_name)
            if not success:
                return False, f"Failed to load model {model_name}"
            # Проверяем снова после попытки загрузки
            if not self.is_model_available(model_name):
                return False, f"Model {model_name} still not available after pull attempt"
        return True, ""
    
    def generate_content(self, prompt: str) -> str:
        """
        Генерирует контент с помощью модели
        
        Args:
            prompt: Промпт для генерации
            
        Returns:
            str: Сгенерированный контент
            
        Raises:
            ValueError: Если промпт пустой или модель не доступна
            Exception: Если произошла ошибка при генерации
        """
        if not prompt:
            raise ValueError("Prompt cannot be empty")
            
        if not self.ensure_server_ready():
            raise Exception("Ollama server is not ready")
            
        # Проверяем кэш
        cache_key = f"ollama_content_{hashlib.md5(prompt.encode()).hexdigest()}"
        cached_content = cache.get(cache_key)
        if cached_content:
            logger.info("Using cached content")
            return cached_content
            
        try:
            # Get model name from settings
            model_name = self._get_model_name()
            logger.info(f"Using model {model_name} for content generation")
            
            # First check if model is available
            if not self.is_model_available(model_name):
                logger.warning(f"Model {model_name} not found, attempting to pull...")
                success = self.pull_model(model_name)
                if not success:
                    raise Exception(f"Failed to load model {model_name}")
            
            response = requests.post(
                f"{self.api_url}/api/generate",
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
            
            result = response.json()
            if 'response' not in result:
                raise Exception("Invalid response format from Ollama API")
                
            content = result['response']
            if not content:
                raise Exception("Empty response from Ollama API")
            
            # Кэшируем результат на 24 часа
            cache.set(cache_key, content, timeout=86400)
            logger.info("Successfully generated content")
            return content
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Ollama service: {str(e)}")
        except Exception as e:
            raise Exception(f"Error generating content: {str(e)}")
    
    def get_available_models(self) -> list:
        """
        Получает список доступных моделей из API Ollama
        
        Returns:
            list: Список моделей с детальной информацией
        """
        try:
            response = requests.get(f"{self.api_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if 'models' not in result:
                logger.error("Unexpected API response format when getting models")
                return []
                
            return result['models']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting available models: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error while getting models: {str(e)}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """
        Загружает модель в Ollama
        
        Args:
            model_name: Название модели для загрузки
            
        Returns:
            bool: True если модель успешно загружена
        """
        try:
            logger.info(f"Pulling model {model_name}...")
            response = requests.post(
                f"{self.api_url}/api/pull",
                json={"name": model_name},
                timeout=600  # Даём 10 минут на загрузку модели
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model {model_name}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error pulling model {model_name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while pulling model {model_name}: {str(e)}")
            return False

    def is_server_healthy(self) -> bool:
        """
        Проверяет доступность сервера Ollama
        
        Returns:
            bool: True если сервер отвечает
        """
        try:
            response = requests.get(f"{self.api_url}/api/version", timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama server health check failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during server health check: {str(e)}")
            return False

    def ensure_server_ready(self) -> bool:
        """
        Проверяет готовность сервера к работе
        
        Returns:
            bool: True если сервер готов к работе
        """
        if not self.is_server_healthy():
            logger.error("Ollama server is not responding")
            return False
            
        return True 