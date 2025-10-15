from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'index.html')

def trending(request):
    return render(request, 'trend.html')

def categories(request):
    return render(request, 'bookcatagory.html')

def recommendations(request):
    return render(request, 'personalize.html')

@login_required(login_url='login')
def personalize(request):
    return render(request, 'personalize.html')

# Login View
def login_view(request):
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next page or home
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'login.html')
    
    return render(request, 'login.html')

# Signup View
def signup_view(request):
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'signup.html')
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return render(request, 'signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'signup.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'signup.html')
        
        # Create user
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'signup.html')
    
    return render(request, 'signup.html')

# Logout View
def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.success(request, f'Goodbye {username}! You have been logged out successfully!')
    return redirect('home')

# ====================== USER PROFILE VIEWS ======================

# User Profile View
@login_required(login_url='login')
def profile(request):
    return render(request, 'profile.html', {'user': request.user})

# Edit Profile View
@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Validation
        if username != user.username and User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken!')
            return render(request, 'edit_profile.html')
        
        if email != user.email and User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'edit_profile.html')
        
        # Update user information
        try:
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            return render(request, 'edit_profile.html')
    
    return render(request, 'edit_profile.html')

# Change Password View
@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        user = request.user
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validation
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect!')
            return render(request, 'change_password.html')
        
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match!')
            return render(request, 'change_password.html')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long!')
            return render(request, 'change_password.html')
        
        if old_password == new_password:
            messages.error(request, 'New password must be different from current password!')
            return render(request, 'change_password.html')
        
        # Change password
        try:
            user.set_password(new_password)
            user.save()
            # Update session to prevent logout
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully!')
            return redirect('profile')
        except Exception as e:
            messages.error(request, f'Error changing password: {str(e)}')
            return render(request, 'change_password.html')
    
    return render(request, 'change_password.html')