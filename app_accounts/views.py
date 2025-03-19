from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from app_accounts.forms import SignUpForm

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('app_admin_management:index_admin')
    else:
        form = SignUpForm()
    return render(request, 'app_accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('app_admin_management:index_admin')
    else:
        form = AuthenticationForm()
    return render(request, 'app_accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('app_admin_management:index_admin')
