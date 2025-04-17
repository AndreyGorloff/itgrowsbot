from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Customize admin site headers
admin.site.site_header = 'ItGrowsBot Administration'
admin.site.site_title = 'ItGrowsBot Admin'
admin.site.index_title = 'Content Management System'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    path('', TemplateView.as_view(template_name='itgrowsbot/home.html'), name='home'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 