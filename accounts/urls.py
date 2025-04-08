from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('notifications/', views.notifications, name='notifications'),
    path('security/', views.security, name='security'),
    path('email-settings/', views.email_settings, name='email_settings'),
] 