from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured

try:
    import dj_database_url  # type: ignore
except ImportError:
    dj_database_url = None

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


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw_value = os.getenv(name, '')
    if not raw_value:
        return list(default or [])
    return [item.strip() for item in raw_value.split(',') if item.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE, override=False)

IS_RENDER = bool(os.getenv('RENDER'))
IS_PRODUCTION = _env_bool('IS_PRODUCTION', default=IS_RENDER)
DEBUG = _env_bool('DEBUG', default=not IS_PRODUCTION)

SECRET_KEY = (os.getenv('SECRET_KEY') or '').strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-insecure-change-me'
    else:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG=False.')
if not DEBUG and SECRET_KEY == 'dev-insecure-change-me':
    raise ImproperlyConfigured('Set a secure SECRET_KEY before running in production.')

ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', 'testserver'])
RENDER_EXTERNAL_HOSTNAME = (os.getenv('RENDER_EXTERNAL_HOSTNAME') or '').strip()
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', default=[])
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f'https://{RENDER_EXTERNAL_HOSTNAME}'
    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)

try:
    import whitenoise  # type: ignore # pragma: no cover - used to detect availability
except ImportError:
    WHITENOISE_AVAILABLE = False
else:
    WHITENOISE_AVAILABLE = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'rest_framework',
    'accounts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
]
if WHITENOISE_AVAILABLE:
    MIDDLEWARE.append('whitenoise.middleware.WhiteNoiseMiddleware')
MIDDLEWARE += [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'readwise.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'readwise.wsgi.application'

DATABASE_URL = (os.getenv('DATABASE_URL') or '').strip()
if DATABASE_URL:
    if dj_database_url is None:
        raise ImproperlyConfigured('DATABASE_URL is set but dj-database-url is not installed.')
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'readwise-locmem-cache',
        'TIMEOUT': None,
    }
}

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

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']

SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
    SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', default=False)

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
GLOBAL_STATIC_DIR = BASE_DIR / 'static'
STATICFILES_DIRS = [GLOBAL_STATIC_DIR] if GLOBAL_STATIC_DIR.exists() else []

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if (not DEBUG and WHITENOISE_AVAILABLE)
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        )
    },
}

_site_base_url = (os.getenv('SITE_BASE_URL') or '').strip().rstrip('/')
if _site_base_url:
    SITE_BASE_URL = _site_base_url
elif RENDER_EXTERNAL_HOSTNAME:
    SITE_BASE_URL = f'https://{RENDER_EXTERNAL_HOSTNAME}'
else:
    SITE_BASE_URL = 'http://localhost:8000'

GOOGLE_OAUTH = {
    'CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID', ''),
    'CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET', ''),
    'REDIRECT_URI': os.getenv('GOOGLE_REDIRECT_URI', f'{SITE_BASE_URL}/accounts/oauth2callback/'),
    'SCOPE': os.getenv('GOOGLE_OAUTH_SCOPE', 'openid email profile'),
}

GOOGLE_BOOKS_API_KEY = os.getenv('GOOGLE_BOOKS_API_KEY', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
