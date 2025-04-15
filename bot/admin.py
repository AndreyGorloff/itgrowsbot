from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import Topic, Post, Settings, OpenAISettings
from .services import generate_article
from django.urls import reverse
from django.utils.html import format_html

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at', 'generate_article_link')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
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
            article = generate_article(topic.name)
            Post.objects.create(
                title=article['title'],
                content=article['content'],
                topic=topic,
                created_by=request.user
            )
            messages.success(request, f'Статья успешно сгенерирована для топика "{topic.name}"')
        except Exception as e:
            messages.error(request, f'Ошибка при генерации статьи: {str(e)}')
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_list_display_links(self, request, list_display):
        return None

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        return list_display + ('generate_article_link',)

    def generate_article_link(self, obj):
        return format_html(
            '<a class="button" href="{}">Сгенерировать статью</a>',
            reverse('admin:topic-generate-article', args=[obj.id])
        )
    generate_article_link.short_description = 'Действия'
    generate_article_link.allow_tags = True

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'topic',
        'status',
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
    search_fields = ('content', 'topic__title')
    readonly_fields = ('created_at', 'published_at', 'telegram_message_id')
    ordering = ('-created_at',)
    
    actions = ['mark_as_published', 'mark_as_draft', 'regenerate_content']

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by during the first save.
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
        # This will be implemented with OpenAI service
        self.message_user(
            request,
            _('Content regeneration will be implemented with OpenAI service.')
        )
    regenerate_content.short_description = _('Regenerate content for selected posts')

@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('telegram_channel_id', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by during the first save.
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete settings
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Only superusers can change settings
        return request.user.is_superuser

    def has_add_permission(self, request):
        # Only superusers can add settings
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        # Make API tokens readonly after creation for additional security
        if obj:  # editing an existing object
            return self.readonly_fields + ('telegram_bot_token', 'telegram_channel_id')
        return self.readonly_fields

@admin.register(OpenAISettings)
class OpenAISettingsAdmin(admin.ModelAdmin):
    list_display = ('is_active', 'use_local_model', 'local_model_name', 'created_at', 'updated_at')
    list_filter = ('is_active', 'use_local_model', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('API Settings', {
            'fields': ('is_active', 'api_key')
        }),
        ('Local Model Settings', {
            'fields': ('use_local_model', 'local_model_name')
        }),
        ('Generation Parameters', {
            'fields': ('temperature', 'max_tokens', 'top_p', 'presence_penalty', 'frequency_penalty'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by during the first save.
            obj.created_by = request.user
        super().save_model(request, obj, form, change) 