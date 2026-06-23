import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Load environment variables
load_dotenv(PROJECT_ROOT / '.env')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-p2p-share-secret-key-change-in-production'
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

# Allowed hosts
allowed_hosts = os.getenv('DJANGO_ALLOWED_HOSTS', '')

if allowed_hosts:
    ALLOWED_HOSTS = [
        host.strip()
        for host in allowed_hosts.split(',')
        if host.strip()
    ]
elif DEBUG:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
else:
    ALLOWED_HOSTS = []

# CSRF trusted origins
csrf_trusted_origins = os.getenv(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    ''
)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in csrf_trusted_origins.split(',')
    if origin.strip()
]

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# Email configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@peerdrop.com')
else:
    # Fallback to console for local testing
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'noreply@peerdrop.local'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'channels',
    'corsheaders',
    'rest_framework',

    # Local apps
    'peer',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    # WhiteNoise for static files
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'p2p_share.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', BASE_DIR / 'static' / 'dist'],
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

# WSGI / ASGI
WSGI_APPLICATION = 'p2p_share.wsgi.application'
ASGI_APPLICATION = 'p2p_share.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

STATICFILES_DIRS = []

for static_dir in (
    BASE_DIR / 'static',
    PROJECT_ROOT / 'static'
):
    if static_dir.exists():
        STATICFILES_DIRS.append(static_dir)

STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise static file storage
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Channels configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_PERMISSIONS = 0o644

# P2P app specific settings
P2P_MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
P2P_CHUNK_SIZE = 1024 * 1024           # 1MB chunks
P2P_DEFAULT_PORT = 8000
P2P_PEER_TIMEOUT = 300                 # 5 min timeout

# Production security settings
if not DEBUG:

    SECURE_SSL_REDIRECT = (
        os.getenv(
            'DJANGO_SECURE_SSL_REDIRECT',
            'False'
        ).lower() == 'true'
    )

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = int(
        os.getenv(
            'DJANGO_SECURE_HSTS_SECONDS',
            '0'
        )
    )

    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        SECURE_HSTS_SECONDS > 0
    )

    SECURE_HSTS_PRELOAD = (
        SECURE_HSTS_SECONDS > 0
    )