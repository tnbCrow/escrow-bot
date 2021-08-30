import os
from .base import *  # noqa: F401

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))


# Project Artitecture Constants
DEBUG = False
ALLOWED_HOSTS = ['iskush.pythonanywhere.com']

# Business Logic Constants
MIN_TNBC_ALLOWED = 100  # In TNBC
TRADE_CHANNEL_ID = '826324743145390090'
DISPUTE_CHANNEL_ID = '880645101913768046'
AGENT_ROLE_ID = '880647875976114177'
MANAGER_ID = '534628936571813889'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT')
    }
}
