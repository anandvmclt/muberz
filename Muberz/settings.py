"""
Django settings for Muberz project.

Generated by 'django-admin startproject' using Django 1.11.7.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import json
import os

from django.core.exceptions import ImproperlyConfigured
import rollbar

# Parsing json file to get data
with open('env.json') as f:
    config_data = json.loads(f.read())


def get_config(setting):
    try:
        val = config_data[setting]
        return val
    except KeyError:
        error_msg = "ImproperlyConfigured: Set {0} in env.json configuration file".format(setting)
        raise ImproperlyConfigured(error_msg)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

LIVE_ENV = False

ALLOWED_HOSTS = ['*']
# Application definition
FROM_EMAIL = "info@muberz.com"

# Email configuration
EMAIL_USE_TLS = True
EMAIL_HOST = get_config('EMAIL_HOST')
EMAIL_PORT = 2525  # Set port 2525, google compute engine doesn't support 587
EMAIL_HOST_USER = get_config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = get_config('EMAIL_HOST_PASSWORD')

BUCKET_URL = get_config('S3_BUCKET_DOMAIN')

GOOGLE_API_KEY = get_config('GOOGLE_API_KEY')
USER_PROFILE_MODEL_PATH = 'api_base.models.BaseProfile'
# CELERY_BROKER_URL = 'amqp://guest:**@127.0.0.1:5672'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'api_base',
    'django_api_base',
    'dashboard',
    'push_notifications',
    'djcelery'
]

PUSH_NOTIFICATIONS_SETTINGS = {
    "FCM_API_KEY": get_config('FCM_API_KEY'),
    "FCM_ERROR_TIMEOUT": 1000.0,
    "APNS_CERTIFICATE": "push-certificates/MuberzPushCert.pem",
    # "APNS_CERTIFICATE": "push-certificates/Muberz_iOS_Production_App.pem",
    "APNS_TOPIC": "com.goodbits.muberzios",
    "APNS_USE_SANDBOX": False
}

# Set the default language for your site.
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dashboard.trans_to.BenchmarkMiddleware',
    'django_api_base.middleware.api_exception.APIExceptionHandler',
    # APIExceptionHandler middleware should be added here
    # 'api_base.middleware.logging_middleware.LogAllServerCalls',
    # 'django_api_base.middleware.logging_middleware.LogAllServerCalls',  # For logging all server request calls info
    'django_api_base.middleware.logging_middleware.LogAllExceptionErrors',  # For logging all exceptions occured,
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
]

ROLLBAR = {
    'access_token': 'c6c6df1d667442d4aecd68134b0f2ba5',
    'environment': 'development' if DEBUG else 'production',
    'root': BASE_DIR,
}

rollbar.init(**ROLLBAR)

ROOT_URLCONF = 'Muberz.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join('templates')],
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

WSGI_APPLICATION = 'Muberz.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': get_config('DATABASE_ENGINE'),
#         'NAME': get_config('DATABASE_NAME'),
#         'USER': get_config('DATABASE_USER'),
#         'PASSWORD': get_config('DATABASE_PASSWORD'),
#         'HOST': get_config('DATABASE_HOST'),
#         'PORT': get_config('DATABASE_PORT'),
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

ACCESS_TOKEN_EXPIRE_DAYS = 30

LOGIN_URL = '/dashboard/login/'

# Logging settings
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'access': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'access.log',
            'formatter': 'verbose'
        },
        'error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
            'formatter': 'verbose'
        },
        'debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'info': {
            'handlers': ['access'],
            'level': 'INFO',
        },
        'error': {
            'handlers': ['error'],
            'level': 'ERROR',
        },
        'debug': {
            'handlers': ['debug'],
            'level': 'DEBUG',
        },
    }
}

CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
