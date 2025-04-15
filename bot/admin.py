from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import Topic, Post, Settings, OpenAISettings, OllamaModel
from .services.openai_service import OpenAIService
from django.urls import reverse
from django.utils.html import format_html

class BotAdminSite(admin.AdminSite):
    site_header = 'Bot Administration'
    site_title = 'Bot Admin'
    index_title = 'Bot Management'

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        
        # Reorganize the app list
        bot_app = next((app for app in app_list if app['app_label'] == 'bot'), None)
        if bot_app:
            # Create new structure
            new_models = []
            
            # Bot Settings Section
            settings_models = [
                model for model in bot_app['models']
                if model['object_name'] in ['Settings', 'OpenAISettings', 'OllamaModel']
            ]
            if settings_models:
                new_models.append({
                    'name': 'Bot Settings',
                    'app_label': 'bot',
                    'models': settings_models
                })
            
            # Content Management Section
            content_models = [
                model for model in bot_app['models']
                if model['object_name'] in ['Topic', 'Post']
            ]
            if content_models:
                new_models.append({
                    'name': 'Content Management',
                    'app_label': 'bot',
                    'models': content_models
                })
            
            # Replace the original models with our new structure
            bot_app['models'] = new_models
        
        return app_list

# Create an instance of our custom admin site
bot_admin_site = BotAdminSite(name='bot_admin')

# Register models with our custom admin site
@admin.register(Settings, site=bot_admin_site)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('telegram_channel_id', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    list_display_links = ('telegram_channel_id',)
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('telegram_bot_token', 'telegram_channel_id')
        return self.readonly_fields

@admin.register(OpenAISettings, site=bot_admin_site)
class OpenAISettingsAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'use_local_model', 'local_model_name', 'created_at', 'updated_at')
    list_filter = ('is_active', 'use_local_model', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    list_display_links = ('is_active',)
    fieldsets = (
        ('API Settings', {
            'fields': ('is_active', 'api_key')
        }),
        ('Local Model Settings', {
            'fields': ('use_local_model', 'local_model_name'),
            'description': 'If "Use Local Model" is enabled, the system will use the specified Ollama model instead of OpenAI. Make sure the model is installed in Ollama.'
        }),
        ('Generation Parameters', {
            'fields': ('temperature', 'max_tokens', 'top_p', 'presence_penalty', 'frequency_penalty'),
            'classes': ('collapse',)
        }),
    )

@admin.register(OllamaModel, site=bot_admin_site)
class OllamaModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_installed', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_installed', 'is_active', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_display_links = ('name',)

@admin.register(Topic, site=bot_admin_site)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at', 'generate_article_link', 'get_latest_post_status')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    list_display_links = ('name',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:topic_id>/generate-article/',
                self.admin_site.admin_view(self.generate_article),
                name='topic-generate-article',
            ),
        ]
        return custom_urls + urls

    def generate_article(self, request, topic_id):
        topic = Topic.objects.get(id=topic_id)
        try:
            from bot.tasks import generate_article_for_topic
            generate_article_for_topic.delay(topic_id, request.user.id)
            messages.success(request, f'Генерация статьи для топика "{topic.name}" запущена')
        except Exception as e:
            messages.error(request, f'Ошибка при запуске генерации статьи: {str(e)}')
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_latest_post_status(self, obj):
        latest_post = obj.posts.order_by('-created_at').first()
        if latest_post:
            status_display = dict(Post.STATUS_CHOICES).get(latest_post.status, latest_post.status)
            if latest_post.status == 'generating':
                return format_html('<span style="color: orange;">{}</span>', status_display)
            elif latest_post.status == 'failed':
                return format_html('<span style="color: red;">{}</span>', status_display)
            return status_display
        return '-'
    get_latest_post_status.short_description = 'Статус последней статьи'

    def generate_article_link(self, obj):
        return format_html(
            '<a class="button" href="{}">Сгенерировать статью</a>',
            reverse('admin:topic-generate-article', args=[obj.id])
        )
    generate_article_link.short_description = 'Действия'
    generate_article_link.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Post, site=bot_admin_site)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'topic',
        'status',
        'get_progress_display',
        'language',
        'created_by',
        'created_at',
        'published_at',
        'edited'
    )
    list_filter = (
        'status',
        'language',
        'created_by',
        'edited',
        'created_at',
        'published_at'
    )
    search_fields = ('content', 'topic__name')
    readonly_fields = ('created_at', 'published_at', 'telegram_message_id', 'progress')
    ordering = ('-created_at',)
    list_display_links = ('topic',)
    
    actions = ['mark_as_published', 'mark_as_draft', 'regenerate_content']

    def get_progress_display(self, obj):
        if obj.status == 'generating':
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
                '<div style="width: {}%; background-color: #79aec8; height: 20px; border-radius: 3px; text-align: center; color: white;">'
                '{}%</div></div>',
                obj.progress,
                obj.progress
            )
        return '-'
    get_progress_display.short_description = 'Progress'
    get_progress_display.admin_order_field = 'progress'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def mark_as_published(self, request, queryset):
        updated = queryset.update(
            status='published',
            published_at=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d post(s) were successfully marked as published.') % {
                'count': updated
            }
        )
    mark_as_published.short_description = _('Mark selected posts as published')

    def mark_as_draft(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(
            request,
            _('%(count)d post(s) were successfully marked as draft.') % {
                'count': updated
            }
        )
    mark_as_draft.short_description = _('Mark selected posts as draft')

    def regenerate_content(self, request, queryset):
        self.message_user(
            request,
            _('Content regeneration will be implemented with OpenAI service.')
        )
    regenerate_content.short_description = _('Regenerate content for selected posts') 