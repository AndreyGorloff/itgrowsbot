import os
import logging
import requests
from typing import Optional
from django.core.cache import cache
from ..models import OpenAISettings

logger = logging.getLogger(__name__)

class OllamaService:
    """
    Сервис для работы с локальной LLM моделью через Ollama
    """
    
    def __init__(self):
        self.api_url = os.getenv('OLLAMA_API_URL', 'http://ollama:11434')
        self.settings = OpenAISettings.get_active()
        self.model = self.settings.local_model_name if self.settings else "llama2"
        
    def _get_cache_key(self, topic: str, language: str) -> str:
        """
        Генерирует безопасный ключ кэша
        """
        import hashlib
        key_string = f"ollama_{topic}_{language}".encode('utf-8')
        return f"ollama_content_{hashlib.md5(key_string).hexdigest()}"
    
    def generate_content(
        self,
        topic: str,
        description: str = "",
        language: str = "ru",
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        Генерирует контент с использованием локальной LLM модели
        
        Args:
            topic: Тема для генерации
            description: Описание темы (опционально)
            language: Язык контента (по умолчанию 'ru')
            model: Название модели Ollama (опционально)
            
        Returns:
            str: Сгенерированный контент или None в случае ошибки
        """
        try:
            # Проверяем кэш
            cache_key = self._get_cache_key(topic, language)
            cached_content = cache.get(cache_key)
            if cached_content:
                logger.info(f"Using cached content for topic: {topic}")
                return cached_content
            
            # Формируем промпт
            prompt = f"""
            Напиши статью на тему "{topic}" на {language} языке.
            {f"Дополнительная информация: {description}" if description else ""}
            
            Требования к статье:
            1. Информативная и полезная
            2. Хорошо структурированная
            3. Легко читаемая
            4. Без технических ошибок
            
            Формат вывода:
            # Заголовок
            
            Введение (2-3 предложения)
            
            Основная часть (3-4 абзаца)
            
            Заключение (2-3 предложения)
            """
            
            # Выбираем модель и параметры
            model_to_use = model or self.model
            settings = self.settings
            
            # Генерируем контент
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": model_to_use,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.temperature if settings else 0.7,
                        "top_p": settings.top_p if settings else 0.9,
                        "max_tokens": settings.max_tokens if settings else 500,
                        "presence_penalty": settings.presence_penalty if settings else 0.6,
                        "frequency_penalty": settings.frequency_penalty if settings else 0.6
                    }
                }
            )
            
            if response.status_code == 200:
                content = response.json()["response"]
                
                # Сохраняем в кэш
                cache.set(cache_key, content, timeout=24 * 60 * 60)  # 24 часа
                
                return content
            else:
                logger.error(f"Error generating content with Ollama: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error in OllamaService: {str(e)}")
            return None
    
    def get_available_models(self) -> list:
        """
        Получает список доступных моделей в Ollama
        """
        try:
            response = requests.get(f"{self.api_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
            return []
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
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
            response = requests.post(
                f"{self.api_url}/api/pull",
                json={"name": model_name}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {str(e)}")
            return False 