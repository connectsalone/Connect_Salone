from pathlib import Path
import os
from datetime import timedelta
from decouple import config
from cryptography.fernet import Fernet
import base64

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)


BASE_DIR = Path(__file__).resolve().parent.parent

# Security
#SECRET_KEY = env('SECRET_KEY')  # Move to .env
#DEBUG = env.bool('DEBUG', default=True)
#ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])


# 32-byte base64 key (store this securely, e.g., in environment variable)

fernet_key = config("FERNET_SECRET_KEY")
cipher_suite = Fernet(fernet_key)


FERNET_KEY = config('FERNET_KEY')

SITE_ID = config("SITE_ID", default=1, cast=int) # or the ID of the site you want to be the default


# Installed Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.humanize',
    'django.contrib.sites',

    # Custom apps
    'accounts',
    'events',
    'payment',
    'dashboard',
    'googleauthentication',
    'whitenoise.runserver_nostatic',

    # AllAuth for authentication
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'rest_framework_simplejwt.token_blacklist',
  

   
]

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'corsheaders.middleware.CorsMiddleware',  # CORS
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Make sure this is correct


    "whitenoise.middleware.WhiteNoiseMiddleware",

    'allauth.account.middleware.AccountMiddleware',  # Add this line
]

ROOT_URLCONF = 'connect_salone.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'connect_salone.wsgi.application'


DATABASES = {
    
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # Change this based on your database type
        'NAME': config('DATABASE_NAME'),
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST'),
        'PORT': config('DATABASE_PORT'),
    }
}


#ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="yourdomain.com").split(",")
ALLOWED_HOSTS =['salone-connect.com', 'https://salone-connect.com', 'connect-salone.onrender.com', 'localhost', '127.0.0.1']

CSRF_TRUSTED_ORIGINS = ['https://salone-connect.com', 'https://connect-salone.onrender.com']

# CORS settings
CORS_ALLOWED_ORIGINS = ['https://salone-connect.com', 'https://connect-salone.onrender.com']



# Authentication and AllAuth
AUTHENTICATION_BACKENDS = ["accounts.authentication.CustomAuthBackend", "django.contrib.auth.backends.ModelBackend", 'allauth.account.auth_backends.AuthenticationBackend',]

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
SOCIALACCOUNT_LOGIN_ON_GET = True

AUTH_USER_MODEL = 'accounts.User'


# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
}

# Static and Media Files
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

if DEBUG:
    STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
else:
    if not DEBUG:
        STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
       

   

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# White noise static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Caching (Choose One: Memcached or File-Based)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'cache_directory'),
    }
}





# Email settings
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")  # REMOVE .encode("utf-8").decode("utf-8")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")  # REMOVE .encode("utf-8").decode("utf-8")


if not config("DEBUG", default=False, cast=bool):  # Ensure DEBUG is False in production
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
    SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
    CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '5/minute',
        'user': '10/minute',
    },

     'DEFAULT_AUTHENTICATION_CLASSES': (
         
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

AUTH_USER_MODEL = 'accounts.User'  # Custom user model



DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'




WEBSITE_URL = config("WEBSITE_URL", default="https://salone-connect.com")

#import os, psutil
#process = psutil.Process(os.getpid())
#print(f"Memory usage at startup: {process.memory_info().rss / 1024 ** 2:.2f} MB")

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'django': {
        'handlers': ['console'],
        'level': 'INFO',  # Change to DEBUG for development
        'propagate': True,
    },
}