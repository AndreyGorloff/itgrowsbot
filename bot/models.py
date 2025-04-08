from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class Topic(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название топика', default='Новый топик')
    description = models.TextField(verbose_name='Описание топика', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Топик'
        verbose_name_plural = 'Топики'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('published', _('Published')),
        ('failed', _('Failed')),
    ]

    LANGUAGE_CHOICES = [
        ('ru', 'Russian'),
        ('en', 'English'),
    ]

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name=_('Topic')
    )
    content = models.TextField(_('Content'))
    language = models.CharField(
        _('Language'),
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='ru'
    )
    status = models.CharField(
        _('Status'),
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name=_('Created by')
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    published_at = models.DateTimeField(_('Published at'), null=True, blank=True)
    telegram_message_id = models.IntegerField(
        _('Telegram Message ID'),
        null=True,
        blank=True
    )
    edited = models.BooleanField(_('Edited'), default=False)

    class Meta:
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.topic.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class Settings(models.Model):
    """Global settings for the application."""
    
    telegram_bot_token = models.CharField(
        _('Telegram Bot Token'),
        max_length=255,
        help_text=_('Token obtained from @BotFather')
    )
    telegram_channel_id = models.CharField(
        _('Telegram Channel ID'),
        max_length=255,
        help_text=_('Channel ID where posts will be published')
    )
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Only one settings instance can be active')
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='settings',
        verbose_name=_('Created by')
    )

    class Meta:
        verbose_name = _('Telegram Settings')
        verbose_name_plural = _('Telegram Settings')
        ordering = ['-created_at']

    def clean(self):
        """Ensure only one active settings instance exists."""
        if self.is_active and not self.pk and Settings.objects.filter(is_active=True).exists():
            raise ValidationError(_('There can be only one active settings instance.'))

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate other settings
            Settings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Settings {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_active(cls):
        """Get the active settings instance."""
        return cls.objects.filter(is_active=True).first()

class OpenAISettings(models.Model):
    """OpenAI API settings."""
    
    api_key = models.CharField(
        _('API Key'),
        max_length=255,
        help_text=_('API key from OpenAI platform')
    )
    model = models.CharField(
        _('Model'),
        max_length=50,
        default='gpt-3.5-turbo',
        help_text=_('OpenAI model to use for generation')
    )
    temperature = models.FloatField(
        _('Temperature'),
        default=0.7,
        help_text=_('Controls randomness in the output (0.0-1.0)')
    )
    max_tokens = models.IntegerField(
        _('Max Tokens'),
        default=2000,
        help_text=_('Maximum number of tokens in the response')
    )
    is_active = models.BooleanField(
        _('Is Active'),
        default=True,
        help_text=_('Only one settings instance can be active')
    )
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='openai_settings',
        verbose_name=_('Created by')
    )

    class Meta:
        verbose_name = _('OpenAI Settings')
        verbose_name_plural = _('OpenAI Settings')
        ordering = ['-created_at']

    def clean(self):
        """Ensure only one active settings instance exists."""
        if self.is_active and not self.pk and OpenAISettings.objects.filter(is_active=True).exists():
            raise ValidationError(_('There can be only one active settings instance.'))

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate other settings
            OpenAISettings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"OpenAI Settings {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_active(cls):
        """Get the active settings instance."""
        return cls.objects.filter(is_active=True).first() 