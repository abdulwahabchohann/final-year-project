from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Google OAuth fallback
    path('accounts/oauth2callback/', accounts_views.google_callback),

    # Accounts app
    path('', include('accounts.urls')),
]
