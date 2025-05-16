from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Development-specific installed apps
INSTALLED_APPS += [
    'django_browser_reload',
    'debug_toolbar',
]

MIDDLEWARE += [
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Use simpler password validation for dev
AUTH_PASSWORD_VALIDATORS = []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Debug Toolbar settings
INTERNAL_IPS = ['127.0.0.1', 'localhost']

# Explicitly disable security settings for development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Other dev settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'NAME': os.environ.get('POSTGRES_DB', 'postgres'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
