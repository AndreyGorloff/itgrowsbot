# This file makes the services directory a Python package 

from .openai_service import OpenAIService

def generate_article(topic):
    """
    Генерирует статью на основе заданного топика
    """
    return OpenAIService.generate_article(topic)

__all__ = ['OpenAIService', 'generate_article'] 