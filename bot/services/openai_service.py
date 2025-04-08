import os
from typing import Optional
from openai import OpenAI
from django.conf import settings
from ..models import Settings

class OpenAIService:
    def __init__(self):
        settings_obj = Settings.get_active()
        if not settings_obj:
            raise ValueError("No active settings found in database")
            
        self.client = OpenAI(api_key=settings_obj.openai_api_key)
        self.model = "gpt-4-turbo-preview"  # or your preferred model

    def generate_content(
        self,
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
            # Construct the prompt based on parameters
            prompt = self._construct_prompt(topic, description, language, style)
            
            # Generate content using OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional content creator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating content: {str(e)}")
            return None

    def _construct_prompt(
        self,
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