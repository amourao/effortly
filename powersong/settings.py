"""
Django settings for powersong project on Heroku. For more info, see:
https://github.com/heroku/heroku-django-template

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os


from powersong.local import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
SITE_ID = 1
# Application definition

INSTALLED_APPS = [
    'powersong.apps.powersongConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # Disable Django's own staticfiles handling in favour of WhiteNoise, for
    # greater consistency between gunicorn and `./manage.py runserver`. See:
    # http://whitenoise.evans.io/en/stable/django.html#using-whitenoise-in-development
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'debug_toolbar',
    'async_include',
    # 'silk',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # 'silk.middleware.SilkyMiddleware',
]

ROOT_URLCONF = 'powersong.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['/home/amourao/powersong/powersong/template','./powersong/template'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'builtins': [
                'powersong.templatetags.power_extra'
            ],
            'debug': DEBUG,
        },
    },
]

WSGI_APPLICATION = 'powersong.wsgi.application'

def show_toolbar(request):
    return DEBUG

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': 'powersong.settings.show_toolbar',
    # Rest of config
}
# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
        'file_power': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug_power.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'powersong': {
            'handlers': ['file_power'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


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
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Change 'default' database configuration with $DATABASE_URL.
#DATABASES['default'] = dj_database_url.config(conn_max_age=500)

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'static'),
]

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/
#ALLOWED_HOSTSSTATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"


STRAVA_CALLBACK_URL = HOME_URL + '/strava_oauth_callback/'
STRAVA_CALLBACK_EDIT_URL = HOME_URL + '/strava_oauth_callback_edit/'

LASTFM_CALLBACK_URL = HOME_URL + '/lastfm_oauth_callback/'

SPOTIFY_CALLBACK_URL = HOME_URL + '/spotify_oauth_callback/'


LASTFM_BASE = 'https://www.last.fm/api/auth/?cb={}&api_key='.format(LASTFM_CALLBACK_URL)
LASTFM_API_AUTHBASE = 'https://ws.audioscrobbler.com/2.0/?method={}&api_key={}&token={}&api_sig={}&format=json'
LASTFM_API_BASE = 'https://ws.audioscrobbler.com/2.0/?method={}&api_key={}&user={}&format=json'
LASTFM_API_RECENT = 'https://ws.audioscrobbler.com/2.0/?method={}&api_key={}&user={}&from={}&to={}&limit=200&extended=1&format=json'
LASTFM_API_ARTIST = 'https://ws.audioscrobbler.com/2.0/?method={}&api_key={}&artist={}&format=json'
LASTFM_API_TRACK = 'https://ws.audioscrobbler.com/2.0/?method={}&api_key={}&artist={}&track={}&format=json'
LASTFM_API_ARTIST_MB = 'https://ws.audioscrobbler.com/2.0/?method={}&api_key={}&mbid={}&format=json'

SPOTIFY_BASE = 'https://accounts.spotify.com/en/authorize?client_id={}&redirect_uri={}&response_type=code&scope=user-read-recently-played,streaming,user-read-birthdate,user-read-email,user-read-private,playlist-modify-private'

from celery.schedules import crontab

CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_IMPORTS = ['powersong.tasks', 'powersong.lastfm_aux']
CELERY_BEAT_SCHEDULE = {
#    'lastfm_sync_artists': {
#       'task': 'powersong.lastfm_aux.lastfm_sync_artists',
#       'schedule': crontab(minute=59, hour=00, day_of_week='mon')
#    },
#    'lastfm_sync_tracks': {
#       'task': 'powersong.lastfm_aux.lastfm_sync_tracks',
#       'schedule': crontab(minute=59, hour=00, day_of_week='thu')
#    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'