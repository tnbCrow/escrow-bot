from .base import *  # noqa: F401
from decouple import config

# Project Artitecture Constants
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1']

# Business Logic Constants
MIN_TNBC_ALLOWED = 100  # In TNBC
TRADE_CHANNEL_ID = '826324743145390090'
DISPUTE_CHANNEL_ID = '880645101913768046'
AGENT_ROLE_ID = '880647875976114177'
MANAGER_ID = '534628936571813889'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST'),
        'PORT': config('POSTGRES_PORT')
    }
}
