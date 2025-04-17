from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import Topic, Post, Settings, OpenAISettings, OllamaModel, SchedulerSettings
from .services.openai_service import OpenAIService
from .services.ollama_service import OllamaService
from django.urls import reverse
from django.utils.html import format_html

# Customize admin site headers
admin.site.site_header = 'ItGrowsBot Administration'
admin.site.site_title = 'ItGrowsBot Admin'
admin.site.index_title = 'Content Management System'

class SettingsAdmin(admin.ModelAdmin):
    list_display = ('telegram_channel_id', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    list_display_links = ('telegram_channel_id',)
    fieldsets = (
        ('Telegram Configuration', {
            'fields': ('telegram_bot_token', 'telegram_channel_id'),
            'description': 'Configure your Telegram bot settings. The bot token and channel ID are required for publishing posts.'
        }),
        ('Status', {
            'fields': ('is_active',),
            'description': 'Enable or disable the bot functionality.'
        }),
    )
    
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

class OpenAISettingsAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'use_local_model', 'local_model_name', 'created_at', 'updated_at')
    list_filter = ('is_active', 'use_local_model', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    list_display_links = ('is_active',)
    fieldsets = (
        ('API Settings', {
            'fields': ('is_active', 'api_key'),
            'description': 'Configure your OpenAI API settings. An API key is required for content generation.'
        }),
        ('Local Model Settings', {
            'fields': ('use_local_model', 'local_model_name'),
            'description': 'If "Use Local Model" is enabled, the system will use the specified Ollama model instead of OpenAI. Make sure the model is installed in Ollama.'
        }),
        ('Generation Parameters', {
            'fields': ('temperature', 'max_tokens', 'top_p', 'presence_penalty', 'frequency_penalty'),
            'description': 'Adjust these parameters to control the content generation process. Higher temperature values make the output more random, while lower values make it more focused.',
            'classes': ('collapse',)
        }),
    )

class OllamaModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_installed', 'is_active', 'last_updated', 'install_button')
    list_filter = ('is_installed', 'is_active')
    readonly_fields = ('last_updated', 'details')
    search_fields = ('name',)
    list_display_links = ('name',)
    fieldsets = (
        ('Model Information', {
            'fields': ('name', 'is_installed', 'is_active'),
            'description': 'Manage your local Ollama models. Ensure models are installed before enabling them.'
        }),
        ('Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
    )

    def install_button(self, obj):
        if obj.is_installed:
            return format_html(
                '<span style="color: green;">✓ Installed</span>'
            )
        return format_html(
            '<a class="button" href="{}">Install</a>',
            reverse('admin:install_ollama_model', args=[obj.pk])
        )
    install_button.short_description = 'Install'
    install_button.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/install/',
                self.admin_site.admin_view(self.install_model),
                name='install_ollama_model',
            ),
        ]
        return custom_urls + urls

    def install_model(self, request, object_id):
        model = self.get_object(request, object_id)
        if model:
            try:
                ollama_service = OllamaService()
                success = ollama_service.pull_model(model.name)
                if success:
                    model.is_installed = True
                    model.save()
                    self.message_user(request, f'Successfully installed model {model.name}')
                else:
                    self.message_user(request, f'Failed to install model {model.name}', level=messages.ERROR)
            except Exception as e:
                self.message_user(request, f'Error installing model: {str(e)}', level=messages.ERROR)
        return HttpResponseRedirect(reverse('admin:bot_ollamamodel_changelist'))

class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'created_at', 'created_by', 'generate_article_link', 'get_latest_post_status')
    list_filter = ('is_active', 'created_at', 'created_by')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'created_by')
    list_display_links = ('name',)
    actions = ['generate_content_for_selected']

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
            # Create a new post with 'draft' status
            from .models import Post
            post = Post.objects.create(
                topic=topic,
                status='draft',
                created_by=request.user
            )
            # Trigger content generation
            from .tasks import generate_article_for_topic
            generate_article_for_topic.delay(topic_id, request.user.id)
            messages.success(request, f'Generation started for topic "{topic.name}". You can track progress in the Posts section.')
        except Exception as e:
            messages.error(request, f'Error starting article generation: {str(e)}')
        return HttpResponseRedirect(reverse('admin:bot_post_changelist'))

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
    get_latest_post_status.short_description = 'Latest Post Status'

    def generate_article_link(self, obj):
        return format_html(
            '<a class="button" href="{}">Generate Article</a>',
            reverse('admin:topic-generate-article', args=[obj.id])
        )
    generate_article_link.short_description = 'Actions'
    generate_article_link.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
            super().save_model(request, obj, form, change)
            # Create a new post in draft status
            from .models import Post
            post = Post.objects.create(
                topic=obj,
                status='draft',
                created_by=request.user
            )
            # Trigger content generation
            from .tasks import generate_article_for_topic
            generate_article_for_topic.delay(obj.id, request.user.id)
        else:
            super().save_model(request, obj, form, change)

    def generate_content_for_selected(self, request, queryset):
        from .tasks import generate_article_for_topic
        for topic in queryset:
            # Create a new post in draft status
            from .models import Post
            post = Post.objects.create(
                topic=topic,
                status='draft',
                created_by=request.user
            )
            # Trigger content generation
            generate_article_for_topic.delay(topic.id, request.user.id)
        self.message_user(request, f"Content generation started for {queryset.count()} topics")

    generate_content_for_selected.short_description = "Generate content for selected topics"

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

class PostAdmin(admin.ModelAdmin):
    list_display = ('topic', 'content_preview', 'status', 'created_at', 'published_at', 'created_by')
    list_filter = ('status', 'created_at', 'published_at', 'created_by')
    search_fields = ('topic__name', 'content')
    readonly_fields = ('created_at', 'published_at', 'created_by', 'telegram_message_id')
    list_display_links = ('topic',)
    actions = ['generate_content', 'publish_selected']

    def content_preview(self, obj):
        """Return a truncated version of the post content for display in the list view."""
        if obj.content:
            return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        return '-'
    content_preview.short_description = 'Content Preview'

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def generate_content(self, request, queryset):
        from .tasks import generate_article_for_topic
        for post in queryset:
            if post.status == 'draft':
                generate_article_for_topic.delay(post.topic.id, request.user.id)
        self.message_user(request, f"Content generation started for {queryset.count()} posts")

    def publish_selected(self, request, queryset):
        from .tasks import publish_post_to_telegram
        for post in queryset:
            if post.status == 'ready':
                publish_post_to_telegram.delay(post.id)
        self.message_user(request, f"Publishing started for {queryset.count()} posts")

    generate_content.short_description = "Generate content for selected posts"
    publish_selected.short_description = "Publish selected posts"

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

class SchedulerSettingsAdmin(admin.ModelAdmin):
    list_display = ('publish_interval', 'publish_time', 'max_posts_per_day', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'publish_interval', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    list_display_links = ('publish_interval',)
    fieldsets = (
        ('Publishing Schedule', {
            'fields': ('publish_interval', 'custom_interval', 'publish_time', 'max_posts_per_day'),
            'description': 'Configure how often and when to publish new content. Set a custom interval if needed.'
        }),
        ('Status', {
            'fields': ('is_active',),
            'description': 'Enable or disable the scheduler.'
        }),
    )
    
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

# Register models with the admin site
admin.site.register(Settings, SettingsAdmin)
admin.site.register(OpenAISettings, OpenAISettingsAdmin)
admin.site.register(OllamaModel, OllamaModelAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(SchedulerSettings, SchedulerSettingsAdmin) 