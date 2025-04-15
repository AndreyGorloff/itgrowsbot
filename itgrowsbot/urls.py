from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='itgrowsbot/home.html'), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    path('bot/', include('bot.urls')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = 'ItGrowsBot Admin'
admin.site.site_title = 'ItGrowsBot Admin Portal'
admin.site.index_title = 'Welcome to ItGrowsBot Portal' 