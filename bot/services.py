import openai
from django.conf import settings
from .models import OpenAISettings
from .services.openai_service import OpenAIService

def generate_article(topic):
    """
    Генерирует статью на основе заданного топика
    """
    return OpenAIService.generate_article(topic)

def generate_article_old(topic):
    """
    Генерирует статью на основе заданного топика
    """
    openai_settings = OpenAISettings.get_active()
    if not openai_settings:
        raise ValueError("OpenAI settings not configured. Please configure OpenAI settings in admin panel.")
    
    openai.api_key = openai_settings.api_key
    
    prompt = f"""
    Напиши информативную статью на тему "{topic}".
    Статья должна быть структурированной, с заголовками и подзаголовками.
    Используй маркированные списки где это уместно.
    Статья должна быть написана в формате HTML.
    """
    
    response = openai.ChatCompletion.create(
        model=openai_settings.model,
        messages=[
            {"role": "system", "content": "Ты - опытный копирайтер, который пишет информативные статьи."},
            {"role": "user", "content": prompt}
        ],
        temperature=openai_settings.temperature,
        max_tokens=openai_settings.max_tokens
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