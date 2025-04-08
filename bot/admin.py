from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from .models import Topic, Post, Settings

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'language', 'created_by', 'created_at')
    list_filter = ('language', 'created_by', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

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
        if not change:  # If creating new object
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
    list_display = ('created_by', 'is_active', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    fieldsets = (
        (_('API Tokens'), {
            'fields': ('telegram_bot_token', 'telegram_channel_id', 'openai_api_key'),
            'classes': ('collapse',),
            'description': _('API tokens for external services. Keep these secure!')
        }),
        (_('Status'), {
            'fields': ('is_active',),
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
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
            return self.readonly_fields + ('telegram_bot_token', 'telegram_channel_id', 'openai_api_key')
        return self.readonly_fields 