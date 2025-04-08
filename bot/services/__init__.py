# This file makes the services directory a Python package 

from .openai_service import OpenAIService

def generate_article(topic: str) -> dict:
    """
    Generates an article based on the given topic
    
    Args:
        topic (str): The topic to generate an article about
        
    Returns:
        dict: A dictionary containing the generated article with 'title' and 'content' keys
    """
    return OpenAIService.generate_article(topic)

__all__ = ['OpenAIService', 'generate_article'] 