from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from allauth.account.forms import AddEmailForm

# Create your views here.

@login_required
def profile(request):
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })

@login_required
def settings(request):
    return render(request, 'accounts/settings.html', {
        'user': request.user
    })

@login_required
def notifications(request):
    return render(request, 'accounts/notifications.html', {
        'user': request.user
    })

@login_required
def security(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('security')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/security.html', {
        'form': form
    })

@login_required
def email_settings(request):
    if request.method == 'POST':
        form = AddEmailForm(request.user, request.POST)
        if form.is_valid():
            form.save(request)
            messages.success(request, 'Your email settings were successfully updated!')
            return redirect('email_settings')
    else:
        form = AddEmailForm(request.user)
    
    return render(request, 'accounts/email_settings.html', {
        'form': form
    })
