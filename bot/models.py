from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class Topic(models.Model):
    name = models.CharField(max_length=200, help_text='Enter a topic name')
    description = models.TextField(help_text='Enter a brief description of the topic')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text='Enable or disable this topic')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='topics')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'

    def __str__(self):
        return self.name

class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generating', 'Generating'),
        ('ready', 'Ready to Publish'),
        ('published', 'Published'),
        ('failed', 'Failed')
    ]
    
    LANGUAGE_CHOICES = [
        ('ru', 'Russian'),
        ('en', 'English')
    ]
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='posts', help_text='Select the topic for this post')
    content = models.TextField(help_text='The generated content of the post')
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='ru', help_text='Select the language for this post')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', help_text='Current status of the post')
    priority = models.IntegerField(default=0, help_text='Higher number means higher priority for publishing')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True, help_text='When the post was published')
    telegram_message_id = models.IntegerField(null=True, blank=True, help_text='ID of the message in Telegram')
    edited = models.BooleanField(default=False, help_text='Whether the post has been edited')
    progress = models.IntegerField(default=0, help_text='Generation progress in percentage')

    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'

    def __str__(self):
        return f"{self.topic.name} - {self.get_status_display()}"

    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

class Settings(models.Model):
    telegram_bot_token = models.CharField(max_length=255, help_text='Your Telegram bot token')
    telegram_channel_id = models.CharField(max_length=255, help_text='ID of your Telegram channel')
    is_active = models.BooleanField(default=True, help_text='Enable or disable the bot')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='settings')

    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'

    def __str__(self):
        return f"Settings - {self.telegram_channel_id}"

    @classmethod
    def get_active(cls):
        """Get the first active settings."""
        return cls.objects.filter(is_active=True).first()

    @classmethod
    def get_active_settings(cls):
        return cls.objects.filter(is_active=True).first()

class OpenAISettings(models.Model):
    api_key = models.CharField(max_length=255, help_text='Your OpenAI API key')
    model = models.CharField(max_length=50, default='gpt-4', help_text='The OpenAI model to use')
    temperature = models.FloatField(default=0.7, help_text='Controls randomness in generation (0.0 to 1.0)')
    max_tokens = models.IntegerField(default=2000, help_text='Maximum number of tokens to generate')
    top_p = models.FloatField(default=1.0, help_text='Controls diversity via nucleus sampling')
    frequency_penalty = models.FloatField(default=0.0, help_text='Penalizes repeated token sequences')
    presence_penalty = models.FloatField(default=0.0, help_text='Penalizes repeated tokens')
    use_local_model = models.BooleanField(default=False, help_text='Use local Ollama model instead of OpenAI')
    local_model_name = models.CharField(max_length=255, blank=True, help_text='Name of the local Ollama model to use')
    is_active = models.BooleanField(default=True, help_text='Enable or disable OpenAI settings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='openai_settings')

    def __str__(self):
        return f"OpenAI Settings ({'Active' if self.is_active else 'Inactive'})"

    @classmethod
    def get_active(cls):
        """Get the first active OpenAI settings."""
        return cls.objects.filter(is_active=True).first()

    class Meta:
        verbose_name = 'OpenAI Settings'
        verbose_name_plural = 'OpenAI Settings'

class OllamaModel(models.Model):
    name = models.CharField(max_length=255, help_text='Name of the Ollama model')
    is_installed = models.BooleanField(default=False, help_text='Whether the model is installed in Ollama')
    is_active = models.BooleanField(default=True, help_text='Enable or disable this model')
    last_updated = models.DateTimeField(auto_now=True)
    details = models.JSONField(null=True, blank=True, help_text='Additional model details from Ollama')

    class Meta:
        verbose_name = 'Ollama Model'
        verbose_name_plural = 'Ollama Models'

    def __str__(self):
        return self.name

    def get_model_status(self):
        if not self.is_installed:
            return "Not Installed"
        if not self.is_active:
            return "Inactive"
        return "Active"

    def save(self, *args, **kwargs):
        """
        При сохранении новой активной модели деактивируем остальные
        """
        if self.is_active:
            OllamaModel.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class SchedulerSettings(models.Model):
    PUBLISH_INTERVAL_CHOICES = [
        ('hourly', 'Every Hour'),
        ('daily', 'Once Daily'),
        ('weekly', 'Once Weekly'),
        ('custom', 'Custom Interval')
    ]
    
    publish_interval = models.CharField(
        max_length=10,
        choices=PUBLISH_INTERVAL_CHOICES,
        default='daily',
        help_text='How often to publish new content'
    )
    custom_interval = models.IntegerField(
        null=True,
        blank=True,
        help_text='Custom interval in hours (only used if publish_interval is "custom")'
    )
    publish_time = models.TimeField(
        default='09:00',
        help_text='Time of day to publish content (in UTC)'
    )
    max_posts_per_day = models.IntegerField(
        default=1,
        help_text='Maximum number of posts to publish per day'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Enable or disable the scheduler'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='scheduler_settings')

    class Meta:
        verbose_name = 'Scheduler Settings'
        verbose_name_plural = 'Scheduler Settings'

    def __str__(self):
        return f"Scheduler Settings - {self.get_publish_interval_display()}"

    def clean(self):
        if self.publish_interval == 'custom' and not self.custom_interval:
            raise ValidationError('Custom interval is required when publish interval is set to "custom"')
        if self.custom_interval and self.custom_interval < 1:
            raise ValidationError('Custom interval must be at least 1 hour')

    @classmethod
    def get_active_settings(cls):
        return cls.objects.filter(is_active=True).first() 