import os
from typing import Optional
from openai import OpenAI
from django.conf import settings
from ..models import Settings, OpenAISettings

class OpenAIService:
    @classmethod
    def get_settings(cls):
        """
        Получение активных настроек OpenAI
        """
        openai_settings = OpenAISettings.get_active()
        if not openai_settings:
            raise ValueError("OpenAI settings not configured. Please configure OpenAI settings in admin panel.")
        return openai_settings

    @classmethod
    def get_client(cls):
        """
        Получение клиента OpenAI API
        """
        openai_settings = cls.get_settings()
        return OpenAI(api_key=openai_settings.api_key)
        
    @classmethod
    def generate_content(
        cls,
        topic: str,
        description: str,
        language: str = 'ru',
        style: str = 'expert'
    ) -> Optional[str]:
        """
        Generate content based on topic and description.
        
        Args:
            topic: The topic title
            description: Topic description/prompt
            language: Content language (ru/en)
            style: Content style (expert, casual, humorous, etc.)
            
        Returns:
            Generated content as string or None if generation failed
        """
        try:
            openai_settings = cls.get_settings()
            client = cls.get_client()
            
            # Construct the prompt based on parameters
            prompt = cls._construct_prompt(topic, description, language, style)
            
            # Generate content using OpenAI API
            response = client.chat.completions.create(
                model=openai_settings.model,
                messages=[
                    {"role": "system", "content": "You are a professional content creator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=openai_settings.temperature,
                max_tokens=openai_settings.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            return None

    @classmethod
    def _construct_prompt(
        cls,
        topic: str,
        description: str,
        language: str,
        style: str
    ) -> str:
        """Construct the prompt for content generation."""
        
        style_prompts = {
            'expert': "Write in an expert, professional tone",
            'casual': "Write in a casual, friendly tone",
            'humorous': "Write in a humorous, entertaining tone",
        }
        
        style_prompt = style_prompts.get(style, style_prompts['expert'])
        
        return f"""
        Topic: {topic}
        Description: {description}
        
        Please write a detailed article in {language} language.
        {style_prompt}
        
        The content should be:
        - Well-structured
        - Engaging
        - Informative
        - Suitable for social media
        
        Format the text with appropriate paragraphs and sections.
        """
    
    @classmethod
    def generate_article(cls, topic):
        """
        Генерирует статью на основе заданного топика
        """
        try:
            openai_settings = cls.get_settings()
            client = cls.get_client()
            
            prompt = f"""
            Напиши информативную статью на тему "{topic}".
            Статья должна быть структурированной, с заголовками и подзаголовками.
            Используй маркированные списки где это уместно.
            Статья должна быть написана в формате HTML.
            """
            
            response = client.chat.completions.create(
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
        except Exception as e:
            print(f"Error generating article: {str(e)}")
            raise 