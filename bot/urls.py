from django.urls import path
from . import views
from .admin import bot_admin_site

urlpatterns = [
    path('admin/', bot_admin_site.urls),
] 