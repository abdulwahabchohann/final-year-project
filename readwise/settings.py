from pathlib import Path
import os

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover - fallback when python-dotenv is missing
    def load_dotenv(path, override=False):
        """Minimal .env loader used if python-dotenv is unavailable."""
        if path.exists():
            for _line in path.read_text(encoding='utf-8').splitlines():
                line = _line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                if override or key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()

# -----------------------
# Base directory setup
# -----------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Lightweight .env loader (no external deps)
ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE, override=False)

# -----------------------
# Basic project settings
# -----------------------
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-insecure-change-me')
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']

# -----------------------
# Installed Apps
# -----------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Allauth (Google Auth)
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Third-party
    'rest_framework',

    # Local app
    'accounts',
]

# -----------------------
# Middleware
# -----------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -----------------------
# URL Configuration
# -----------------------
ROOT_URLCONF = 'readwise.urls'

# -----------------------
# Templates
# -----------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # global templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# -----------------------
# WSGI Application
# -----------------------
WSGI_APPLICATION = 'readwise.wsgi.application'

# -----------------------
# Database
# -----------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -----------------------
# Caches
# -----------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'readwise-locmem-cache',
        'TIMEOUT': None,
    }
}

# -----------------------
# Django REST Framework
# -----------------------
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'user': '120/min',
    },
}

# -----------------------
# Authentication & Allauth Config
# -----------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

ACCOUNT_EMAIL_VERIFICATION = 'none'  # disable email verification for dev
# ACCOUNT_EMAIL_REQUIRED = True  # deprecated, using SIGNUP_FIELDS instead
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']

# -----------------------
# Session & Cookie Configuration
# -----------------------
# For development with external OAuth (Google), allow cookies across redirects.
# In production, ensure SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, and
# SESSION_COOKIE_SAMESITE are configured properly.
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'  # Allow cross-site cookies for OAuth redirects
CSRF_COOKIE_SECURE = False  # Set to True in production with HTTPS
CSRF_COOKIE_SAMESITE = 'Lax'

# -----------------------
# Internationalization
# -----------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# -----------------------
# Static Files
# -----------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'accounts' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# -----------------------
# Optional Google OAuth Info (for clarity)
# -----------------------
SITE_BASE_URL = os.getenv('SITE_BASE_URL', 'http://localhost:8000').rstrip('/')

GOOGLE_OAUTH = {
    'CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID', ''),
    'CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET', ''),
    'REDIRECT_URI': os.getenv('GOOGLE_REDIRECT_URI', f'{SITE_BASE_URL}/oauth2callback/'),
    'SCOPE': os.getenv('GOOGLE_OAUTH_SCOPE', 'openid email profile'),
}

# -----------------------
# External API Keys
# -----------------------
GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATICFILES_DIRS = [
    BASE_DIR / 'accounts' / 'static',
    BASE_DIR / 'static',
]
